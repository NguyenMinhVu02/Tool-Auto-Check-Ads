import unittest


class TypoMatchTest(unittest.TestCase):
    def test_typo_in_document_name_matches_by_same_id(self):
        from apk_audit.placement_policy import config_key
        local = {'native_onboarding_fullscreen_2_2': {'id': 'X/1'}, 'native_onboarding_fullscreen_1_2': {'id': 'X/2'}}
        self.assertEqual(config_key('ative_onboarding_fullscreen_2_2', local, 'X/1', set()), 'native_onboarding_fullscreen_2_2')

    def test_no_match_without_same_id_or_when_ambiguous(self):
        from apk_audit.placement_policy import config_key
        local = {'native_onboarding_fullscreen_2_2': {'id': 'X/1'}}
        self.assertIsNone(config_key('ative_onboarding_fullscreen_2_2', local, 'X/9', set()))
        self.assertIsNone(config_key('native_onboarding_fullscreen_2_3', local, 'X/1', set()))
