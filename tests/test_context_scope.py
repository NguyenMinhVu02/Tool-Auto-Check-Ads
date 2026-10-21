import unittest

from apk_audit.context_scope import compact_prior, not_applicable_by_document, scope_documents, scope_inventory


class ContextScopeTests(unittest.TestCase):
    documents = {
        'ads_scripts': {'app_id': 'app', 'placements': [
            {'name': 'inter_splash', 'ad_type': 'interstitial', 'id': 'a', 'state': 'active', 'line': 3,
             'description_en': 'dup', 'strikethrough': False},
            {'name': 'banner_home', 'ad_type': 'banner', 'id': 'b', 'state': 'active', 'line': 4}]},
        'checklist': {'checklist_rows': [
            {'line': 2, 'task': 'Setup Remote Config', 'pic': 'BD', 'deadline': 'T'},
            {'line': 3, 'task': 'Sign contract', 'pic': 'BD'}]},
    }

    def test_placement_areas_keep_only_relevant_rows_in_compact_form(self):
        scoped = scope_documents(self.documents, 'splash')
        self.assertEqual([p['name'] for p in scoped['ads_scripts']['placements']], ['inter_splash'])
        self.assertNotIn('description_en', scoped['ads_scripts']['placements'][0])
        self.assertEqual(scoped['ads_scripts']['scope'], {'area': 'splash', 'kept': 1, 'total': 2})

    def test_general_areas_keep_every_placement_and_filter_checklist(self):
        scoped = scope_documents(self.documents, 'remote_config')
        self.assertEqual(len(scoped['ads_scripts']['placements']), 2)
        self.assertEqual(scoped['checklist']['checklist_rows'], [{'line': 2, 'task': 'Setup Remote Config'}])

    def test_inventory_lists_follow_scope_and_references_group_by_file(self):
        inventory = {'mismatched_ids': ['inter_splash', 'banner_home'], 'package_match': True,
                     'code_references': {'inter_splash': [{'file': 'A.java', 'line': n} for n in range(5)],
                                         'banner_home': [{'file': 'B.java', 'line': 1}]}}
        scoped = scope_inventory(inventory, 'splash')
        self.assertEqual(scoped['mismatched_ids'], ['inter_splash'])
        self.assertEqual(scoped['code_references_by_file'], {'A.java': {'inter_splash': [0, 1, 2]}})
        self.assertTrue(scoped['package_match'])

    def test_prior_keeps_verdict_and_short_excerpts(self):
        prior = compact_prior([{'rule_id': 'R', 'status': 'FAIL', 'reasoning': 'x' * 2000,
                                'claims': [{'statement': 's', 'kind': 'violation', 'evidence_indices': [0]}],
                                'evidence': [{'file': 'A.java', 'line': 1, 'excerpt': 'y' * 500}],
                                'verification': {'big': 'z' * 5000}}])
        self.assertEqual(len(prior[0]['reasoning']), 700)
        self.assertEqual(len(prior[0]['evidence'][0]['excerpt']), 160)
        self.assertNotIn('verification', prior[0])

    def test_welcome_is_skipped_only_when_document_marks_it_unused(self):
        def docs(*rows):
            return {'ads_scripts': {'placements': [{'name': n, 'state': s} for n, s in rows]}}
        self.assertIn('inter_welcome_back', not_applicable_by_document(docs(('inter_welcome_back', 'disabled'), ('inter_splash', 'active')), 'welcome'))
        self.assertIn('không có placement', not_applicable_by_document(docs(('inter_splash', 'active')), 'welcome'))
        self.assertIsNone(not_applicable_by_document(docs(('inter_welcome_back', 'active')), 'welcome'))
        self.assertIsNone(not_applicable_by_document(docs(('native_welcome', 'unknown')), 'welcome'))
        self.assertIsNone(not_applicable_by_document({}, 'welcome'))          # no document: audit as usual
        self.assertIsNone(not_applicable_by_document(docs(('inter_splash', 'disabled')), 'splash'))  # core screens never skipped


if __name__ == '__main__':
    unittest.main()
