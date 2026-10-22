from pathlib import Path
import tempfile
import unittest

from apk_audit.slicer import Slicer, parse_methods


class SlicerTests(unittest.TestCase):
    def test_methods_are_found_with_braces_in_strings_and_comments_ignored(self):
        lines = ['class A {', '    @Override', '    public void onCreate() {', '        s = "}{"; // }', '        if (x) { y(); }',
                 '    }', '    int f(int a) { return a; }', '}']
        found = {m['name']: (m['start'], m['end']) for m in parse_methods(lines)}
        self.assertEqual(found, {'onCreate': (2, 6)})   # the one-line method has no block opener at line end

    def write(self, root, relative, text):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_slice_takes_screen_methods_with_real_line_numbers_follows_helpers_and_skips_libraries(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            screen = self.write(root, 'sources/com/app/ui/LanguageActivity.java',
                                'package com.app.ui;\nimport com.app.ads.H;\nclass LanguageActivity {\n'
                                '    public void onCreate() {\n        H.loadNative(this, "native_language_1");\n        new Obs(this);\n    }\n'
                                '    void unrelated() {\n        int x = 1;\n    }\n}\n')
            helper = self.write(root, 'sources/com/app/ads/H.java',
                                'package com.app.ads;\nclass H {\n    static void loadNative(Object a, String k) {\n        postValue(k);\n    }\n'
                                '    static void other() {\n        int y = 2;\n    }\n}\n')
            obs = self.write(root, 'sources/com/app/ui/Obs.java', 'package com.app.ui;\nclass Obs {\n    Obs(Object o) { o.observe(); }\n}\n')
            lib = self.write(root, 'sources/com/google/Ads.java', 'class Ads {\n    void load() {\n        loadAd("native_language_1");\n    }\n}\n')
            facts = {'source': {'package': 'com.app'}, 'manifest': {'application_class': 'com.app.App', 'activities': [
                {'name': 'com.app.ui.LanguageActivity', 'file': 'sources/com/app/ui/LanguageActivity.java'},
                {'name': 'com.app.ui.WelcomeActivity', 'file': 'sources/com/app/ui/WelcomeActivity.java'}]}}
            slicer = Slicer(root, facts, [screen, helper, obs, lib], ['native_language_1'])
            text = slicer.build('language')
            self.assertIn('// sources/com/app/ui/LanguageActivity.java:4-7 (onCreate)', text)
            self.assertIn('5|         H.loadNative(this, "native_language_1");', text)       # real line numbers
            self.assertIn('loadNative', text)                                                    # one hop into the helper
            self.assertIn('Obs.java', text)                                                      # `new Obs(` followed
            self.assertNotIn('unrelated', text)
            self.assertNotIn('other()', text)
            self.assertNotIn('google', text)                                                     # libraries are noise
            missing = slicer.build('welcome')
            self.assertIn('KHÔNG CÓ MÃ: com.app.ui.WelcomeActivity', missing)


if __name__ == '__main__':
    unittest.main()
