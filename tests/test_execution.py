import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from apk_audit.contracts import AgentResult, Finding, Rule
from apk_audit.engines import ReplayEngine
from apk_audit import run
from apk_audit.pipeline import normalize_usage


class SchedulerTests(unittest.TestCase):
    def test_two_workers_overlap_budget_is_reserved_and_report_order_stays_fixed(self):
        from apk_audit.execution import execute_rules, RuleOutcome
        entered = threading.Barrier(2)
        allocations = []
        lock = threading.Lock()
        rules = [Rule('A', 'A', 'agent', budget={'max_tool_calls': 3}),
                 Rule('B', 'B', 'agent', budget={'max_tool_calls': 3}),
                 Rule('ADS_CROSS_FLOW_BUGS', 'Cross', 'agent')]
        def work(rule, budget, prior):
            with lock:
                allocations.append((rule.id, budget))
            if rule.id != 'ADS_CROSS_FLOW_BUGS':
                entered.wait(timeout=3)
            else:
                self.assertEqual([item['rule_id'] for item in prior], ['A', 'B'])
                self.assertTrue(all('evidence' in item for item in prior))
            finding = Finding.for_rule(rule, status='UNKNOWN', tool_calls=min(1,budget))
            return RuleOutcome(finding)
        events=[]
        outcomes, used = execute_rules(rules, work, max_tool_calls=4, workers=2,
                                      progress=lambda event,data: events.append((event,data)))
        self.assertEqual([o.finding.rule_id for o in outcomes], ['A','B','ADS_CROSS_FLOW_BUGS'])
        self.assertEqual(used, 3)
        self.assertEqual(dict(allocations)['A'], 3)
        self.assertEqual(dict(allocations)['B'], 1)
        self.assertEqual(events[-1][1]['completed'],3)
        self.assertTrue(any(len(data['active_rules'])==2 for _,data in events))

    def test_many_workers_run_independent_rules_together(self):
        from apk_audit.execution import execute_rules, RuleOutcome
        entered = threading.Barrier(6)
        rules = [Rule(f'R{i}', f'R{i}', 'agent', budget={'max_tool_calls': 40}) for i in range(6)]
        def work(rule, budget, prior):
            entered.wait(timeout=3)  # Breaks unless all six run at once.
            return RuleOutcome(Finding.for_rule(rule, status='PASS', tool_calls=1))
        outcomes, used = execute_rules(rules, work, max_tool_calls=400, workers=6)
        self.assertEqual([o.finding.status for o in outcomes], ['PASS'] * 6)
        self.assertEqual(used, 6)

    def test_crossflow_runs_last_even_if_pack_lists_it_first(self):
        from apk_audit.execution import execute_rules, RuleOutcome
        rules=[Rule('ADS_CROSS_FLOW_BUGS','Cross','agent'), Rule('A','A','agent')]
        order=[]
        def work(rule,budget,prior):
            order.append(rule.id)
            return RuleOutcome(Finding.for_rule(rule))
        outcomes,_=execute_rules(rules,work,max_tool_calls=0,workers=1)
        self.assertEqual(order,['A','ADS_CROSS_FLOW_BUGS'])
        self.assertEqual([o.finding.rule_id for o in outcomes],['ADS_CROSS_FLOW_BUGS','A'])

    def test_invalid_worker_count_rejected(self):
        from apk_audit.execution import execute_rules
        for workers in (0,11,True):
            with self.subTest(workers=workers), self.assertRaises(ValueError):
                execute_rules([],None,workers=workers)


class PipelineOptimizationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.ws=self.root/'ws'
        (self.ws/'sources/demo').mkdir(parents=True)
        (self.ws/'resources/assets').mkdir(parents=True)
        (self.ws/'resources/AndroidManifest.xml').write_text('<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="demo.app"><application android:name="demo.App"/></manifest>')
        (self.ws/'sources/demo/App.java').write_text('package demo;\npublic class App { void onCreate() { Example.init(); } }\n')
        (self.ws/'resources/assets/ad_config.json').write_text('{"inter_splash":{"id":"local-id"}}')
        self.pack=self.root/'pack'; (self.pack/'rules').mkdir(parents=True)
        (self.pack/'pack.yaml').write_text('name: fixture\nversion: "1"\nschema_version: 2\n')
        (self.pack/'rules/a.yaml').write_text('- id: EXAMPLE\n  title: Inspect\n  area: splash\n  mode: agent\n  question: Inspect\n  verdict: {pass_when: "yes", fail_when: "no", unknown_when: unclear}\n')
        self.kwargs=dict(rules=self.pack,out=self.root/'out',cache_dir=self.root/'cache',trace=True)
        self.payload=json.dumps({'rule_id':'EXAMPLE','status':'UNKNOWN','reasoning':'fixture incomplete','evidence':[]})

    def scoped_pass_result(self, command='sed -n 1,5p sources/demo/App.java'):
        payload=json.dumps({'rule_id':'EXAMPLE','status':'PASS','reasoning':'ok','hint':'sources/',
                            'evidence':[{'file':'sources/demo/App.java','line':2,'excerpt':'public class App { void onCreate() { Example.init(); } }'}]})
        return AgentResult(payload,tool_calls=1,events=[{'type':'source_read','command':command,'output':'x'}])

    def copy_workspace(self,name,edit=None):
        import shutil
        target=self.root/name
        shutil.copytree(self.ws,target)
        if edit:
            edit(target)
        return target

    def test_scoped_cache_reuses_verdict_only_when_files_read_are_unchanged(self):
        (self.ws/'sources/demo/Other.java').write_text('package demo;\nclass Other { int v = 1; }\n')
        first=run(self.ws,engine=ReplayEngine([self.scoped_pass_result()]),**self.kwargs)
        self.assertEqual(first['findings'][0]['status'],'PASS')
        class Forbidden(ReplayEngine):
            def run_agent(inner,*args,**kwargs):
                raise AssertionError('AI must not be called')
        unrelated=self.copy_workspace('unrelated',lambda w:(w/'sources/demo/Other.java').write_text('package demo;\nclass Other { int v = 2; }\n'))
        second=run(unrelated,engine=Forbidden([]),**self.kwargs)
        self.assertEqual((second['findings'][0]['status'],second['findings'][0]['from_cache']),('PASS',True))
        self.assertTrue(second['metrics']['rules'][0]['from_scoped_cache'])
        changed=self.copy_workspace('changed',lambda w:(w/'sources/demo/App.java').write_text('package demo; // edited\npublic class App { void onCreate() { Example.init(); } }\n'))
        third=run(changed,engine=ReplayEngine([self.scoped_pass_result()]),**self.kwargs)
        self.assertFalse(third['metrics']['rules'][0]['from_scoped_cache'])
        self.assertEqual(third['metrics']['rules'][0]['tool_calls'],1)
        added=self.copy_workspace('added',lambda w:(w/'sources/demo/New.java').write_text('class New {}\n'))
        fourth=run(added,engine=ReplayEngine([self.scoped_pass_result()]),**self.kwargs)
        self.assertFalse(fourth['metrics']['rules'][0]['from_scoped_cache'])

    def test_scoped_cache_is_disabled_for_workspace_wide_searches_and_when_turned_off(self):
        (self.ws/'sources/demo/Other.java').write_text('class Other { int v = 1; }\n')
        run(self.ws,engine=ReplayEngine([self.scoped_pass_result('rg -n Example.init')]),**self.kwargs)
        other=self.copy_workspace('other',lambda w:(w/'sources/demo/Other.java').write_text('class Other { int v = 2; }\n'))
        report=run(other,engine=ReplayEngine([self.scoped_pass_result('rg -n Example.init')]),**self.kwargs)
        self.assertFalse(report['metrics']['rules'][0]['from_scoped_cache'])
        self.assertEqual(report['metrics']['rules'][0]['tool_calls'],1)

    def test_rule_with_skip_after_pass_is_skipped_on_later_builds_unless_rechecked(self):
        (self.pack/'rules/a.yaml').write_text('- id: EXAMPLE\n  title: Inspect\n  area: splash\n  mode: agent\n  question: Inspect\n  params: {skip_after_pass: true}\n  verdict: {pass_when: "y", fail_when: "n", unknown_when: u}\n')
        first=run(self.ws,engine=ReplayEngine([self.scoped_pass_result()]),**self.kwargs)
        self.assertEqual(first['findings'][0]['status'],'PASS')
        class Forbidden(ReplayEngine):
            def run_agent(inner,*args,**kwargs):
                raise AssertionError('AI must not be called')
        newer=self.copy_workspace('newer',lambda w:(w/'sources/demo/App.java').write_text('package demo; // v2\npublic class App { void onCreate() { Example.init(); } }\n'))
        second=run(newer,engine=Forbidden([]),**self.kwargs)
        finding=second['findings'][0]
        self.assertEqual((finding['status'],finding['reason'],finding['tool_calls']),('SKIPPED','passed_previously',0))
        third=run(newer,engine=ReplayEngine([self.scoped_pass_result()]),recheck_all=True,**self.kwargs)
        self.assertEqual(third['findings'][0]['status'],'PASS')
        self.assertEqual(third['metrics']['rules'][0]['tool_calls'],1)

    def test_pack_version_bump_keeps_unchanged_ai_verdicts_but_rule_edits_do_not(self):
        run(self.ws,engine=ReplayEngine([self.scoped_pass_result()]),**self.kwargs)
        class Forbidden(ReplayEngine):
            def run_agent(inner,*args,**kwargs):
                raise AssertionError('AI must not be called')
        (self.pack/'pack.yaml').write_text('name: fixture\nversion: "2"\nschema_version: 2\n')
        warm=run(self.ws,engine=Forbidden([]),**self.kwargs)
        self.assertEqual((warm['findings'][0]['status'],warm['findings'][0]['from_cache']),('PASS',True))
        (self.pack/'rules/a.yaml').write_text('- id: EXAMPLE\n  title: Inspect\n  area: splash\n  mode: agent\n  question: Inspect again\n  verdict: {pass_when: "yes", fail_when: "no", unknown_when: unclear}\n')
        changed=run(self.ws,engine=ReplayEngine([self.scoped_pass_result()]),**self.kwargs)
        self.assertEqual(changed['metrics']['rules'][0]['tool_calls'],1)

    def test_failed_screen_rule_keeps_full_checklist_and_quota_is_reported(self):
        (self.pack/'rules/a.yaml').write_text('- id: EXAMPLE\n  title: Inspect\n  area: splash\n  mode: agent\n  question: Inspect\n  params:\n    checklist: ["Load đúng", "Thoát khi lỗi"]\n  verdict: {pass_when: "y", fail_when: "n", unknown_when: u}\n')
        class Quota(ReplayEngine):
            requires_claims=True
            def run_agent(inner,*args,**kwargs):
                raise RuntimeError("You've hit your usage limit. Try again at 2:19 PM.")
        report=run(self.ws,engine=Quota([]),**self.kwargs)
        finding=report['findings'][0]
        self.assertEqual((finding['status'],finding['reason']),('UNKNOWN','engine_error'))
        self.assertEqual([r['status'] for r in finding['screen_report']['requirements']],['unknown','unknown'])
        self.assertTrue(any(w.startswith('engine_quota_exhausted: 1 rule') for w in report['warnings']))
        screen=next(x for x in report['marketing']['screens'] if x['rule_id']=='EXAMPLE') if any(x['rule_id']=='EXAMPLE' for x in report['marketing']['screens']) else None
        self.assertIsNone(screen)  # fixture rule is not one of the four marketing screens
        self.assertIn('hết hạn mức', report['dev_view']['groups'][0]['rules'][0]['unknown_reason'])

    def test_mismatched_documents_stop_before_any_ai_call_unless_confirmed(self):
        from apk_audit.preflight import DocumentMismatch
        ads=self.root/'ads.json'
        ads.write_text(json.dumps({'placements':[{'name':'inter_splash','id':'ca-app-pub-111/1','enabled':True}]}))
        (self.ws/'resources/assets/ad_config.json').write_text('{"inter_splash":{"id":"ca-app-pub-222/1"}}')
        class Forbidden(ReplayEngine):
            def run_agent(inner,*args,**kwargs):
                raise AssertionError('AI must not be called')
        with self.assertRaises(DocumentMismatch) as caught:
            run(self.ws,engine=Forbidden([]),ads_scripts=ads,**self.kwargs)
        self.assertEqual(caught.exception.details['reasons'][0]['code'],'publisher')
        report=run(self.ws,engine=ReplayEngine([self.payload]),ads_scripts=ads,confirm_mismatch=True,**self.kwargs)
        self.assertEqual(report['preflight']['level'],'block')
        self.assertTrue(any(w.startswith('documents_may_not_match_app') for w in report['warnings']))
        offline=run(self.ws,engine='none',ads_scripts=ads,**self.kwargs)    # no AI quota at stake: never blocks
        self.assertEqual(offline['summary']['agent'],1)

    def test_rule_is_skipped_without_ai_when_document_marks_area_unused(self):
        (self.pack/'rules/a.yaml').write_text('- id: WELCOME\n  title: Welcome\n  area: welcome\n  mode: agent\n  question: Inspect\n  verdict: {pass_when: "y", fail_when: "n", unknown_when: u}\n')
        ads=self.root/'ads.json'
        ads.write_text(json.dumps({'placements':[{'name':'inter_welcome_back','id':'x','enabled':False},{'name':'inter_splash','id':'y'}]}))
        class Forbidden(ReplayEngine):
            def run_agent(inner,*args,**kwargs):
                raise AssertionError('AI must not be called')
        report=run(self.ws,engine=Forbidden([]),ads_scripts=ads,**self.kwargs)
        finding=report['findings'][0]
        self.assertEqual((finding['status'],finding['reason'],finding['tool_calls']),('SKIPPED','not_applicable_by_document',0))
        self.assertIn('inter_welcome_back',finding['reasoning'])

    def test_usage_is_normalized_per_rule_and_totalled(self):
        usage={"input_tokens":6,"cache_read_input_tokens":100,"cache_creation_input_tokens":40,"output_tokens":9}
        report=run(self.ws,engine=ReplayEngine([AgentResult(self.payload,tool_calls=1,usage=usage)]),**self.kwargs)
        expected={"input":6,"cache_read":100,"cache_write":40,"output":9}
        self.assertEqual(report['metrics']['rules'][0]['usage'],expected)
        self.assertEqual(report['metrics']['usage_totals'],expected)
        self.assertEqual(report['metrics']['rules'][0]['resumed_attempts'],0)
        codex=normalize_usage({"input_tokens":50,"cached_input_tokens":30,"output_tokens":4})
        self.assertEqual(codex,{"input":50,"cache_read":30,"cache_write":0,"output":4})

    def test_metrics_and_source_bundle_are_sent_and_warm_cache_avoids_ai(self):
        class Recording(ReplayEngine):
            def run_agent(inner,prompt,*args,**kwargs):
                self.assertIn('evidence_bundle',prompt)
                self.assertIn('inter_splash',prompt)
                return super(Recording,inner).run_agent(prompt,*args,**kwargs)
        first=run(self.ws,engine=Recording([AgentResult(self.payload,tool_calls=1,usage={"input_tokens":7,"output_tokens":3})]),**self.kwargs)
        second=run(self.ws,engine=ReplayEngine([]),**self.kwargs)
        self.assertEqual(second['summary']['from_cache'],1)
        self.assertTrue(second['metrics']['index']['cache_hit'])
        self.assertEqual(first['metrics']['workers'],1)
        self.assertIn('facts',first['metrics']['phases'])
        self.assertEqual(first['metrics']['rules'][0]['usage_observed'],{'input_tokens':7,'output_tokens':3})
        self.assertEqual(second['metrics']['rules'][0]['usage_observed'],{})
        self.assertEqual(first['metrics']['rules'][0]['rule_id'],'EXAMPLE')
        self.assertGreaterEqual(first['metrics']['rules'][0]['duration_seconds'],0)
        self.assertTrue((self.root/'out/checkpoint.json').is_file())

    def test_cache_policy_changes_force_fresh_verdict(self):
        run(self.ws,engine=ReplayEngine([self.payload]),**self.kwargs)
        with patch('apk_audit.pipeline.policy_identity',return_value={'policy':'changed'}):
            report=run(self.ws,engine=ReplayEngine([self.payload]),**self.kwargs)
        self.assertEqual(report['summary']['from_cache'],0)

    def test_rule_base_reference_reaches_ai_and_changes_invalidate_its_verdict(self):
        reference = {'schema_version': 1, 'source': {'repository': 'base', 'commit': 'fixture-v1'},
                     'rules': {'EXAMPLE': {'static_goal': 'trace load to navigation',
                                           'snippets': [{'file': 'Base.kt', 'start': 1, 'excerpt': 'fun load() = next()'}]}}}
        path = self.pack / 'base-reference.json'
        path.write_text(json.dumps(reference))
        prompts = []
        class Recording(ReplayEngine):
            def run_agent(inner, prompt, *args, **kwargs):
                prompts.append(prompt)
                return super(Recording, inner).run_agent(prompt, *args, **kwargs)
        first = run(self.ws, engine=Recording([self.payload]), **self.kwargs)
        self.assertIn('fixture-v1', prompts[0])
        self.assertIn('trace load to navigation', prompts[0])
        reference['rules']['EXAMPLE']['static_goal'] = 'trace timeout as well'
        path.write_text(json.dumps(reference))
        second = run(self.ws, engine=Recording([self.payload]), **self.kwargs)
        self.assertEqual(second['summary']['from_cache'], 0)
        self.assertEqual(first['metrics']['rules'][0]['base_reference_snippets'], 1)

    def test_tampered_cached_evidence_cannot_be_pass(self):
        valid=json.dumps({'rule_id':'EXAMPLE','status':'PASS','evidence':[{'file':'sources/demo/App.java','line':2,'excerpt':'Example.init();'}]})
        run(self.ws,engine=ReplayEngine([valid]),**self.kwargs)
        cache_file=next((self.root/'cache/verdicts').glob('*.json'))
        data=json.loads(cache_file.read_text()); data['finding']['evidence'][0]['line']=999
        cache_file.write_text(json.dumps(data))
        report=run(self.ws,engine=ReplayEngine([self.payload]),**self.kwargs)
        self.assertEqual(report['summary']['pass'],0)
        self.assertEqual(report['summary']['from_cache'],0)

    def test_checkpoint_resume_reuses_completed_rules_without_verdict_cache(self):
        report=run(self.ws,engine=ReplayEngine([self.payload]),**self.kwargs)
        for path in (self.root/'cache/verdicts').glob('*.json'):
            path.unlink()
        resumed=run(self.ws,engine=ReplayEngine([]),resume=True,**self.kwargs)
        self.assertEqual(resumed['summary']['from_cache'],1)
        self.assertTrue(resumed['metrics']['rules'][0]['from_checkpoint'])
        (self.ws/'sources/demo/App.java').write_text('class Changed {}')
        changed=run(self.ws,engine=ReplayEngine([self.payload]),resume=True,**self.kwargs)
        self.assertFalse(changed['metrics']['rules'][0]['from_checkpoint'])

    def test_crossflow_warm_cache_uses_semantic_prior_not_execution_flags(self):
        (self.pack/'rules/b.yaml').write_text('- id: ADS_CROSS_FLOW_BUGS\n  title: Cross\n  mode: agent\n  question: Inspect\n  verdict: {pass_when: "yes", fail_when: "no", unknown_when: unclear}\n')
        response=json.dumps({'rule_id':'ADS_CROSS_FLOW_BUGS','status':'UNKNOWN','evidence':[]})
        first=run(self.ws,engine=ReplayEngine([self.payload,response]),cross_flow=True,**self.kwargs)
        warm=run(self.ws,engine=ReplayEngine([]),cross_flow=True,**self.kwargs)
        self.assertEqual(warm['summary']['from_cache'],2)


