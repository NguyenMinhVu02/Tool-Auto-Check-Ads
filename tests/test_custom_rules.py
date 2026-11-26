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

    def test_profile_reports_release_unless_manifest_is_debuggable(self):
        from apk_audit.rules import code_facts
        manifest = self.root / 'resources' / 'AndroidManifest.xml'
        manifest.parent.mkdir(parents=True)
        manifest.write_text('<manifest><application android:label="x"/></manifest>')
        code_facts._cache.clear()
        self.assertEqual(code_facts.code_profile(self.root)['build'], 'release')
        manifest.write_text('<manifest><application android:debuggable="true"/></manifest>')
        code_facts._cache.clear()
        self.assertEqual(code_facts.code_profile(self.root)['build'], 'debug')


if __name__ == '__main__':
    unittest.main()


class MediationRuleTests(unittest.TestCase):
    NETWORKS = {'applovin': {'name': 'AppLovin', 'adapter': ['com/google/ads/mediation/applovin'], 'sdk': ['com/applovin/sdk']},
                'mintegral': {'name': 'Mintegral', 'adapter': ['com/google/ads/mediation/mintegral'], 'sdk': ['com/mbridge/msdk']}}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'sources').mkdir()

    def add(self, package, cls='A'):
        folder = self.root / 'sources' / package
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f'{cls}.java').write_text(f'package {package.replace("/", ".")};\npublic class {cls} {{}}\n')

    def run_rule(self):
        rule = Rule('ADS_MEDIATION_ADAPTERS', 'Mediation', 'static', check='mediation_adapters', params={'networks': self.NETWORKS})
        return evaluate_static(rule, {}, {}, workspace=self.root)

    def test_no_mediation_is_not_applicable(self):
        self.add('com/example/app', 'MainActivity')
        self.assertEqual(self.run_rule().status, 'SKIPPED')

    def test_adapter_and_sdk_pass(self):
        self.add('com/google/ads/mediation/applovin', 'AppLovinMediationAdapter')
        self.add('com/applovin/sdk', 'AppLovinSdk')
        finding = self.run_rule()
        self.assertEqual(finding.status, 'PASS')
        self.assertEqual(finding.actual['ready'], ['AppLovin'])

    def test_adapter_without_sdk_fails_on_readable_code(self):
        for index in range(30):
            self.add('com/example/app', f'ReadableClassName{index}')
        self.add('com/google/ads/mediation/mintegral', 'MintegralMediationAdapter')
        finding = self.run_rule()
        self.assertEqual(finding.status, 'FAIL')
        self.assertEqual(finding.actual['adapter_without_sdk'], ['Mintegral'])

    def test_sdk_without_adapter_needs_review(self):
        self.add('com/applovin/sdk', 'AppLovinSdk')
        finding = self.run_rule()
        self.assertEqual(finding.status, 'UNKNOWN')
        self.assertEqual(finding.actual['sdk_without_adapter'], ['AppLovin'])


class SheetExportTests(unittest.TestCase):
    REPORT = {
        'package': 'com.demo.app', 'version_name': '1.2', 'summary': {'pass': 1, 'total': 2},
        'dev_view': {'groups': [{'key': 'splash', 'title': 'Màn Splash', 'rules': [
            {'rule_id': 'R1', 'title': 'Splash "inter"', 'status': 'FAIL', 'conclusion': 'Thiếu\\tpreload',
             'fixes': 'Thêm preload', 'locations': ['sources/A.java:3']},
            {'rule_id': 'R2', 'title': 'Banner', 'status': 'PASS', 'conclusion': 'Đúng', 'fixes': '', 'locations': []}]}]},
        'marketing': {'screens': [{'title': 'Màn Splash', 'placements': [
            {'name': 'inter_splash', 'ad_type': 'Inter', 'status': 'Sai ID', 'problem': True, 'document_id': 'a/1', 'app_id': 'a/2'}]}]},
    }

    def test_only_fails_rows_keep_kog_columns_and_escape_quotes(self):
        import csv, io
        from apk_audit.sheet_export import sheet_tsv
        text = sheet_tsv(self.REPORT, only_fails=True)
        rows = list(csv.reader(io.StringIO(text), delimiter='\t'))
        self.assertEqual(rows[0], ['ID', 'Function', 'Test Scenario Group', 'Actual', 'Test Condition',
                                   'Steps to Reproduce', 'Expected', 'Round 1', 'Round 2', 'Link Bug'])
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(len(row) == 10 for row in rows))
        self.assertEqual(rows[1][2], 'Splash "inter"')
        self.assertIn('sources/A.java:3', rows[1][3])
        self.assertEqual(rows[1][7], 'Fail')
        self.assertIn('a/1', rows[2][6])

    def test_partner_summary_lists_failures(self):
        from apk_audit.sheet_export import partner_summary
        text = partner_summary(self.REPORT)
        self.assertIn('Đạt **1/2 tiêu chí**', text)
        self.assertIn('[R1]', text)
        self.assertNotIn('[R2]', text)


