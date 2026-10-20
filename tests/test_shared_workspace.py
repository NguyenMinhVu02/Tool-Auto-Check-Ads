import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from apk_audit.facts import build_facts
from apk_audit.inventory import build_inventory
from apk_audit.tools import WorkspaceTools
from apk_audit.utils import source_files


class SharedWorkspaceTests(unittest.TestCase):
    def test_prevalidated_manifest_avoids_repeated_tree_walks_without_losing_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'sources/demo').mkdir(parents=True); (root/'resources/assets').mkdir(parents=True)
            (root/'resources/AndroidManifest.xml').write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="demo.app"><application android:name="demo.App"/></manifest>')
            (root/'sources/demo/App.java').write_text('class App { void init() { load("inter_splash"); } }')
            (root/'resources/assets/ad_config.json').write_text('{"inter_splash":{"id":"demo-id"}}')
            files=list(source_files(root))
            def no_walk(*args):
                raise AssertionError('Unnecessary repeated workspace directory traversal')
            with patch('apk_audit.facts.source_files',side_effect=no_walk), patch('apk_audit.facts.assets.source_files',side_effect=no_walk), patch('apk_audit.facts.strings.source_files',side_effect=no_walk), patch('apk_audit.tools.source_files',side_effect=no_walk):
                facts=build_facts(root,files=files).to_dict()
                tools=WorkspaceTools(root,facts,files=files)
                inventory=build_inventory(root,facts,{},files=files)
            self.assertEqual(facts['source']['package'],'demo.app')
            self.assertEqual(facts['assets']['json']['ad_config.json']['inter_splash']['id'],'demo-id')
            self.assertEqual(tools.classes[0]['name'],'demo.App')
            self.assertEqual(inventory['code_references']['inter_splash'][0]['line'],1)