class CacheIdentityTests(unittest.TestCase):
    def test_unknown_claude_model_is_not_reused_and_explicit_model_invalidates(self):
        from apk_audit.cache_identity import engine_identity
        fake=type('Engine',(),{'name':'claude:default','requires_claims':True})()
        with patch('apk_audit.cache_identity.cli_version',return_value='Claude 2'):
            identity,reusable=engine_identity(fake)
            self.assertFalse(reusable)
            fake.model='sonnet-explicit'
            first,ok=engine_identity(fake)
            self.assertTrue(ok)
            fake.model='opus-explicit'
            second,ok=engine_identity(fake)
            self.assertNotEqual(first,second)

    def test_reasoning_effort_changes_engine_cache_identity(self):
        from apk_audit.cache_identity import engine_identity
        fake=type('Engine',(),{'name':'codex:gpt-6.1-sol','model':'gpt-6.1-sol',
                               'requires_claims':True,'reasoning_effort':'medium'})()
        with patch('apk_audit.cache_identity.cli_version',return_value='codex 1'):
            medium,_=engine_identity(fake)
            fake.reasoning_effort='high'
            high,_=engine_identity(fake)
        self.assertNotEqual(medium,high)
        self.assertEqual(medium['reasoning_effort'],'medium')

    def test_pinned_claude_model_can_reuse_cache_with_known_cli_version(self):
        from apk_audit.cache_identity import engine_identity
        from apk_audit.claude_engine import ClaudeEngine
        with patch('apk_audit.cache_identity.cli_version',return_value='Claude 2'):
            identity,reusable=engine_identity(ClaudeEngine())
        self.assertTrue(reusable)
        self.assertEqual(identity['model'],'sonnet')
        self.assertEqual(identity['reasoning_effort'],'low')

    def test_cli_upgrade_is_seen_by_next_job_in_same_server(self):
        import os
        from apk_audit.cache_identity import cli_version
        with tempfile.TemporaryDirectory() as tmp:
            binary=Path(tmp)/'codex'
            binary.write_text('#!/bin/sh\necho codex-fixture-v1\n'); binary.chmod(0o755)
            with patch.dict(os.environ,{'PATH':tmp+':'+os.environ['PATH']}):
                first=cli_version('codex')
                binary.write_text('#!/bin/sh\necho codex-fixture-v2\n')
                second=cli_version('codex')
            self.assertEqual(first,'codex-fixture-v1')
            self.assertEqual(second,'codex-fixture-v2')

