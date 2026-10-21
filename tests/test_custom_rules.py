import json
from pathlib import Path
import tempfile
import unittest

from apk_audit.contracts import Rule
from apk_audit.rules.engine import evaluate_static


class CustomRuleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def config_rule(self):
        return Rule('ADS_CONFIG_FLAGS', 'Flags', 'static', check='ad_config_flags',
                    params={'files': ['ad_config.json'], 'ua_check_true': ['native_onboarding_fullscreen_*'],
                            'optional': ['inter_onboarding']})

    def facts(self, config):
        assets = self.root / 'resources' / 'assets'
        assets.mkdir(parents=True, exist_ok=True)
        (assets / 'ad_config.json').write_text(json.dumps(config, indent=2))
        return {'assets': {'json': {'ad_config.json': config}}}

    def test_ua_check_only_on_fullscreen_onboarding_and_enable_follows_document(self):
        facts = self.facts({
            'native_onboarding_fullscreen_1_3': {'id': 'a', 'isEnable': True},
            'inter_splash': {'id': 'b', 'isEnable': True, 'enableUaCheck': True},
            'native_language_1': {'id': 'c', 'isEnable': True},
            'inter_onboarding': {'id': 'd', 'isEnable': True}})
        documents = {'ads_scripts': {'placements': [
            {'name': 'native_language_1', 'id': 'c', 'state': 'disabled'},
            {'name': 'inter_onboarding', 'id': 'd', 'state': 'disabled'}]}}
        finding = evaluate_static(self.config_rule(), facts, documents, workspace=self.root)
        self.assertEqual(finding.status, 'FAIL')
        problems = {(i['placement'], i['field']) for i in finding.actual['issues']}
        self.assertEqual(problems, {('native_onboarding_fullscreen_1_3', 'enable_ua_check'),
                                    ('inter_splash', 'enable_ua_check'), ('native_language_1', 'isEnable')})
        self.assertTrue(all(e['line'] > 1 and e['excerpt'].startswith('"') for e in finding.evidence))
        self.assertIn('UA', finding.marketing_summary)

    def test_correct_flags_pass(self):
        facts = self.facts({'native_onboarding_fullscreen_2_4': {'id': 'a', 'isEnable': True, 'enable_ua_check': True},
                            'native_onboarding_fullscreen_1_2': {'id': 'a', 'isEnable': True, 'enableUaCheck': True},
                            'inter_splash': {'id': 'b', 'isEnable': True, 'enable_ua_check': False}})
        self.assertEqual(evaluate_static(self.config_rule(), facts, {}, workspace=self.root).status, 'PASS')

    def test_language_dev_toggle(self):
        rule = Rule('ADS_LANGUAGE_DEV_TOGGLE', 'Dev', 'static', check='language_dev_toggle',
                    params={'marker': 'setOnAdminAdToggleListener'})
        screen = self.root / 'sources' / 'app' / 'LanguageActivity.java'
        screen.parent.mkdir(parents=True)
        screen.write_text('class LanguageActivity {\n  void init() { }\n}\n')
        self.assertEqual(evaluate_static(rule, {}, {}, workspace=self.root).status, 'FAIL')
        screen.write_text('class LanguageActivity {\n  void init() { DevConfigViewExtKt.setOnAdminAdToggleListener$default(t); }\n}\n')
        finding = evaluate_static(rule, {}, {}, workspace=self.root)
        self.assertEqual((finding.status, finding.evidence[0]['line']), ('PASS', 2))
        screen.unlink()
        self.assertEqual(evaluate_static(rule, {}, {}, workspace=self.root).status, 'UNKNOWN')

    def write_source(self, relative, text):
        path = self.root / 'sources' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_remote_keys_require_literals_in_app_code_only(self):
        rule = Rule('K', 'Keys', 'static', check='remote_config_keys',
                    params={'required': ['ad_remote_config', 'on_show_dialog_consent'], 'optional': ['on_show_navigation_button']})
        facts = {'source': {'package': 'demo.app'}}
        self.write_source('demo/app/Remote.java', 'class R { static final String A = "ad_remote_config"; }\n')
        finding = evaluate_static(rule, facts, {}, workspace=self.root)
        self.assertEqual((finding.status, finding.actual['missing']), ('FAIL', ['on_show_dialog_consent']))
        # The code package often differs from the applicationId (templates, obfuscation): any source counts.
        self.write_source('com/template/Other.java', 'String B = "on_show_dialog_consent";\n')
        finding = evaluate_static(rule, facts, {}, workspace=self.root)
        self.assertEqual((finding.status, finding.evidence[0]['line']), ('PASS', 1))

    def test_interstitial_interval_must_equal_requirement(self):
        rule = Rule('I', 'Interval', 'static', check='interstitial_interval', params={'seconds': 35})
        facts = {'source': {'package': 'demo.app'}}
        self.assertEqual(evaluate_static(rule, facts, {}, workspace=self.root).status, 'UNKNOWN')
        self.write_source('demo/app/App.java', 'void f() {\n  cfg.setIntervalInterstitialAd(15);\n}\n')
        finding = evaluate_static(rule, facts, {}, workspace=self.root)
        self.assertEqual((finding.status, finding.actual, finding.evidence[0]['line']), ('FAIL', [15], 2))
        self.write_source('demo/app/App.java', 'cfg.setIntervalInterstitialAd(35);\n')
        self.assertEqual(evaluate_static(rule, facts, {}, workspace=self.root).status, 'PASS')

    def test_screen_names_check_manifest_activities(self):
        rule = Rule('S', 'Names', 'static', check='screen_class_names',
                    params={'screens': {'Splash': ['SplashActivity'], 'Onboarding': ['OnBoardingActivity', 'OnboardingActivity']}})
        facts = {'manifest': {'activities': [{'name': 'demo.SplashActivity'}, {'name': 'demo.IntroActivity'}]}}
        finding = evaluate_static(rule, facts, {}, workspace=self.root)
        self.assertEqual(finding.status, 'FAIL')
        self.assertIn('Onboarding', finding.actual['missing'][0])
        facts['manifest']['activities'][1]['name'] = 'demo.OnboardingActivity'
        self.assertEqual(evaluate_static(rule, facts, {}, workspace=self.root).status, 'PASS')

    def test_debug_config_must_use_matching_google_test_ids_and_release_must_not(self):
        rule = Rule('D', 'Debug ids', 'static', check='debug_test_ids', params={})
        test = 'ca-app-pub-3940256099942544/'
        debug = {'inter_splash': {'id': test + '1033173712', 'isEnable': True},
                 'banner_splash': {'id': test + '6300978111', 'isEnable': True},
                 'native_language_1': {'id': test + '2247696110', 'isEnable': True},
                 'open_resume': {'id': '', 'isEnable': False}}
        release = {'inter_splash': {'id': 'ca-app-pub-1/2', 'isEnable': True}}
        assets = self.root / 'resources' / 'assets'
        assets.mkdir(parents=True)
        (assets / 'ad_config_debug.json').write_text(json.dumps(debug, indent=2))
        (assets / 'ad_config.json').write_text(json.dumps(release, indent=2))
        facts = {'assets': {'json': {'ad_config_debug.json': debug, 'ad_config.json': release}}}
        self.assertEqual(evaluate_static(rule, facts, {}, workspace=self.root).status, 'PASS')
        debug['inter_splash']['id'] = 'ca-app-pub-1/2'                      # real ID in debug
        debug['banner_splash']['id'] = test + '1033173712'                  # interstitial unit on a banner
        debug['native_language_1']['id'] = ''                               # enabled but blank
        release['inter_splash']['id'] = test + '1033173712'                 # demo ID leaked to release
        (assets / 'ad_config_debug.json').write_text(json.dumps(debug, indent=2))
        (assets / 'ad_config.json').write_text(json.dumps(release, indent=2))
        finding = evaluate_static(rule, facts, {}, workspace=self.root)
        problems = {(i['file'], i['placement'], i['problem'].split(',')[0]) for i in finding.actual['issues']}
        self.assertEqual(finding.status, 'FAIL')
        self.assertEqual(problems, {('ad_config_debug.json', 'inter_splash', 'Debug đang dùng ID thật'),
                                    ('ad_config_debug.json', 'banner_splash', 'ID test sai loại quảng cáo (cần ID test của loại banner)'),
                                    ('ad_config_debug.json', 'native_language_1', 'Debug để trống ID dù đang bật'),
                                    ('ad_config.json', 'inter_splash', 'Bản release đang dùng ID test')})
        self.assertTrue(all(e['line'] > 1 for e in finding.evidence))

    def test_first_screens_must_lock_orientation_in_manifest(self):
        rule = Rule('O', 'Orientation', 'static', check='screen_orientation_lock',
                    params={'screens': {'Splash': ['SplashActivity'], 'Language': ['LanguageActivity']}})
        manifest = self.root / 'resources' / 'AndroidManifest.xml'
        manifest.parent.mkdir(parents=True)
        template = ('<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="demo"><application>\n'
                    '<activity android:name=".SplashActivity" android:screenOrientation="portrait"/>\n'
                    '<activity android:name="demo.LanguageActivity"{extra}/>\n</application></manifest>')
        manifest.write_text(template.format(extra=' android:configChanges="orientation"'))
        finding = evaluate_static(rule, {}, {}, workspace=self.root)
        self.assertEqual(finding.status, 'FAIL')
        issue = finding.actual['issues'][0]
        self.assertEqual((issue['placement'], issue['actual']), ('Language (LanguageActivity)', 'không khai báo · tự xử lý xoay bằng configChanges'))
        self.assertEqual(finding.evidence[0]['line'], 3)
        manifest.write_text(template.format(extra=' android:screenOrientation="sensorPortrait"'))
        self.assertEqual(evaluate_static(rule, {}, {}, workspace=self.root).status, 'PASS')
        manifest.write_text('<manifest')
        self.assertEqual(evaluate_static(rule, {}, {}, workspace=self.root).status, 'UNKNOWN')

    def test_obfuscated_dev_toggle_is_unknown_not_fail(self):
        rule = Rule('D', 'Dev', 'static', check='language_dev_toggle', params={'marker': 'setOnAdminAdToggleListener'})
        self.write_source('com/itg/devconfig/Dialog.java', 'class Dialog {}\n')
        self.write_source('com/itg/template/ui/language/LanguageActivity.java',
                          'class LanguageActivity {\n  void f() { tvTitle.setOnTouchListener(new p.a(h, t)); }\n}\n')
        finding = evaluate_static(rule, {}, {}, workspace=self.root)
        self.assertEqual((finding.status, finding.reason, finding.evidence[0]['line']), ('UNKNOWN', 'obfuscated', 2))
        (self.root / 'sources/com/itg/template/ui/language/LanguageActivity.java').write_text('class LanguageActivity {}\n')
        self.assertEqual(evaluate_static(rule, {}, {}, workspace=self.root).status, 'FAIL')

    def obfuscate(self, count=12):
        for index in range(count):
            self.write_source(f'x/{chr(97 + index)}.java', 'class A {}\n')   # one/two-letter class names

    def test_absence_of_names_is_inconclusive_when_code_is_obfuscated_but_literals_still_decide(self):
        interval = Rule('I', 'Interval', 'static', check='interstitial_interval', params={'seconds': 35})
        toggle = Rule('D', 'Dev', 'static', check='language_dev_toggle', params={'marker': 'setOnAdminAdToggleListener'})
        keys = Rule('K', 'Keys', 'static', check='remote_config_keys', params={'required': ['ad_remote_config']})
        self.write_source('demo/app/LanguageActivity.java', 'class LanguageActivity {}\n')
        self.write_source('demo/app/Other.java', 'class Other {}\n')
        facts = {'source': {'package': 'demo.app'}}
        low = {r.check: evaluate_static(r, facts, {}, workspace=self.root) for r in (interval, toggle, keys)}
        self.assertEqual({k: v.status for k, v in low.items()},
                         {'interstitial_interval': 'FAIL', 'language_dev_toggle': 'FAIL', 'remote_config_keys': 'FAIL'})
        self.obfuscate()
        from apk_audit.rules import code_facts
        code_facts._cache.clear()
        high = {r.check: evaluate_static(r, facts, {}, workspace=self.root) for r in (interval, toggle, keys)}
        self.assertEqual(high['interstitial_interval'].status, 'UNKNOWN')
        self.assertEqual(high['language_dev_toggle'].status, 'UNKNOWN')
        self.assertEqual(high['remote_config_keys'].status, 'FAIL')           # a missing string is still a defect
        self.assertEqual(high['remote_config_keys'].verification['confidence'], 'cao')
        self.assertEqual(high['interstitial_interval'].verification['confidence'], 'thấp')
        self.assertIn('mức làm rối cao', high['interstitial_interval'].verification['limits'])

    def test_missing_literal_is_unknown_when_app_code_failed_to_decompile(self):
        from apk_audit.rules import code_facts
        keys = Rule('K', 'Keys', 'static', check='remote_config_keys', params={'required': ['ad_remote_config']})
        self.write_source('demo/app/Broken.java', '/* JADX WARN: Code restructure failed: missing block */\nclass Broken {}\n')
        self.write_source('lib/Lib.java', '/* Method dump skipped */\nclass Lib {}\n')   # library gaps are not the app's
        code_facts._cache.clear()
        facts = {'source': {'package': 'demo.app'}}
        finding = evaluate_static(keys, facts, {}, workspace=self.root)
        self.assertEqual((finding.status, finding.reason), ('UNKNOWN', 'decompile_gaps'))
        (self.root / 'sources/demo/app/Broken.java').write_text('class Broken { String k = "ad_remote_config"; }\n')
        code_facts._cache.clear()
        self.assertEqual(evaluate_static(keys, facts, {}, workspace=self.root).status, 'PASS')


if __name__ == '__main__':
    unittest.main()
