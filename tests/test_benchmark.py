import json
from pathlib import Path
import tempfile
import unittest

class BenchmarkTests(unittest.TestCase):
    def test_comparison_rejects_different_inputs_instead_of_claiming_speedup(self):
        from apk_audit.benchmark import compare_reports
        first={'metrics':{'input_fingerprint':'one'},'summary':{'duration_seconds':10},'findings':[]}
        other={'metrics':{'input_fingerprint':'two'},'summary':{'duration_seconds':1},'findings':[]}
        self.assertFalse(compare_reports(first,other)['comparable'])
        other['metrics']['input_fingerprint']='one'
        result=compare_reports(first,other)
        self.assertTrue(result['comparable'])
        self.assertEqual(result['speedup'],10)
        other['findings']=[{'rule_id':'A','status':'FAIL'}]
        result=compare_reports(first,other)
        self.assertFalse(result['verdicts_equal'])
        self.assertFalse(result['quality_preserved'])

    def test_offline_suite_exercises_real_claim_guard_and_reports_denominators(self):
        from apk_audit.benchmark import quality_suite
        result=quality_suite()
        self.assertGreaterEqual(result['total'],6)
        self.assertEqual(result['matched'],result['total'],result['cases'])
        self.assertIn('unknown_count',result)
        self.assertIn('false_fail',result)
        self.assertEqual(result['false_fail'],0)
        self.assertIn('synthetic',result['scope'])

    def test_benchmark_cold_warm_and_metrics_have_same_input_fingerprint(self):
        from apk_audit.benchmark import benchmark
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); ws=root/'ws'; (ws/'sources').mkdir(parents=True)
            (ws/'sources/A.java').write_text('class A {}')
            pack=root/'pack'; pack.mkdir(); (pack/'pack.yaml').write_text('name: empty\nversion: "1"\nschema_version: 2\n')
            result=benchmark(ws,rules=pack,out=root/'bench',engine='none',repeats=2)
            self.assertEqual(len(result['runs']),2)
            self.assertFalse(result['runs'][0]['metrics']['index']['cache_hit'])
            self.assertTrue(result['runs'][1]['metrics']['index']['cache_hit'])
            self.assertEqual(result['runs'][0]['metrics']['input_fingerprint'],result['runs'][1]['metrics']['input_fingerprint'])
            self.assertEqual(result['engine'],'none')
            self.assertTrue((root/'bench/benchmark.json').is_file())