class ConsentModuleTests(unittest.TestCase):
    PARAMS = {'required': ['ad_remote_config'], 'optional': [],
              'consent': {'module': ['com/itg/iaumodule', 'com/google/android/ump'],
                          'events': ['load_consent', 'agree_consent']}}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        app = self.root / 'sources' / 'com' / 'demo'
        app.mkdir(parents=True)
        for index in range(30):
            (app / f'ReadableClassName{index}.java').write_text('package com.demo;\nclass X {}\n')
        (app / 'Remote.java').write_text('package com.demo;\nclass Remote {\n  String k = "ad_remote_config";\n}\n')

    def run_rule(self):
        rule = Rule('ADS_REMOTE_KEYS', 'Keys', 'static', check='remote_config_keys', params=self.PARAMS)
        return evaluate_static(rule, {}, {}, workspace=self.root)

    def test_missing_consent_module_fails(self):
        finding = self.run_rule()
        self.assertEqual(finding.status, 'FAIL')
        self.assertIn('consent', finding.reasoning)

    def test_module_and_events_pass(self):
        module = self.root / 'sources' / 'com' / 'itg' / 'iaumodule'
        module.mkdir(parents=True)
        (module / 'ITGAdConsent.java').write_text('package com.itg.iaumodule;\nclass ITGAdConsent {}\n')
        (self.root / 'sources' / 'com' / 'demo' / 'Track.java').write_text(
            'package com.demo;\nclass Track {\n  String a = "new_load_consent_1";\n  String b = "new_agree_consent_1";\n}\n')
        finding = self.run_rule()
        self.assertEqual(finding.status, 'PASS')
        self.assertEqual(finding.actual['consent']['modules'], ['com/itg/iaumodule'])
        self.assertEqual(finding.actual['consent']['events'], ['load_consent', 'agree_consent'])

    def test_events_without_module_folder_still_pass(self):
        (self.root / 'sources' / 'com' / 'demo' / 'Track.java').write_text(
            'package com.demo;\nclass Track {\n  String a = "load_consent_2";\n}\n')
        finding = self.run_rule()
        self.assertEqual(finding.status, 'PASS')
        self.assertIn('agree_consent', finding.reasoning)

    def test_rule_without_consent_params_ignores_consent(self):
        rule = Rule('ADS_REMOTE_KEYS', 'Keys', 'static', check='remote_config_keys',
                    params={'required': ['ad_remote_config'], 'optional': []})
        self.assertEqual(evaluate_static(rule, {}, {}, workspace=self.root).status, 'PASS')


class DuplicateLoadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        src = self.root / 'sources' / 'app'
        src.mkdir(parents=True)
        (src / 'Splash.java').write_text('class Splash {\n  void a() {\n    ads.loadNativeLanguage(this);\n  }\n}\n')
        (src / 'Language.java').write_text('class Language {\n  void onResume() {\n    ads.loadNativeLanguage(this);\n'
                                           '    ads.loadNativeClick(this);\n  }\n}\n')

    def load(self, slot, file, line, anchor, trigger='enter', guarded=False):
        return {'slot': slot, 'file': f'sources/app/{file}', 'line': line, 'anchor': anchor, 'trigger': trigger, 'guarded': guarded}

    def findings(self, splash, language):
        return [{'rule_id': 'ADS_SPLASH_PLACEMENT', 'screen_report': {'loads': splash}},
                {'rule_id': 'ADS_LANGUAGE_PLACEMENT', 'screen_report': {'loads': language}}]

    def test_slot_loaded_on_two_screens_is_reported(self):
        from apk_audit.load_dedup import find_duplicate_loads
        result = find_duplicate_loads(self.findings(
            [self.load('native_language_1', 'Splash.java', 3, 'ads.loadNativeLanguage(this);')],
            [self.load('native_language_1', 'Language.java', 3, 'ads.loadNativeLanguage(this);')]), self.root)
        self.assertEqual([(i['slot'], i['kind']) for i in result['issues']], [('native_language_1', 'cross_screen')])

    def test_unguarded_resume_reload_is_reported_and_guarded_is_not(self):
        from apk_audit.load_dedup import find_duplicate_loads
        unguarded = find_duplicate_loads(self.findings([], [
            self.load('native_language_1_click', 'Language.java', 4, 'ads.loadNativeClick(this);', 'resume')]), self.root)
        self.assertEqual(unguarded['issues'][0]['kind'], 'reload_on_resume')
        guarded = find_duplicate_loads(self.findings([], [
            self.load('native_language_1_click', 'Language.java', 4, 'ads.loadNativeClick(this);', 'resume', True)]), self.root)
        self.assertEqual(guarded['issues'], [])

    def test_loads_with_wrong_anchor_are_ignored(self):
        from apk_audit.load_dedup import find_duplicate_loads
        result = find_duplicate_loads(self.findings(
            [self.load('native_language_1', 'Splash.java', 3, 'ads.loadNativeLanguage(this);')],
            [self.load('native_language_1', 'Language.java', 3, 'ads.somethingElse();')]), self.root)
        self.assertEqual(result['issues'], [])