class CacheValidationTests(unittest.TestCase):
    def test_corrupt_verification_evidence_and_missing_review_trace_are_cache_misses(self):
        from apk_audit.agent import _verify_evidence
        from apk_audit.pipeline import _cached_finding
        from apk_audit.tools import WorkspaceTools
        from apk_audit.utils import digest_json
        cases=json.loads(Path('apk_audit/quality_cases.json').read_text())['cases']
        case=next(c for c in cases if c['id']=='static-fail-reviewed')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,text in case['workspace'].items():
                path=root/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text)
            tools=WorkspaceTools(root); payload=case['review']; rule=Rule(payload['rule_id'],'Check','agent',hint=payload.get('hint',''))
            finding=Finding.for_rule(rule,status='FAIL',reasoning=payload['reasoning'],claims=payload['claims'],
                                     evidence=_verify_evidence(payload,tools),
                                     verification={'review':'accepted'})
            trace={'attempts':[{'review':True,'text':json.dumps(payload),'tool_calls':1}]}
            def record(data,trace_data):
                result={'finding':data,'trace':trace_data}
                result['checksum']=digest_json(result)
                return result
            valid=record(finding.to_dict(),trace)
            self.assertIsNotNone(_cached_finding(valid,rule,tools,True))
            for field,value in [('verification',None),('evidence',None),('evidence',1),('claims',None),('status',[])]:
                altered=finding.to_dict(); altered[field]=value
                with self.subTest(field=field,value=value):
                    self.assertIsNone(_cached_finding(record(altered,trace),rule,tools,True))
            self.assertIsNone(_cached_finding(record(finding.to_dict(),{}),rule,tools,True))
            altered=finding.to_dict(); altered['reasoning']='Invented conclusion despite different review'
            self.assertIsNone(_cached_finding(record(altered,trace),rule,tools,True))

    def test_observed_budget_overrun_is_visible_and_no_further_tool_budget_is_issued(self):
        from apk_audit.execution import execute_rules,RuleOutcome
        allocations=[]
        def work(rule,budget,prior):
            allocations.append(budget)
            return RuleOutcome(Finding.for_rule(rule,tool_calls=budget+1 if budget else 0,
                                               exhausted_budget=bool(budget),reason='tool_budget'))
        outcomes,used=execute_rules([Rule('A','A','agent'),Rule('B','B','agent')],work,max_tool_calls=2,workers=1)
        self.assertEqual(allocations,[2,0])
        self.assertEqual(used,3)
        self.assertEqual(outcomes[0].finding.status,'UNKNOWN')
