"""Synthetic contract checks, not a measurement of APK audit accuracy."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from apk_audit.agent import evaluate
from apk_audit.contracts import AgentResult, Rule
from apk_audit.engines import CodexEngine, ReplayEngine
from apk_audit.claude_engine import ClaudeEngine
from apk_audit.tools import WorkspaceTools


def verdict(status='PASS'):
    return {'rule_id': 'CLAIMS', 'status': status, 'reasoning': 'Synthetic flow', 'hint': 'Flow.java:1',
            'evidence': [{'file': 'Flow.java', 'line': 1, 'excerpt': 'if (enabled) load();'},
                         {'file': 'Flow.java', 'line': 2, 'excerpt': 'onLoaded() { show(); }'}],
            'claims': [{'id': 'c1', 'statement': 'The enabled flow loads then shows.',
                        'kind': 'violation' if status == 'FAIL' else 'compliance',
                        'evidence_indices': [0, 1], 'scope': 'static', 'applicability': 'applicable',
                        'path': [{'role': 'gate', 'evidence_indices': [0]},
                                 {'role': 'callback', 'evidence_indices': [1]}],
                        'conditions': ['enabled'], 'unresolved': [], 'limitations': []}]}


class LiveReplay(ReplayEngine):
    requires_claims = True
    def __init__(self, responses):
        super().__init__(responses)
        self.budgets = []
    def run_agent(self, prompt, tools, max_tool_calls, timeout=600):
        self.budgets.append(max_tool_calls)
        result = next(self.responses, '')
        if isinstance(result, Exception):
            raise result
        return result if isinstance(result, AgentResult) else AgentResult(json.dumps(result), tool_calls=1)


class ClaimTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Flow.java').write_text('if (enabled) load();\nonLoaded() { show(); }\n')
        self.tools = WorkspaceTools(self.root)
        self.rule = Rule('CLAIMS', 'Synthetic claims', 'agent')
    def run_result(self, result, *more, budget=10):
        engine = LiveReplay([result, *more])
        finding, trace = evaluate(self.rule, self.tools, engine, {}, max_tool_calls=budget)
        return finding, trace, engine
    def test_live_adapters_require_claims_legacy_does_not(self):
        self.assertTrue(CodexEngine.requires_claims)
        self.assertTrue(ClaudeEngine.requires_claims)
        self.assertFalse(ReplayEngine.requires_claims)
    def test_valid_static_pass_marks_structure_not_semantic_proof(self):
        finding, trace, _ = self.run_result(verdict())
        self.assertEqual(finding.status, 'PASS')
        self.assertEqual(finding.claims[0]['id'], 'c1')
        self.assertEqual(finding.verification['level'], 'structure_and_evidence')
        self.assertFalse(finding.verification['semantic_proof'])
        attempt = trace['attempts'][0]
        self.assertGreater(attempt['prompt_bytes'], 0)
        self.assertGreaterEqual(attempt['duration_seconds'], 0)
        self.assertFalse(attempt['review'])
    def test_missing_applicability_path_claims_or_broken_refs_are_unknown(self):
        for key in ('applicability', 'path', 'conditions', 'unresolved'):
            with self.subTest(key=key):
                result = verdict()
                del result['claims'][0][key]
                finding, _, _ = self.run_result(result)
                self.assertEqual((finding.status, finding.reason), ('UNKNOWN', 'unverified_claims'))
        for change in ({'claims': []}, {'claims': 'not a list'}):
            finding, _, _ = self.run_result(dict(verdict(), **change))
            self.assertEqual(finding.status, 'UNKNOWN')
        for indices in ([2], [True], [-1], [], '0'):
            result = verdict()
            result['claims'][0]['path'][1]['evidence_indices'] = indices
            self.assertEqual(self.run_result(result)[0].status, 'UNKNOWN')
    def test_runtime_unknown_applicability_or_unresolved_are_unknown(self):
        for field, value in [('scope', 'runtime'), ('applicability', 'unknown'),
                             ('unresolved', ['SDK not decoded']), ('kind', 'uncertain')]:
            result = verdict()
            result['claims'][0][field] = value
            finding, _, _ = self.run_result(result)
            self.assertEqual((finding.status, finding.reason), ('UNKNOWN', 'unverified_claims'))
    def test_live_schema_requires_explicit_limitations(self):
        from apk_audit.engine_common import verdict_schema
        claim_schema = verdict_schema()['properties']['claims']['items']
        self.assertIn('limitations', claim_schema['required'])
        self.assertEqual(claim_schema['properties']['limitations'],
                         {'type': 'array', 'items': {'type': 'string'}})

    def test_static_limitations_allow_reviewed_static_finding(self):
        result = verdict('FAIL')
        result['claims'][0]['limitations'] = ['No runtime proof, outside static contract']
        finding, trace, _ = self.run_result(result, copy.deepcopy(result))
        self.assertEqual(finding.status, 'FAIL')
        self.assertEqual(finding.verification['review'], 'accepted')
        self.assertEqual(len(trace['attempts']), 2)
        self.assertEqual(finding.claims[0]['limitations'], ['No runtime proof, outside static contract'])

    def test_invalid_limitations_are_not_accepted(self):
        for invalid in ('No runtime', None, [123], ['']):
            with self.subTest(invalid=invalid):
                result = verdict()
                result['claims'][0]['limitations'] = invalid
                finding, _, _ = self.run_result(result)
                self.assertEqual((finding.status, finding.reason), ('UNKNOWN', 'unverified_claims'))

    def test_unresolved_is_never_discarded_by_interpreting_prose(self):
        for blocker in ['SDK not decoded', 'No runtime proof, outside static contract']:
            result = verdict('FAIL')
            result['claims'][0]['unresolved'] = [blocker]
            result['claims'][0]['limitations'] = ['No runtime proof, outside static contract']
            finding, trace, _ = self.run_result(result)
            self.assertEqual((finding.status, finding.reason), ('UNKNOWN', 'unverified_claims'))
            self.assertEqual(len(trace['attempts']), 1)
        result = verdict('FAIL')
        result['claims'][0]['scope'] = 'runtime'
        result['claims'][0]['limitations'] = ['No runtime proof, outside static contract']
        self.assertEqual(self.run_result(result)[0].status, 'UNKNOWN')

    def test_legacy_claim_without_limitations_remains_readable(self):
        result = verdict()
        del result['claims'][0]['limitations']
        self.assertEqual(self.run_result(result)[0].status, 'PASS')

    def test_single_role_or_unlinked_path_is_unknown(self):
        result = verdict()
        result['claims'][0]['path'][1]['role'] = 'gate'
        self.assertEqual(self.run_result(result)[0].status, 'UNKNOWN')
        result = verdict()
        result['claims'][0]['evidence_indices'] = [0]
        self.assertEqual(self.run_result(result)[0].status, 'UNKNOWN')
    def test_not_applicable_claim_cannot_support_a_verdict(self):
        result = verdict()
        result['claims'][0]['applicability'] = 'not_applicable'
        self.assertEqual(self.run_result(result)[0].status, 'UNKNOWN')
    def test_verdict_must_agree_with_applicable_claim_kind(self):
        for result in [dict(verdict('FAIL'), status='PASS'), dict(verdict(), status='FAIL')]:
            self.assertEqual(self.run_result(result)[0].status, 'UNKNOWN')
    def test_invalid_evidence_item_is_not_silently_skipped(self):
        result = verdict()
        result['evidence'].append('malformed')
        finding, _, _ = self.run_result(result, result)
        self.assertEqual((finding.status, finding.reason), ('UNKNOWN', 'unverified_evidence'))
    def test_fail_requires_review_and_combines_tool_counts_and_usage(self):
        first = AgentResult(json.dumps(verdict('FAIL')), tool_calls=3)
        second = AgentResult(json.dumps(verdict('FAIL')), tool_calls=2)
        first.usage = {'input_tokens': 10}
        finding, trace, engine = self.run_result(first, second, budget=8)
        self.assertEqual((finding.status, finding.tool_calls), ('FAIL', 5))
        self.assertEqual(engine.budgets, [8, 5])
        self.assertTrue(trace['attempts'][1]['review'])
        self.assertEqual(trace['attempts'][0]['usage'], {'input_tokens': 10})
        self.assertEqual(finding.verification['review'], 'accepted')
    def test_correct_excerpts_wrong_claim_can_be_rejected_by_review(self):
        result = verdict('FAIL')
        result['claims'][0]['statement'] = 'The disabled flow always shows an ad.'
        review = dict(verdict(), status='UNKNOWN', reasoning='Claim not supported by the enabled branch.')
        finding, trace, _ = self.run_result(result, review)
        self.assertEqual(finding.status, 'UNKNOWN')
        self.assertEqual(len(trace['attempts']), 2)
        self.assertIn('not supported', finding.reasoning)
    def test_review_error_invalid_result_and_budget_fail_closed(self):
        for review in [RuntimeError('review timeout'), {'rule_id': 'other', 'status': 'FAIL'},
                       AgentResult('bad json', tool_calls=2), AgentResult('', tool_calls=5, exhausted_budget=True)]:
            finding, trace, _ = self.run_result(verdict('FAIL'), review, budget=5)
            self.assertEqual(finding.status, 'UNKNOWN')
            self.assertTrue(trace['attempts'][1]['review'])
        finding, trace, engine = self.run_result(verdict('FAIL'), budget=1)
        self.assertEqual((finding.status, finding.reason), ('UNKNOWN', 'review_budget'))
        self.assertEqual(engine.budgets, [1])
    def ancillary_draft(self, invalid_evidence=True):
        result = verdict('FAIL')
        result['reasoning'] = 'Kết luận: FAIL\nCần sửa: Preserve this draft detail.'
        extra = copy.deepcopy(result['claims'][0])
        extra.update(id='ancillary', kind='uncertain', scope='runtime',
                     statement='Runtime behavior not observed', unresolved=['Runtime not measured'])
        if invalid_evidence:
            result['evidence'].append({'file': 'Flow.java', 'line': 99, 'excerpt': 'not present'})
            extra['evidence_indices'] = [2]
            extra['path'] = [{'role': 'runtime', 'evidence_indices': [2]}]
        result['claims'].append(extra)
        return result

    def test_valid_violation_with_invalid_ancillary_can_reach_targeted_review(self):
        result = self.ancillary_draft()
        finding, trace, engine = self.run_result(result, copy.deepcopy(result), verdict('FAIL'), budget=5)
        self.assertEqual((finding.status, finding.reason), ('FAIL', ''))
        self.assertEqual(finding.verification['review'], 'accepted')
        self.assertEqual(finding.tool_calls, 3)
        self.assertEqual(engine.budgets, [5, 4, 3])
        self.assertTrue(trace['attempts'][1]['repair'])
        self.assertTrue(trace['attempts'][2]['review'])
        self.assertEqual(len(finding.evidence), 2)

    def test_valid_violation_with_uncertain_ancillary_can_be_reviewed(self):
        result = self.ancillary_draft(invalid_evidence=False)
        finding, trace, _ = self.run_result(result, verdict('FAIL'))
        self.assertEqual((finding.status, finding.reason), ('FAIL', ''))
        self.assertTrue(trace['attempts'][1]['review'])

    def test_ancillary_review_unknown_or_error_explains_rejected_draft(self):
        for review in [dict(verdict(), status='UNKNOWN', reasoning='Review cannot establish this path.'),
                       RuntimeError('Review timed out')]:
            with self.subTest(review=type(review).__name__):
                result = self.ancillary_draft()
                finding, trace, _ = self.run_result(result, copy.deepcopy(result), review)
                self.assertEqual(finding.status, 'UNKNOWN')
                self.assertTrue(trace['attempts'][2]['review'])
                self.assertIn('Chưa đủ căn cứ', finding.reasoning)
                self.assertIn('Bản nháp AI chưa được xác minh', finding.reasoning)
                self.assertIn('Preserve this draft detail.', finding.reasoning)
                self.assertNotIn('\nKết luận: FAIL', finding.reasoning)
                self.assertIn('Review', finding.reasoning)

    def test_review_does_not_automatically_drop_invalid_ancillary(self):
        result = self.ancillary_draft()
        finding, trace, _ = self.run_result(result, copy.deepcopy(result), copy.deepcopy(result))
        self.assertEqual((finding.status, finding.reason), ('UNKNOWN', 'unverified_evidence'))
        self.assertTrue(trace['attempts'][2]['review'])
        self.assertEqual(len(finding.evidence), 3)
        self.assertIn('Chưa đủ căn cứ', finding.reasoning)

    def test_malformed_sole_violation_does_not_trigger_review(self):
        for field, value in [('unresolved', ['SDK not decoded']), ('path', [])]:
            result = verdict('FAIL')
            result['reasoning'] = 'Kết luận: FAIL\nImportant original detail'
            result['claims'][0][field] = value
            finding, trace, _ = self.run_result(result)
            self.assertEqual(finding.status, 'UNKNOWN')
            self.assertEqual(len(trace['attempts']), 1)
            self.assertIn('Chưa đủ căn cứ', finding.reasoning)
            self.assertIn('Important original detail', finding.reasoning)
            self.assertNotIn('\nKết luận: FAIL', finding.reasoning)

    def test_downgraded_pass_and_review_budget_mark_draft_unaccepted(self):
        result = verdict()
        result['reasoning'] = 'Kết luận: PASS\nOriginal PASS detail'
        result['claims'][0]['unresolved'] = ['SDK missing']
        finding, _, _ = self.run_result(result)
        self.assertEqual(finding.status, 'UNKNOWN')
        self.assertIn('Chưa đủ căn cứ', finding.reasoning)
        self.assertIn('Original PASS detail', finding.reasoning)
        self.assertNotIn('\nKết luận: PASS', finding.reasoning)
        result = self.ancillary_draft(invalid_evidence=False)
        finding, _, _ = self.run_result(result, budget=1)
        self.assertEqual((finding.status, finding.reason), ('UNKNOWN', 'review_budget'))
        self.assertIn('Chưa đủ căn cứ', finding.reasoning)

    def test_json_retry_is_recorded_as_repair(self):
        finding, trace, _ = self.run_result(AgentResult('bad json', tool_calls=1), verdict())
        self.assertEqual(finding.status, 'PASS')
        self.assertTrue(trace['attempts'][1]['repair'])

    def test_invalid_repair_is_reported_as_system_failure(self):
        result = verdict()
        result['evidence'][0]['excerpt'] = 'wrong'
        finding, _, _ = self.run_result(result, AgentResult('bad json', tool_calls=1))
        self.assertEqual((finding.status, finding.reason), ('UNKNOWN', 'repair_invalid_result'))

    def test_repair_exhaustion_never_accepts_original_verdict(self):
        result = verdict()
        result['evidence'][0]['excerpt'] = 'wrong'
        repair = AgentResult(json.dumps(verdict()), tool_calls=3, exhausted_budget=True)
        finding, trace, _ = self.run_result(result, repair, budget=3)
        self.assertEqual(finding.status, 'UNKNOWN')
        self.assertTrue(finding.exhausted_budget)
        self.assertEqual(finding.tool_calls, 4)
        self.assertTrue(trace['attempts'][1]['repair'])
    def test_review_exception_preserves_observed_calls(self):
        error = RuntimeError('review failed after tools')
        error.tool_calls = 2
        finding, trace, _ = self.run_result(verdict('FAIL'), error)
        self.assertEqual((finding.status, finding.tool_calls), ('UNKNOWN', 3))
        self.assertEqual(trace['attempts'][1]['tool_calls'], 2)
    def test_legacy_replay_is_explicitly_unverified(self):
        result = verdict()
        del result['claims']
        finding, trace = evaluate(self.rule, self.tools, ReplayEngine([json.dumps(result)]), {})
        self.assertEqual(finding.status, 'PASS')
        self.assertEqual(finding.verification['level'], 'legacy_evidence_only')
    def test_synthetic_quality_fixtures(self):
        fixture = Path(__file__).resolve().parent.parent / 'apk_audit/quality_cases.json'
        for case in json.loads(fixture.read_text())['cases']:
            with self.subTest(case=case['id']):
                for name, text in case['workspace'].items():
                    (self.root / name).write_text(text)
                more = [case['review']] if 'review' in case else []
                finding, _, _ = self.run_result(case['result'], *more, budget=case.get('max_tool_calls', 10))
                self.assertEqual(finding.status, case['expected_status'])
                self.assertEqual(finding.reason, case['expected_reason'])

    def test_policy_identity_changes_with_schema(self):
        from apk_audit.engine_common import policy_identity
        from unittest.mock import patch
        before = policy_identity()
        with patch('apk_audit.engine_common.verdict_schema', return_value={'different': True}):
            self.assertNotEqual(before, policy_identity())


if __name__ == '__main__':
    unittest.main()


class ExcerptMatchTests(unittest.TestCase):
    lines = ['class A {', '    void load() {', '        if (enabled) {', '            sdk.load(id);',
             '        }', '        done();', '    }', '}']

    def test_accepts_reindented_reflowed_and_elided_excerpts(self):
        from apk_audit.agent import _excerpt_matches
        self.assertTrue(_excerpt_matches('if (enabled) {\nsdk.load(id);', self.lines, 3))
        self.assertTrue(_excerpt_matches('if (enabled) { sdk.load(id); }', self.lines, 3))
        self.assertTrue(_excerpt_matches('void load() {\n...\ndone();', self.lines, 2))

    def test_rejects_wrong_line_order_or_invented_code(self):
        from apk_audit.agent import _excerpt_matches
        self.assertFalse(_excerpt_matches('if (enabled) {\nsdk.load(id);', self.lines, 4))
        self.assertFalse(_excerpt_matches('done();\n...\nsdk.load(id);', self.lines, 6))
        self.assertFalse(_excerpt_matches('if (enabled) { sdk.show(id); }', self.lines, 3))
        self.assertFalse(_excerpt_matches('...', self.lines, 3))
