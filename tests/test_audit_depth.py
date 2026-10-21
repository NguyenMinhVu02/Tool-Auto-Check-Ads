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


class RangedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        lines = [f'int v{i} = {i};' for i in range(1, 60)]
        lines[9], lines[10] = 'if (enabled) {', '    sdk.load(id);'
        (self.root / 'Flow.java').write_text('\n'.join(lines) + '\n')
        self.tools = WorkspaceTools(self.root)

    def verify(self, *items):
        from apk_audit.agent import _verify_evidence
        return _verify_evidence({'evidence': list(items)}, self.tools)

    def test_range_with_matching_anchor_is_verified_and_filled_from_source(self):
        result = self.verify({'file': 'Flow.java', 'line': 10, 'end_line': 11, 'anchor': 'sdk.load( id );'})
        self.assertEqual((result[0]['verified'], result[0]['excerpt']), (True, 'if (enabled) {\n    sdk.load(id);'))

    def test_wrong_anchor_oversized_or_out_of_file_ranges_fail(self):
        for item in ({'line': 10, 'end_line': 11, 'anchor': 'sdk.show(id);'},      # not in the cited lines
                     {'line': 1, 'end_line': 30, 'anchor': 'int v1 = 1;'},         # range too large
                     {'line': 58, 'end_line': 70, 'anchor': 'int v58 = 58;'},      # beyond the file
                     {'line': 11, 'end_line': 10, 'anchor': 'sdk.load(id);'},      # reversed
                     {'line': 10, 'end_line': 10, 'anchor': 'if'}):               # anchor too short
            with self.subTest(item=item):
                self.assertFalse(self.verify(dict(item, file='Flow.java'))[0]['verified'])

    def test_full_audit_accepts_anchor_only_evidence_and_cached_copy_reverifies(self):
        from apk_audit.pipeline import _cached_finding
        payload = {'rule_id': 'R', 'status': 'PASS', 'reasoning': 'ok', 'hint': 'Flow.java:10',
                   'evidence': [{'file': 'Flow.java', 'line': 10, 'end_line': 11, 'anchor': 'sdk.load(id);'},
                                {'file': 'Flow.java', 'line': 20, 'end_line': 20, 'anchor': 'int v20 = 20;'}],
                   'claims': [{'id': 'c1', 'statement': 'gate then load', 'kind': 'compliance', 'evidence_indices': [0, 1],
                               'scope': 'static', 'applicability': 'applicable',
                               'path': [{'role': 'gate', 'evidence_indices': [0]}, {'role': 'load', 'evidence_indices': [1]}],
                               'conditions': [], 'unresolved': [], 'limitations': []}]}
        rule = Rule('R', 'T', 'agent', budget={'max_tool_calls': 40})
        finding, _ = evaluate(rule, self.tools, LiveReplay([payload]), '', 40)
        self.assertEqual(finding.status, 'PASS')
        self.assertTrue(all(e['verified'] and e['excerpt'] for e in finding.evidence))
        from apk_audit.verdict_cache import verdict_record
        record = verdict_record(finding, {})
        self.assertIsNotNone(_cached_finding(record, rule, self.tools, True))

    def test_reviewer_receives_real_source_text_for_each_cited_range(self):
        prompts = []
        class Recording(LiveReplay):
            def run_agent(inner, prompt, *args, **kwargs):
                prompts.append(prompt)
                return super(Recording, inner).run_agent(prompt, *args, **kwargs)
        payload = {'rule_id': 'R', 'status': 'FAIL', 'reasoning': 'Kết luận: lỗi', 'hint': 'Flow.java:10',
                   'evidence': [{'file': 'Flow.java', 'line': 10, 'end_line': 11, 'anchor': 'sdk.load(id);'},
                                {'file': 'Flow.java', 'line': 20, 'end_line': 20, 'anchor': 'int v20 = 20;'}],
                   'claims': [{'id': 'c1', 'statement': 'load without gate', 'kind': 'violation', 'evidence_indices': [0, 1],
                               'scope': 'static', 'applicability': 'applicable',
                               'path': [{'role': 'gate', 'evidence_indices': [0]}, {'role': 'load', 'evidence_indices': [1]}],
                               'conditions': [], 'unresolved': [], 'limitations': []}]}
        rule = Rule('R', 'T', 'agent', budget={'max_tool_calls': 40})
        finding, _ = evaluate(rule, self.tools, Recording([payload, payload]), '', 40)
        self.assertEqual(finding.status, 'FAIL')
        review = prompts[-1]
        self.assertIn('source_text', review)
        self.assertIn('if (enabled) {\\n    sdk.load(id);', review)   # real lines, JSON-escaped newline
        self.assertNotIn('"excerpt"', review.split('candidate')[1][:600])


class ScreenReportTests(unittest.TestCase):
    checklist = ['Load inter khi vào', 'Thoát khi lỗi', 'Có gate UA']

    def test_verified_answers_are_kept_and_unanswered_items_are_unknown(self):
        from apk_audit.agent import _screen_report
        raw = {'load': 'Tải khi mở', 'show': 'Hiện khi sẵn sàng', 'requirements': [
            {'index': 0, 'status': 'ok', 'note': 'đúng'}, {'index': 1, 'status': 'issue', 'note': 'kẹt'},
            {'index': 7, 'status': 'ok', 'note': 'bỏ'}, {'index': 0, 'status': 'issue', 'note': 'trùng'}]}
        report = _screen_report(raw, self.checklist, 'FAIL')
        self.assertEqual([r['status'] for r in report['requirements']], ['ok', 'issue', 'unknown'])
        self.assertEqual((report['requirements'][0]['note'], report['verified']), ('đúng', True))

    def test_downgraded_draft_never_shows_unproven_ok_or_issue(self):
        from apk_audit.agent import _screen_report
        raw = {'load': 'x', 'show': 'y', 'requirements': [{'index': 0, 'status': 'ok', 'note': 'a'}, {'index': 1, 'status': 'na', 'note': ''}]}
        report = _screen_report(raw, self.checklist, 'UNKNOWN')
        self.assertEqual([r['status'] for r in report['requirements']], ['unknown', 'na', 'unknown'])
        self.assertFalse(report['verified'])

    def test_rules_without_checklist_have_no_report_and_prompt_carries_checklist(self):
        from apk_audit.agent import _screen_report
        self.assertEqual(_screen_report({'load': 'x'}, None, 'PASS'), {})
        prompts = []
        class Recording(LiveReplay):
            def run_agent(inner, prompt, *args, **kwargs):
                prompts.append(prompt)
                return super(Recording, inner).run_agent(prompt, *args, **kwargs)
        rule = Rule('R', 'T', 'agent', params={'checklist': self.checklist}, budget={'max_tool_calls': 40})
        root = Path(tempfile.mkdtemp())
        (root / 'Flow.java').write_text('if (enabled) load();\nonLoaded() { show(); }\n')
        payload = verdict(); payload['rule_id'] = 'R'
        payload['screen_report'] = {'load': 'L', 'show': 'S', 'requirements': [{'index': 2, 'status': 'ok', 'note': 'n'}]}
        finding, _ = evaluate(rule, WorkspaceTools(root), Recording([payload]), '', 40)
        self.assertIn('Có gate UA', prompts[0])
        self.assertEqual((finding.status, finding.screen_report['requirements'][2]['status']), ('PASS', 'ok'))


if __name__ == '__main__':
    unittest.main()
