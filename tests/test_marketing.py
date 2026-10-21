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
        self.assertIn('Tóm tắt cho Marketing', text)
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


if __name__ == '__main__':
    unittest.main()
