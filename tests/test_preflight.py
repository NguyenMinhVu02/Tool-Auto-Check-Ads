import unittest

from apk_audit.preflight import DocumentMismatch, check_documents


def docs(*ids, state='active'):
    return {'ads_scripts': {'placements': [{'name': f'p{i}', 'id': ad, 'state': state} for i, ad in enumerate(ids)]}}


def facts(*ids):
    return {'source': {'package': 'demo.app'},
            'assets': {'json': {'ad_config.json': {f'p{i}': {'id': ad} for i, ad in enumerate(ids)}}}}


class PreflightTests(unittest.TestCase):
    def test_other_admob_account_blocks_with_both_publishers_named(self):
        result = check_documents(docs('ca-app-pub-111/1', 'ca-app-pub-111/2'), facts('ca-app-pub-222/1'), {})
        self.assertEqual(result['level'], 'block')
        self.assertEqual((result['document_publishers'], result['app_publishers']), (['111'], ['222']))
        self.assertIn('pub-222', result['reasons'][0]['message'])

    def test_shared_publisher_demo_ids_and_missing_documents_do_not_block(self):
        self.assertEqual(check_documents(docs('ca-app-pub-111/1'), facts('ca-app-pub-111/9'), {})['level'], 'ok')
        demo = 'ca-app-pub-3940256099942544/1033173712'
        self.assertEqual(check_documents(docs('ca-app-pub-111/1'), facts(demo), {})['level'], 'ok')   # test IDs say nothing about the account
        self.assertEqual(check_documents({}, facts('ca-app-pub-222/1'), {})['level'], 'ok')
        self.assertEqual(check_documents(docs('ca-app-pub-111/1', state='disabled'), facts('ca-app-pub-222/1'), {})['level'], 'ok')

    def test_package_and_app_id_mismatch_block(self):
        result = check_documents({'checklist': {'checklist_rows': []}}, facts(), {'package_match': False, 'app_id_match': False})
        self.assertEqual([r['code'] for r in result['reasons']], ['package', 'app_id'])

    def test_exception_carries_details_and_cli_hint(self):
        error = DocumentMismatch({'level': 'block', 'reasons': [{'code': 'x', 'message': 'lệch'}]})
        self.assertEqual((error.code, error.details['level']), (7, 'block'))
        self.assertIn('--confirm-mismatch', str(error))


if __name__ == '__main__':
    unittest.main()
