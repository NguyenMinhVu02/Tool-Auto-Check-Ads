import tempfile
import unittest
from pathlib import Path

from apk_audit.documents import list_sheets, load_document
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

    def test_vietnamese_ads_header_keeps_note_and_layout_columns(self):
        path = self.save('ads-vi.csv', 'STT,Ads type,Tên ,ID,Mô tả TV,Mô tả TA,Note,Layout\n'
                         '1,native,Native_full,id-1,Hiện native,Show native,keep note,UI 1\n'
                         ',,App ID,app-1,,,,\n')
        result = load_document(path, 'ads_scripts')
        placement = result['placements'][0]
        self.assertEqual(placement['name'], 'Native_full')
        self.assertEqual(placement['description'], 'Hiện native')
        self.assertEqual(placement['note'], 'keep note')
        self.assertEqual(placement['format'], 'UI 1')
        self.assertEqual(result['app_id'], 'app-1')

    def test_working_content_detail_format(self):
        path = self.save('working.csv', ',Content,Detail,PIC\n'
                         '1,Package name,demo.app,Infinity\n'
                         '2,Adjust token,sample-token,Owner\n')
        rows = load_document(path, 'checklist')['checklist_rows']
        self.assertEqual(rows[0]['task'], 'Package name')
        self.assertEqual(rows[0]['detail'], 'demo.app')
        self.assertEqual(rows[0]['pic'], 'Infinity')
        self.assertEqual(rows[1]['detail'], 'sample-token')

    def test_ads_columns_can_be_reordered_without_changing_identifiers(self):
        path = self.save('ads.csv', 'ID, Name ,Ads Type,STT\nid-1,Native_First,native,1\n')
        result = load_document(path, 'ads_scripts')
        self.assertEqual(result['placements'][0]['name'], 'Native_First')
        self.assertEqual(result['placements'][0]['id'], 'id-1')

    def test_csv_ads_title_before_header_keeps_physical_source_lines(self):
        path = self.save('ads-title.csv', 'ADS SCRIPTS,,,,\n'
                         ',,,,\n'
                         'STT,Ads type,Name,ID,Mô tả\n'
                         '1,native,native_first,id-1,"first\nsecond"\n'
                         '2,open,open_resume,id-2,Resume\n')
        result = load_document(path, 'ads_scripts')
        self.assertEqual([row['name'] for row in result['placements']], ['native_first', 'open_resume'])
        self.assertEqual([row['line'] for row in result['placements']], [4, 6])
        self.assertEqual(result['placements'][0]['description'], 'first\nsecond')
        self.assertEqual(result['placements'][0]['id'], 'id-1')
        self.assertEqual(result['placements'][1]['state'], 'unknown')

    def test_csv_working_title_before_header_is_not_a_checklist_row(self):
        path = self.save('working-title.csv', 'Working file,,\n'
                         'Content,Detail,PIC\n'
                         'Package name,demo.app,Owner\n')
        rows = load_document(path, 'checklist')['checklist_rows']
        self.assertEqual(rows, [{'line': 3, 'phase': '', 'task': 'Package name',
                                'detail': 'demo.app', 'document': '', 'pic': 'Owner',
                                'deadline': '', 'status': ''}])

    def test_csv_header_search_accepts_line_40_but_not_41(self):
        for title_lines in (39, 40):
            with self.subTest(title_lines=title_lines):
                path = self.save('bounded.csv', 'Title,,\n' * title_lines +
                                 'Ads type,Name,ID\nnative,native_first,id-1\n')
                if title_lines == 39:
                    doc = load_document(path, 'ads_scripts')
                    self.assertEqual(doc['placements'][0]['line'], 41)
                else:
                    with self.assertRaisesRegex(AuditError, 'không đúng mẫu'):
                        load_document(path, 'ads_scripts')

    def test_csv_working_header_is_not_accepted_as_ads_scripts(self):
        path = self.save('wrong-slot.csv', 'Working file,,\nContent,Detail,PIC\n'
                         'Package name,demo.app,Owner\n')
        with self.assertRaisesRegex(AuditError, 'ADS SCRIPTS'):
            load_document(path, 'ads_scripts')

    def test_ads_status_survives_csv_and_empty_open_resume_is_disabled(self):
        path = self.save('states.csv', 'Ads type,Name,ID,Status\n'
                         'open,open_resume,,Enabled\n'
                         'native,native_old,id-old,Không dùng\n'
                         'native,native_current,id-new,Enabled\n')
        rows = load_document(path, 'ads_scripts')['placements']
        self.assertEqual([row.get('state') for row in rows], ['disabled', 'disabled', 'active'])
        self.assertEqual(rows[0]['state_reason'], 'empty_id')

    def test_csv_cannot_claim_open_resume_is_active_from_lost_formatting(self):
        doc = load_document(self.save('plain.csv', 'Ads type,Name,ID\n'
                            'open,open_resume,id-open\n'), 'ads_scripts')
        self.assertEqual(doc['placements'][0].get('state'), 'unknown')
        self.assertIn('CSV', ' '.join(doc.get('warnings', [])))

    def test_explicit_strike_or_highlight_disables_json_placement(self):
        import json
        path = self.root / 'marked.json'
        path.write_text(json.dumps({'placements': [
            {'name': 'open_resume', 'id': 'id-open', 'enabled': True, 'strikethrough': True},
            {'name': 'native_old', 'id': 'id-old', 'highlighted': True},
            {'name': 'native_new', 'id': 'id-new', 'enabled': True}]}), encoding='utf-8')
        rows = load_document(path, 'ads_scripts')['placements']
        self.assertEqual([row.get('state') for row in rows], ['disabled', 'disabled', 'active'])

    def test_xlsx_marks_id_fill_and_name_strike_without_disabling_plain_ids(self):
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        workbook = Workbook()
        cover = workbook.active
        cover.title = 'Cover'
        cover.append(['Partner documents'])
        sheet = workbook.create_sheet('ADS SCRIPTS')
        sheet.append(['ADS SCRIPTS'])
        sheet.append(['Ads type', 'Name', 'ID'])
        sheet.append(['open', 'open_resume', 'id-open'])
        sheet.append(['native', 'native_retired', 'id-old'])
        sheet.append(['native', 'native_active', 'id-new'])
        sheet['C3'].fill = PatternFill('solid', fgColor='FFFF00')
        sheet['B4'].font = Font(strike=True)
        path = self.root / 'ads.xlsx'
        workbook.save(path)
        doc = load_document(path, 'ads_scripts')
        self.assertEqual([row['state'] for row in doc['placements']], ['disabled', 'disabled', 'active'])
        self.assertEqual([row['line'] for row in doc['placements']], [3, 4, 5])
        self.assertEqual(doc['sheet'], 'ADS SCRIPTS')
        self.assertTrue(doc['formatting_available'])

    def test_xlsx_plain_open_resume_is_active_but_formula_id_is_unknown(self):
        from openpyxl import Workbook
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(['Ads type', 'Name', 'ID'])
        sheet.append(['open', 'open_resume', 'id-open'])
        sheet.append(['native', 'native_formula', '=A1'])
        path = self.root / 'formula.xlsx'
        workbook.save(path)
        rows = load_document(path, 'ads_scripts')['placements']
        self.assertEqual([row['state'] for row in rows], ['active', 'unknown'])

    def test_xlsx_multi_app_workbook_requires_and_honours_sheet_choice(self):
        from openpyxl import Workbook
        workbook = Workbook()
        workbook.active.title = 'Index'
        workbook.active.append(['Mục lục'])
        for title, name in (('App A', 'banner_a'), ('App B', 'banner_b')):
            sheet = workbook.create_sheet(title)
            sheet.append(['ADS SCRIPTS ' + title])
            sheet.append(['Ads type', 'Name', 'ID'])
            sheet.append(['banner', name, 'id-' + name])
        hidden = workbook.create_sheet('Hidden')
        hidden.append(['Ads type', 'Name', 'ID'])
        hidden.sheet_state = 'hidden'
        path = self.root / 'multi.xlsx'
        workbook.save(path)
        self.assertEqual(list_sheets(path, 'ads_scripts'), ['App A', 'App B'])
        with self.assertRaisesRegex(AuditError, 'App A, App B'):
            load_document(path, 'ads_scripts')
        document = load_document(path, 'ads_scripts', sheet='App B')
        self.assertEqual(document['sheet'], 'App B')
        self.assertEqual([row['name'] for row in document['placements']], ['banner_b'])
        for missing in ('Hidden', 'Nope'):
            with self.subTest(sheet=missing), self.assertRaisesRegex(AuditError, 'không có sheet'):
                load_document(path, 'ads_scripts', sheet=missing)

    def test_xlsx_conditional_color_is_not_mistaken_for_plain_active_id(self):
        from openpyxl import Workbook
        from openpyxl.formatting.rule import CellIsRule
        from openpyxl.styles import PatternFill
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(['Ads type', 'Name', 'ID'])
        sheet.append(['open', 'open_resume', 'id-open'])
        sheet.conditional_formatting.add('C2', CellIsRule(operator='equal', formula=['"id-open"'],
                                         fill=PatternFill('solid', fgColor='FFFF00')))
        path = self.root / 'conditional.xlsx'
        workbook.save(path)
        doc = load_document(path, 'ads_scripts')
        self.assertEqual(doc['placements'][0]['state'], 'unknown')

    def test_xlsx_working_file_and_ambiguous_ads_sheets(self):
        from openpyxl import Workbook
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(['Content', 'Detail', 'PIC'])
        sheet.append(['Package name', 'demo.app', 'Owner'])
        path = self.root / 'working.xlsx'
        workbook.save(path)
        rows = load_document(path, 'checklist')['checklist_rows']
        self.assertEqual(rows[0]['detail'], 'demo.app')
        for name in ['ADS A', 'ADS B']:
            workbook.create_sheet(name).append(['Ads type', 'Name', 'ID'])
        workbook.save(path)
        with self.assertRaisesRegex(AuditError, 'nhiều sheet'):
            load_document(path, 'ads_scripts')
