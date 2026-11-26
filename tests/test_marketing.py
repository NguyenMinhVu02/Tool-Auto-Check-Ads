import unittest

from apk_audit.marketing import build_marketing_summary, marketing_markdown


class MarketingSummaryTests(unittest.TestCase):
    def summary(self, local, findings=()):
        documents = {'ads_scripts': {'placements': [
            {'name': 'inter_splash', 'ad_type': 'interstitial', 'id': 'ca-app-pub-1/1', 'state': 'active'},
            {'name': 'banner_splash', 'ad_type': 'banner', 'id': 'ca-app-pub-1/2', 'state': 'active'},
            {'name': 'native_language_1', 'ad_type': 'native', 'id': 'ca-app-pub-1/3', 'state': 'disabled'},
            {'name': 'inter_welcome_back', 'ad_type': 'interstitial', 'id': 'ca-app-pub-1/4', 'state': 'active'}]}}
        facts = {'assets': {'json': {'ad_config.json': local}}}
        return build_marketing_summary(documents, facts, {'optional_placements': []}, list(findings))

    def test_wrong_and_missing_ids_are_listed_per_screen(self):
        result = self.summary({'inter_splash': {'id': 'ca-app-pub-1/9'}, 'banner_splash': {'id': 'ca-app-pub-1/2'}},
                              [{'rule_id': 'ADS_SPLASH_PLACEMENT', 'status': 'PASS', 'marketing_summary': 'Splash ổn.'}])
        problems = {(p['name'], p['status']) for p in result['id_problems']}
        self.assertEqual(problems, {('inter_splash', 'Sai ID: app khác ADS SCRIPTS'),
                                    ('inter_welcome_back', 'Thiếu: app chưa khai báo vị trí này')})
        splash = result['screens'][0]
        self.assertEqual((splash['level'], splash['id_issues'], splash['flow_label']), ('issue', 1, 'Đạt'))
        self.assertEqual(splash['explanation'], 'Splash ổn.')
        language = result['screens'][1]
        self.assertFalse(language['placements'][0]['problem'])
        self.assertIsNone(result['publisher_note'])

    def test_other_admob_account_and_unknown_flow_are_explained(self):
        result = self.summary({'inter_splash': {'id': 'ca-app-pub-7/1'}},
                              [{'rule_id': 'ADS_WELCOME_RESUME', 'status': 'UNKNOWN', 'marketing_summary': 'Nghi lỗi.'}])
        self.assertIn('pub-7', result['publisher_note'])
        welcome = result['screens'][3]
        self.assertEqual(welcome['flow_level'], 'check')
        self.assertIn('cần dev xem lại', welcome['explanation'])
        self.assertIn('Nghi lỗi.', welcome['explanation'])
        text = '\n'.join(marketing_markdown(result))
        self.assertIn('Tóm tắt cho Tester', text)
        self.assertIn('❌', text)

    def test_screen_logic_and_requirements_reach_summary_and_markdown(self):
        report = {'load': 'Tải khi mở app', 'show': 'Hiện khi sẵn sàng', 'verified': True,
                  'requirements': [{'text': 'Có gate', 'status': 'ok', 'note': 'đúng'}, {'text': 'Thoát khi lỗi', 'status': 'issue', 'note': 'kẹt'}]}
        result = self.summary({'inter_splash': {'id': 'ca-app-pub-1/1'}},
                              [{'rule_id': 'ADS_SPLASH_PLACEMENT', 'status': 'FAIL', 'screen_report': report}])
        splash = result['screens'][0]
        self.assertEqual(splash['logic'], {'load': 'Tải khi mở app', 'show': 'Hiện khi sẵn sàng', 'verified': True})
        self.assertEqual([r['status'] for r in splash['requirements']], ['ok', 'issue'])
        text = '\n'.join(marketing_markdown(result))
        self.assertIn('Tải quảng cáo: Tải khi mở app', text)
        self.assertIn('❌ Thoát khi lỗi — kẹt', text)
        self.assertIsNone(result['screens'][1]['logic'])

    def test_quota_and_engine_errors_get_plain_explanations_and_checklist_stays_visible(self):
        placeholder = {'load': '', 'show': '', 'verified': False,
                       'requirements': [{'text': 'Có gate', 'status': 'unknown', 'note': ''}]}
        result = self.summary({}, [
            {'rule_id': 'ADS_ONBOARDING_PLACEMENT', 'status': 'UNKNOWN', 'reason': 'repair_error',
             'reasoning': "Codex CLI lỗi: You've hit your usage limit. Try again at 2:19 PM.", 'screen_report': placeholder},
            {'rule_id': 'ADS_WELCOME_RESUME', 'status': 'UNKNOWN', 'reason': 'engine_error', 'reasoning': 'Codex CLI lỗi: exit 1',
             'screen_report': placeholder}])
        onboarding, welcome = result['screens'][2], result['screens'][3]
        self.assertIn('hết hạn mức', onboarding['explanation'])
        self.assertIn('lỗi khi gọi AI', welcome['explanation'])
        self.assertEqual([r['status'] for r in onboarding['requirements']], ['unknown'])
        self.assertEqual(len(welcome['requirements']), 1)

    def test_document_name_with_known_alias_matches_the_app_placement(self):
        result = self.summary({'inter_welcome': {'id': 'ca-app-pub-1/4'}, 'inter_splash': {'id': 'ca-app-pub-1/1'},
                               'banner_splash': {'id': 'ca-app-pub-1/2'}})
        welcome = result['screens'][3]
        self.assertEqual([p['name'] for p in welcome['placements']], ['inter_welcome_back'])   # one row, no duplicate
        row = welcome['placements'][0]
        self.assertEqual((row['problem'], row['app_name'], row['app_id']), (False, 'inter_welcome', 'ca-app-pub-1/4'))
        self.assertIn('app đặt tên inter_welcome', row['status'])
        self.assertFalse([p for p in result['id_problems'] if p['name'] == 'inter_welcome_back'])
        wrong = self.summary({'inter_welcome': {'id': 'ca-app-pub-1/9'}})
        self.assertEqual([p['status'] for p in wrong['id_problems'] if 'welcome' in p['name']],
                         ['Sai ID: app khác ADS SCRIPTS (app đặt tên inter_welcome)'])

    def test_same_family_under_another_index_is_a_naming_question_not_plain_missing(self):
        documents = {'ads_scripts': {'placements': [
            {'name': 'native_onboarding_fullscreen_1_2', 'ad_type': 'native', 'id': 'ca-app-pub-1/5', 'state': 'active'},
            {'name': 'native_other', 'ad_type': 'native', 'id': 'ca-app-pub-1/6', 'state': 'active'}]}}
        facts = {'assets': {'json': {'ad_config.json': {'native_onboarding_fullscreen_1_3': {'id': 'ca-app-pub-1/7'}}}}}
        result = build_marketing_summary(documents, facts, {'optional_placements': []}, [])
        rows = {p['name']: p for s in result['screens'] for p in s['placements']}
        row = rows['native_onboarding_fullscreen_1_2']
        self.assertTrue(row['status'].startswith('Chưa khớp tên'))
        self.assertEqual(row['candidates'], ['native_onboarding_fullscreen_1_3'])
        self.assertIn('cần xác nhận', row['status'])


if __name__ == '__main__':
    unittest.main()
