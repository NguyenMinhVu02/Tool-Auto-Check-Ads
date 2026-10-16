import tempfile
import unittest
from pathlib import Path

from apk_audit.documents import load_document
from apk_audit.errors import AuditError


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def save(self, name, content):
        path = self.root / name
        path.write_text(content, encoding="utf-8-sig")
        return path

    def test_ads_scripts_spreadsheet_keeps_placements_and_app_id(self):
        path = self.save("ads.csv", "STT,Ads type,Name,ID,Mô tả,Description,Format,Note\n"
                         "1,inter,inter_splash,ad-1,when opening,,interstitial,first\n"
                         "2,native,native_lang,ad-2,,,,\n"
                         ",,App ID,app-1,,,,\n"
                         ",,Note,,reload after navigation,,,\n")
        result = load_document(path, "ads_scripts")
        self.assertEqual([p["name"] for p in result["placements"]], ["inter_splash", "native_lang"])
        self.assertEqual(result["placements"][0]["ad_type"], "interstitial")
        self.assertEqual(result["placements"][0]["line"], 2)
        self.assertEqual(result["app_id"], "app-1")
        self.assertIn("reload after navigation", result["notes"])

    def test_working_spreadsheet_keeps_status_as_document_data(self):
        path = self.save("working.csv", "Phase 2,Task,Task Detail,Document,PIC,Deadline,Status\n"
                         "Phase 1,Ads,Verify placement,link,owner,today,FALSE\n")
        result = load_document(path, "checklist")
        self.assertEqual(result["checklist_rows"][0]["detail"], "Verify placement")
        self.assertEqual(result["checklist_rows"][0]["status"], "FALSE")

    def test_key_value_csv_still_supported_and_duplicate_rejected(self):
        self.assertEqual(load_document(self.save("simple.csv", "key,value\npackage,demo.app\n")), {"package": "demo.app"})
        with self.assertRaises(AuditError):
            load_document(self.save("duplicate.csv", "key,value\na,1\na,2\n"))

    def test_unknown_spreadsheet_reports_clear_error(self):
        with self.assertRaisesRegex(AuditError, "không đúng mẫu"):
            load_document(self.save("wrong.csv", "foo,bar\na,b\n"), "ads_scripts")

    def test_source_line_survives_multiline_spreadsheet_cell(self):
        path = self.save("ads.csv", 'STT,Ads type,Name,ID,Mô tả,Description,Format,Note\n'
                         '1,native,native_first,id-1,"first\nsecond",,,\n'
                         '2,native,native_second,id-2,,,,\n')
        result = load_document(path, "ads_scripts")
        self.assertEqual([row["line"] for row in result["placements"]], [2, 4])
