from pathlib import Path
import tempfile
import unittest

from apk_audit.flow_map import build_flow_map


class FlowMapTests(unittest.TestCase):
    def test_screens_use_class_names_not_package_and_call_sites_stay_in_app_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app = root / 'sources/com/speak/language/app'
            app.mkdir(parents=True)
            (app / 'SplashActivity.java').write_text('class S {\n  void f() { AdsManager.loadNativeLanguage(this); }\n}\n')
            (app / 'LanguageActivity.java').write_text('class L {\n  void g() { title.setOnAdminAdToggleListener$default(a); }\n}\n')
            lib = root / 'sources/com/other'
            lib.mkdir(parents=True)
            (lib / 'Lib.java').write_text('class Lib { void x() { loadNativeFoo(); } }\n')
            facts = {'source': {'package': 'com.speak.language.app'}, 'manifest': {'activities': [
                {'name': 'com.speak.language.app.SplashActivity', 'file': 'sources/com/speak/language/app/SplashActivity.java'},
                {'name': 'com.speak.language.app.LanguageActivity', 'file': 'sources/com/speak/language/app/LanguageActivity.java'}]}}
            result = build_flow_map(root, facts)
            self.assertEqual(result['screens']['language']['activity'], 'LanguageActivity')
            self.assertEqual(result['screens']['splash']['activity'], 'SplashActivity')
            self.assertEqual(result['ad_call_sites']['sources/com/speak/language/app/SplashActivity.java'], [2])
            self.assertNotIn('sources/com/other/Lib.java', result['ad_call_sites'])


if __name__ == '__main__':
    unittest.main()