class CaseListStaticTests(unittest.TestCase):
    """Splash ads notice, Language Done delay (information) and Uninstall setup."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'resources' / 'res' / 'values').mkdir(parents=True)
        (self.root / 'sources').mkdir()

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def run_check(self, check, facts=None, params=None):
        return evaluate_static(Rule('R', 'R', 'static', check=check, params=params or {}), facts or {}, {}, workspace=self.root)

    def test_splash_notice_found_in_strings(self):
        self.write('resources/res/values/strings.xml', '<resources>\n<string name="a">This action may contains ads</string>\n</resources>')
        finding = self.run_check('splash_ads_notice')
        self.assertEqual(finding.status, 'PASS')
        self.assertEqual(finding.actual, 'This action may contains ads')
        self.assertEqual(finding.evidence[0]['line'], 2)

    def test_splash_notice_other_wording_passes_with_note(self):
        self.write('resources/res/values/strings.xml', '<resources><string name="a">This action can contain ads</string></resources>')
        finding = self.run_check('splash_ads_notice')
        self.assertEqual(finding.status, 'PASS')
        self.assertIn('khác câu mẫu', finding.reasoning)

    def test_splash_notice_missing_fails(self):
        self.write('resources/res/values/strings.xml', '<resources><string name="a">Loading</string></resources>')
        self.assertEqual(self.run_check('splash_ads_notice').status, 'FAIL')

    def test_done_delay_reads_default_from_code(self):
        self.write('sources/com/app/c.java', 'x = D.x(new k("time_delay_show_language_done_button", 1500L));\n')
        self.write('sources/com/app/K.java', 'public static final long DEFAULT_TIME_DELAY_SHOW_LANGUAGE_DONE_BUTTON = 2000;\n')
        finding = self.run_check('language_done_delay')
        self.assertEqual(finding.status, 'PASS')
        self.assertEqual(finding.actual, {'milliseconds': [1500, 2000]})
        self.assertIn('1,5 giây', finding.reasoning)

    def test_done_delay_unknown_value_is_not_a_defect(self):
        self.write('sources/com/app/c.java', 'long t = rc.getLong("time_delay_show_language_done_button");\n')
        self.assertEqual(self.run_check('language_done_delay').status, 'SKIPPED')

    def manifest(self, *names):
        return {'manifest': {'activities': [{'name': 'com.app.' + n} for n in names]}}

    def test_uninstall_setup_pass(self):
        self.write('sources/com/app/ShortcutManager.java', 'new ShortcutInfo.Builder(context, "uninstall");\nload("native_confirm_uninstall");\n')
        finding = self.run_check('uninstall_setup', self.manifest('SplashActivity', 'UninstallAdActivity', 'UninstallFeedbackActivity'))
        self.assertEqual(finding.status, 'PASS')
        self.assertEqual(finding.actual['confirm_screen'], ['UninstallAdActivity'])
        self.assertEqual(finding.actual['survey_screen'], ['UninstallFeedbackActivity'])
        self.assertEqual(finding.actual['native_slots'], ['native_confirm_uninstall'])

    def test_uninstall_shortcut_inside_androidx_does_not_count(self):
        self.write('sources/androidx/core/content/pm/ShortcutInfoCompat.java', 'new ShortcutInfo.Builder(c, id);\n')
        finding = self.run_check('uninstall_setup', self.manifest('ConfirmUninstallActivity', 'SurveyActivity'))
        self.assertEqual(finding.status, 'FAIL')
        self.assertIn('shortcut', finding.reasoning)

    def test_uninstall_missing_survey_screen_fails(self):
        self.write('sources/com/app/S.java', 'new ShortcutInfo.Builder(context, "uninstall");\n')
        finding = self.run_check('uninstall_setup', self.manifest('ConfirmUninstallActivity'))
        self.assertEqual(finding.status, 'FAIL')
        self.assertIn('Survey', finding.reasoning)
