import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from apk_audit import run
from apk_audit.agent import evaluate
from apk_audit.contracts import Rule
from apk_audit.engines import ReplayEngine
from apk_audit.errors import AuditError
from apk_audit.facts import build_facts
from apk_audit.rules.loader import load_pack
from apk_audit.tools import WorkspaceTools
from apk_audit.fetch import validate_archive


class FrameworkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ws = self.root / 'workspace'
        (self.ws / 'resources/assets').mkdir(parents=True)
        (self.ws / 'sources/demo').mkdir(parents=True)
        (self.ws / 'smali/demo').mkdir(parents=True)
        (self.ws / 'resources/AndroidManifest.xml').write_text('''<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="demo.app"><application android:name="demo.App"><meta-data android:name="sample" android:value="abc"/><activity android:name=".Main"><intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter></activity></application></manifest>''')
        (self.ws / 'resources/assets/config.json').write_text('{"enabled": true}')
        (self.ws / 'sources/demo/App.java').write_text('package demo;\npublic class App {\n public void onCreate() {\n  Example.init();\n }\n}\n')
        (self.ws / 'smali/demo/App.smali').write_text('.class public Ldemo/App;\n.method public onCreate()V\n invoke-static {}, Ldemo/Example;->init()V\n.end method\n')
        self.pack = self.root / 'pack'
        (self.pack / 'rules').mkdir(parents=True)
        (self.pack / 'pack.yaml').write_text('name: demo\nversion: "1"\nschema_version: 2\n')

    def agent_rule(self):
        return Rule(id='EXAMPLE', title='Example', mode='agent', question='Inspect', verdict={'pass_when':'yes','fail_when':'no','unknown_when':'unclear'})

    def test_empty_pack_report_is_explicit(self):
        result = run(self.ws, rules=self.pack, out=self.root / 'out')
        self.assertEqual(result['summary']['total'], 0)
        self.assertIn('no_rules', result['warnings'])
        self.assertTrue((self.root / 'out/report.md').exists())
        self.assertFalse((self.ws / 'facts.json').exists())

    def test_facts_have_real_paths(self):
        facts = build_facts(self.ws).to_dict()
        self.assertEqual(facts['manifest']['application_file'], 'sources/demo/App.java')
        self.assertTrue(facts['manifest']['activities'][0]['is_launcher'])
        self.assertTrue(facts['assets']['json']['config.json']['enabled'])
        self.assertEqual(facts['source']['package'], 'demo.app')

    def test_nine_tools_and_locations(self):
        tools = WorkspaceTools(self.ws)
        self.assertEqual(tools.get_facts('manifest.package'), 'demo.app')
        self.assertEqual(tools.list_classes()['items'][0]['name'], 'demo.App')
        self.assertEqual(len(tools.search_classes('App')['items']), 1)
        self.assertEqual(tools.get_class(name='demo.App')['lines'][3]['line'], 4)
        self.assertIn('onCreate', tools.get_methods('demo.App')['items'][0]['text'])
        self.assertEqual(tools.get_smali('demo.App')['file'], 'smali/demo/App.smali')
        self.assertEqual(tools.xrefs_to(method='demo.Example.init')['items'][0]['line'], 3)
        self.assertEqual(tools.grep('Example', '*.java')['items'][0]['line'], 4)
        self.assertEqual(tools.read_lines('sources/demo/App.java', 4, 4)['lines'][0]['text'], '  Example.init();')

    def test_tools_reject_escape(self):
        tools = WorkspaceTools(self.ws)
        outside = self.root / 'secret'
        outside.write_text('secret')
        (self.ws / 'escape').symlink_to(outside)
        for name in ['../secret', str(outside), 'escape']:
            with self.assertRaises((ValueError, AuditError)):
                tools.read_lines(name)

    def test_facts_tool_rejects_oversized_response(self):
        tools = WorkspaceTools(self.ws, {'large': 'a'*70000, 'small': 'ok'})
        with self.assertRaises(ValueError):
            tools.get_facts()
        self.assertEqual(tools.get_facts('small'), 'ok')

    def test_duplicate_rule_rejected(self):
        (self.pack / 'rules/a.yaml').write_text('- {id: X, title: X, mode: static, check: manifest_meta, params: {key: sample}}\n- {id: X, title: X, mode: static, check: manifest_meta, params: {key: sample}}')
        with self.assertRaises(AuditError):
            load_pack(self.pack)

    def test_static_and_missing_document(self):
        (self.pack / 'rules/a.yaml').write_text('''- id: A
  title: sample
  mode: static
  check: manifest_meta
  params: {key: sample, equals: abc}
- id: B
  title: contract
  mode: static
  check: manifest_meta
  params: {key: sample, equals_doc: ads_scripts.value}
''')
        result = run(self.ws, rules=self.pack, out=self.root / 'out')
        self.assertEqual([f['status'] for f in result['findings']], ['PASS', 'SKIPPED'])

    def test_evidence_guardrails(self):
        for evidence, status in [([], 'UNKNOWN'), ([{'file':'sources/demo/App.java','line':999,'excerpt':'Example.init();'}], 'UNKNOWN'), ([{'file':'sources/demo/App.java','line':4,'excerpt':'Example.init();'}], 'FAIL')]:
            response = json.dumps({'rule_id':'EXAMPLE','status':'FAIL','evidence':evidence})
            finding, trace = evaluate(self.agent_rule(), WorkspaceTools(self.ws), ReplayEngine([response]), '')
            self.assertEqual(finding.status, status)
        response = json.dumps({'rule_id':'EXAMPLE','status':'PASS','evidence':[]})
        finding, _ = evaluate(self.agent_rule(), WorkspaceTools(self.ws), ReplayEngine([response]), '')
        self.assertEqual(finding.status, 'UNKNOWN')
        mixed = [{'file':'sources/demo/App.java','line':4,'excerpt':'Example.init();'},
                 {'file':'sources/demo/App.java','line':99,'excerpt':'Example.init();'}]
        finding, _ = evaluate(self.agent_rule(), WorkspaceTools(self.ws), ReplayEngine([json.dumps({'rule_id':'EXAMPLE','status':'FAIL','evidence':mixed})]), '')
        self.assertEqual((finding.status, finding.reason), ('UNKNOWN', 'unverified_evidence'))

    def test_invalid_evidence_can_be_repaired_once(self):
        wrong = {'rule_id': 'EXAMPLE', 'status': 'FAIL', 'evidence': [
            {'file': 'sources/demo/App.java', 'line': 5, 'excerpt': 'Example.init();'}]}
        fixed = {'rule_id': 'EXAMPLE', 'status': 'FAIL', 'evidence': [
            {'file': 'sources/demo/App.java', 'line': 4, 'excerpt': 'Example.init();'}]}
        class RecordingReplay(ReplayEngine):
            def __init__(self, responses):
                super().__init__(responses)
                self.prompts = []

            def run_agent(self, prompt, tools, max_tool_calls, timeout=600):
                self.prompts.append(prompt)
                return super().run_agent(prompt, tools, max_tool_calls, timeout)

        engine = RecordingReplay([json.dumps(wrong), json.dumps(fixed)])
        finding, trace = evaluate(self.agent_rule(), WorkspaceTools(self.ws), engine, 'DOC_MARKER')
        self.assertEqual(finding.status, 'FAIL')
        self.assertTrue(finding.evidence[0]['verified'])
        self.assertTrue(trace['attempts'][-1]['repair'])
        self.assertIn('DOC_MARKER', engine.prompts[1])

    def test_multiline_evidence_must_match_contiguous_source_at_cited_line(self):
        excerpt = ' public void onCreate() {\n  Example.init();\n }'
        for line, expected in [(3, 'FAIL'), (4, 'UNKNOWN')]:
            payload = {'rule_id': 'EXAMPLE', 'status': 'FAIL', 'evidence': [
                {'file': 'sources/demo/App.java', 'line': line, 'excerpt': excerpt}]}
            finding, _ = evaluate(self.agent_rule(), WorkspaceTools(self.ws), ReplayEngine([json.dumps(payload)]), '')
            self.assertEqual(finding.status, expected)

    def test_invalid_agent_output_and_wrong_rule(self):
        for responses in [['bad', 'bad'], [json.dumps({'rule_id':'OTHER','status':'PASS'})], [json.dumps({'rule_id':'EXAMPLE','status':'bogus'})], [json.dumps({'rule_id':'EXAMPLE','status':{}})]]:
            finding, _ = evaluate(self.agent_rule(), WorkspaceTools(self.ws), ReplayEngine(responses), '')
            self.assertEqual(finding.status, 'UNKNOWN')

    def test_archive_rejects_traversal(self):
        apk = self.root / 'bad.apk'
        with zipfile.ZipFile(apk, 'w') as z:
            z.writestr('AndroidManifest.xml', 'manifest')
            z.writestr('../escape', 'bad')
        with self.assertRaises(AuditError):
            validate_archive(apk)

if __name__ == '__main__':
    unittest.main()
