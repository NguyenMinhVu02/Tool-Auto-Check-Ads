import tempfile
import unittest
from pathlib import Path

from apk_audit.inventory import build_inventory, inventory_observations


class InventoryTests(unittest.TestCase):
    def test_compare_ids_and_locate_java_literals_without_treating_absence_as_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "sources/demo/App.java"
            source.parent.mkdir(parents=True)
            source.write_text('class App { String slot = "inter_splash"; String config = "ad_config_debug.json"; }\n')
            facts = {"assets": {"json": {"ad_config.json": {
                "inter_splash": {"id": "id-1"}, "native_extra": {"id": "id-extra"}}}}}
            docs = {"ads_scripts": {"placements": [
                {"name": "inter_splash", "id": "id-1"}, {"name": "inter_onboarding", "id": "id-2"}]}}
            result = build_inventory(root, facts, docs)
            self.assertEqual(result["matching_ids"], ["inter_splash"])
            self.assertEqual(result["missing_local"], [])
            self.assertEqual(result["optional_placements"], ["inter_onboarding"])
            self.assertEqual(result["extra_local"], ["native_extra"])
            self.assertEqual(result["code_references"]["inter_splash"][0]["line"], 1)
            self.assertEqual(result["config_references"]["ad_config_debug.json"][0]["line"], 1)
            self.assertNotIn("inter_onboarding", result["code_references"])
            self.assertNotIn("Thiếu trong config local: inter_onboarding", inventory_observations(result))

    def test_disabled_and_uncertain_contract_slots_are_not_missing_or_wrong_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            facts = {'assets': {'json': {'ad_config.json': {
                'open_resume': {'id': 'local-old', 'isEnable': False},
                'native_uncertain': {'id': 'local-other'}}}}}
            docs = {'ads_scripts': {'placements': [
                {'name': 'open_resume', 'id': 'doc-old', 'state': 'disabled'},
                {'name': 'native_uncertain', 'id': 'doc-other', 'state': 'unknown'},
                {'name': 'native_missing', 'id': 'wanted', 'state': 'active'}]}}
            result = build_inventory(root, facts, docs)
            self.assertEqual(result['missing_local'], ['native_missing'])
            self.assertEqual(result['mismatched_ids'], [])
            self.assertEqual(result['extra_local'], [])
            self.assertEqual(result['disabled_placements'], ['open_resume'])
            self.assertEqual(result['uncertain_placements'], ['native_uncertain'])
            self.assertEqual(result['integration_policy']['open_resume']['state'], 'disabled')

    def test_absent_open_resume_is_not_required_but_missing_document_is_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            supplied = build_inventory(root, {}, {'ads_scripts': {'placements': [
                {'name': 'native_lang', 'id': 'id-lang'}]}})
            missing = build_inventory(root, {}, {})
            self.assertEqual(supplied['integration_policy']['open_resume']['state'], 'not_required')
            self.assertEqual(missing['integration_policy']['open_resume']['state'], 'unknown')

    def test_optional_inter_is_not_extra_when_absent_from_script(self):
        with tempfile.TemporaryDirectory() as temp:
            result = build_inventory(Path(temp), {'assets': {'json': {'ad_config.json': {
                'inter_onboarding': {'id': 'optional-id'}}}}}, {'ads_scripts': {'placements': [
                    {'name': 'native_lang', 'id': 'id-lang'}]}})
            self.assertEqual(result['extra_local'], [])

    def test_package_and_app_id_match_documents(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            resource = root / 'resources/res/values/strings.xml'
            resource.parent.mkdir(parents=True)
            resource.write_text('<resources><string name="admob_app_id">app-123</string></resources>')
            facts = {'source': {'package': 'demo.app'}, 'manifest': {'meta_data': {
                'com.google.android.gms.ads.APPLICATION_ID': '@string/admob_app_id'}}, 'assets': {'json': {}}}
            docs = {'ads_scripts': {'placements': [], 'app_id': 'app-123'},
                    'checklist': {'checklist_rows': [{'task': 'Package name', 'detail': 'demo.app', 'document': ''}]}}
            result = build_inventory(root, facts, docs)
            self.assertTrue(result['package_match'])
            self.assertTrue(result['app_id_match'])
