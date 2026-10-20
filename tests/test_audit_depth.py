"""Recovery must obtain new valid evidence, never waive the final guard."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from apk_audit.agent import evaluate
from apk_audit.contracts import AgentResult, Finding, Rule
from apk_audit.pipeline import _cached_finding
from apk_audit.tools import WorkspaceTools
from apk_audit.verdict_cache import verdict_record
from test_claims import LiveReplay, verdict


class AuditDepthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Flow.java').write_text('if (enabled) load();\nonLoaded() { show(); }\n')
        self.tools = WorkspaceTools(self.root)
        self.rule = Rule('CLAIMS', 'Flow', 'agent', budget={'max_tool_calls': 40})

    def test_claim_index_errors_get_targeted_ai_repair(self):
        first = verdict()
        first['claims'][0]['evidence_indices'].append(53)
        engine = LiveReplay([first, verdict()])
        finding, trace = evaluate(self.rule, self.tools, engine, 'reference context', 40)
        self.assertEqual(finding.status, 'PASS')
        self.assertEqual(len(trace['attempts']), 2)
        self.assertTrue(trace['attempts'][1]['repair'])
        self.assertIn('invalid_evidence_indices', trace['repair_prompt'])
        self.assertIn('evidence_catalog', trace['repair_prompt'])

    def test_repair_resumes_rule_session_with_only_feedback_and_cleans_up(self):
        calls, closed = [], []
        class Resumable(LiveReplay):
            supports_resume = True
            def run_agent(inner, prompt, tools, allowance, resume=None):
                calls.append((prompt, resume))
                result = super(Resumable, inner).run_agent(prompt, tools, allowance)
                result.session_id = resume or f'session-{len(calls)}'
                return result
            def close_session(inner, session_id):
                closed.append(session_id)
        first = verdict()
        first['claims'][0]['evidence_indices'].append(53)
        finding, trace = evaluate(self.rule, self.tools, Resumable([first, verdict()]), 'LONG_CONTEXT', 40)
        self.assertEqual(finding.status, 'PASS')
        self.assertIsNone(calls[0][1])
        self.assertEqual(calls[1][1], 'session-1')
        self.assertNotIn('LONG_CONTEXT', calls[1][0])
        self.assertIn('invalid_evidence_indices', calls[1][0])
        self.assertTrue(trace['attempts'][1]['resumed'])
        self.assertEqual(set(closed), {'session-1'})

    def test_failed_resume_falls_back_to_full_prompt(self):
        calls = []
        class Broken(LiveReplay):
            supports_resume = True
            def run_agent(inner, prompt, tools, allowance, resume=None):
                calls.append(resume)
                if resume:
                    raise RuntimeError('No conversation found')
                result = super(Broken, inner).run_agent(prompt, tools, allowance)
                result.session_id = f'session-{len(calls)}'
                return result
            def close_session(inner, session_id):
                pass
        first = verdict()
        first['claims'][0]['evidence_indices'].append(53)
        finding, trace = evaluate(self.rule, self.tools, Broken([first, verdict()]), 'LONG_CONTEXT', 40)
        self.assertEqual(finding.status, 'PASS')
        self.assertEqual(calls, [None, 'session-1', None])
        self.assertFalse(trace['attempts'][1]['resumed'])
        self.assertIn('No conversation found', trace['attempts'][1]['resume_error'])

    def test_unknown_with_wrong_excerpt_is_repaired_instead_of_cached_as_inconclusive(self):
        first = dict(verdict(), status='UNKNOWN')
        first['evidence'][0]['excerpt'] = 'wrong source'
        engine = LiveReplay([first, verdict()])
        finding, trace = evaluate(self.rule, self.tools, engine, '', 40)
        self.assertEqual(finding.status, 'PASS')
        self.assertTrue(trace['attempts'][1]['repair'])

    def test_static_unknown_gets_one_focused_investigation(self):
        first = dict(verdict(), status='UNKNOWN', reasoning='Need callback implementation')
        first['claims'][0].update(kind='uncertain', unresolved=['Need callback implementation'])
        engine = LiveReplay([first, verdict()])
        finding, trace = evaluate(self.rule, self.tools, engine, '', 40)
        self.assertEqual(finding.status, 'PASS')
        self.assertTrue(trace['attempts'][1]['investigation'])
        self.assertIn('Need callback implementation', trace['investigation_prompt'])

    def test_investigation_cannot_promote_unmeasured_runtime_to_pass(self):
        first = dict(verdict(), status='UNKNOWN')
        first['claims'][0].update(kind='uncertain', unresolved=['Need SDK implementation'])
        unsupported = verdict()
        unsupported['claims'][0]['scope'] = 'runtime'
        engine = LiveReplay([first, unsupported])
        finding, trace = evaluate(self.rule, self.tools, engine, '', 40)
        self.assertEqual(finding.status, 'UNKNOWN')
        self.assertTrue(any('runtime_not_proven' in error for error in finding.verification['errors']))

    def test_initial_budget_exhaustion_can_use_reserved_followup_calls(self):
        first = AgentResult('', tool_calls=25, exhausted_budget=True, events=[
            {'type': 'source_read', 'command': 'read Flow.java', 'output': 'if (enabled) load();'}])
        engine = LiveReplay([first, verdict()])
        finding, trace = evaluate(self.rule, self.tools, engine, '', 40)
        self.assertEqual(finding.status, 'PASS')
        self.assertEqual(finding.tool_calls, 26)
        self.assertEqual(engine.budgets, [24, 15])
        self.assertTrue(trace['attempts'][1]['investigation'])
        self.assertIn('read Flow.java', trace['investigation_prompt'])
        self.assertFalse(finding.exhausted_budget)

    def test_prompt_separates_attempt_allowance_from_total_rule_budget(self):
        prompts = []
        class Recording(LiveReplay):
            def run_agent(inner, prompt, *args, **kwargs):
                prompts.append(json.loads(prompt.splitlines()[-1]))
                return super(Recording, inner).run_agent(prompt, *args, **kwargs)
        first = AgentResult('', tool_calls=25, exhausted_budget=True)
        finding, _ = evaluate(self.rule, self.tools, Recording([first, verdict()]), '', 40)
        self.assertEqual([p.get('current_attempt_max_tool_calls') for p in prompts], [24, 15])
        self.assertEqual(finding.status, 'PASS')

    def test_new_links_from_investigation_are_checked_and_repaired_before_acceptance(self):
        first = dict(verdict(), status='UNKNOWN')
        first['claims'][0].update(kind='uncertain', unresolved=['Need callback'])
        broken = verdict()
        broken['claims'][0]['path'][1]['evidence_indices'] = [63]
        engine = LiveReplay([first, broken, verdict()])
        finding, trace = evaluate(self.rule, self.tools, engine, '', 40)
        self.assertEqual(finding.status, 'PASS')
        self.assertEqual(len(trace['attempts']), 3)
        self.assertTrue(trace['attempts'][1]['investigation'])
        self.assertTrue(trace['attempts'][2]['repair'])

    def test_unknown_with_invalid_links_is_never_reused_from_cache(self):
        payload = dict(verdict(), status='UNKNOWN')
        payload['claims'][0]['evidence_indices'] = [53]
        from apk_audit.agent import _verify_evidence
        finding = Finding.for_rule(self.rule, status='UNKNOWN', reason='',
            evidence=_verify_evidence(payload, self.tools), claims=payload['claims'],
            verification={'valid': True})
        self.assertIsNone(_cached_finding(verdict_record(finding, {}), self.rule, self.tools, True))


if __name__ == '__main__':
    unittest.main()
