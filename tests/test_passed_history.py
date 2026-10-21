import json
from pathlib import Path
import tempfile
import unittest

from apk_audit.passed_history import PassedHistory


def report(status, sha, mode='agent', engine='codex'):
    return {'package': 'demo.app', 'apk_sha256': sha, 'version_name': '1.0', 'engine': engine,
            'findings': [{'rule_id': 'R', 'status': status, 'mode': mode}]}


class PassedHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.history = PassedHistory(self.root / 'cache')

    def test_pass_is_found_only_for_a_different_build_and_failure_invalidates_it(self):
        self.assertEqual(self.history.record(report('PASS', 'a')), 1)
        self.assertIsNone(self.history.lookup('demo.app', 'R', 'a'))        # same build: normal cache handles it
        self.assertEqual(self.history.lookup('demo.app', 'R', 'b')['version_name'], '1.0')
        self.assertIsNone(self.history.lookup('other.app', 'R', 'b'))
        self.history.record(report('FAIL', 'b'))
        self.assertIsNone(self.history.lookup('demo.app', 'R', 'c'))

    def test_offline_and_static_results_are_not_remembered(self):
        self.assertEqual(self.history.record(report('PASS', 'a', engine='none')), 0)
        self.assertEqual(self.history.record(report('PASS', 'a', mode='static')), 0)
        self.assertIsNone(self.history.lookup('demo.app', 'R', 'b'))

    def test_history_can_be_rebuilt_from_saved_reports(self):
        job = self.root / 'jobs' / 'one'
        job.mkdir(parents=True)
        (job / 'report.json').write_text(json.dumps(report('PASS', 'a')))
        self.assertEqual(self.history.seed_from_reports(self.root / 'jobs'), 1)
        self.assertIsNotNone(self.history.lookup('demo.app', 'R', 'b'))


if __name__ == '__main__':
    unittest.main()
