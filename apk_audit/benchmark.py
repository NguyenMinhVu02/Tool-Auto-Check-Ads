"""Comparable local audit measurements and synthetic verdict guard regression cases."""
import json
from pathlib import Path
import tempfile

from .agent import evaluate
from .contracts import AgentResult, Rule
from .engines import ReplayEngine
from .pipeline import run
from .tools import WorkspaceTools
from .utils import safe_path, write_json


def compare_reports(first, second):
    left = first.get('metrics',{}).get('input_fingerprint')
    right = second.get('metrics',{}).get('input_fingerprint')
    comparable = bool(left and right and left == right)
    statuses = lambda report: [(f['rule_id'],f['status']) for f in report.get('findings',[])]
    equal = statuses(first) == statuses(second)
    result = {'comparable':comparable,'verdicts_equal':equal,'quality_preserved':comparable and equal,
              'note':'Verdict ổn định không thay thế đối chiếu ground truth; cold/warm cache cần đọc riêng.'}
    if comparable:
        duration = second.get('summary',{}).get('duration_seconds',0)
        result['speedup'] = first.get('summary',{}).get('duration_seconds',0)/duration if duration > 0 else None
    else:
        result['reason'] = 'input_or_policy_fingerprint_mismatch'
    return result


def quality_suite():
    fixture_path = Path(__file__).with_name('quality_cases.json')
    fixture = json.loads(fixture_path.read_text(encoding='utf-8'))
    results = []
    for case in fixture['cases']:
        with tempfile.TemporaryDirectory(prefix='apk-quality-') as temp:
            root = Path(temp)
            for relative,text in case['workspace'].items():
                path = safe_path(root,relative)
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(text,encoding='utf-8')
            payload = case['result']
            responses = [AgentResult(json.dumps(payload),tool_calls=case.get('tool_calls',1))]
            if 'review' in case:
                responses.append(AgentResult(json.dumps(case['review']),tool_calls=case.get('review_tool_calls',1)))
            engine = ReplayEngine(responses)
            engine.requires_claims = True
            rule = Rule(payload['rule_id'],'Synthetic quality case','agent', question='Evaluate the explicit fixture contract',
                        verdict={'pass_when':'the stated synthetic flow is compliant',
                                 'fail_when':'the fixture contains a reachable static violation',
                                 'unknown_when':'the evidence does not prove the claim'},
                        budget={'max_tool_calls':case.get('max_tool_calls',10)})
            finding,_ = evaluate(rule,WorkspaceTools(root),engine,'Synthetic fixture; not an APK accuracy claim.')
            expected_reason = case.get('expected_reason')
            matched = finding.status == case['expected_status'] and (expected_reason is None or finding.reason == expected_reason)
            results.append({'id':case['id'],'expected':case['expected_status'],'actual':finding.status,
                            'reason':finding.reason,'expected_reason':expected_reason,'matched':matched})
    tp = sum(c['actual']=='FAIL' and c['expected']=='FAIL' for c in results)
    fp = sum(c['actual']=='FAIL' and c['expected']!='FAIL' for c in results)
    expected_fail = sum(c['expected']=='FAIL' for c in results)
    return {'scope':'synthetic claim guards and targeted-review replay; not live-model or real-APK accuracy',
            'total':len(results),'matched':sum(c['matched'] for c in results),'cases':results,
            'unknown_count':sum(c['actual']=='UNKNOWN' for c in results),'true_fail':tp,'false_fail':fp,
            'false_pass':sum(c['actual']=='PASS' and c['expected']!='PASS' for c in results),
            'fail_precision':{'value':tp/(tp+fp) if tp+fp else None,'numerator':tp,'denominator':tp+fp},
            'fail_recall':{'value':tp/expected_fail if expected_fail else None,'numerator':tp,'denominator':expected_fail}}


def benchmark(target, *, out, rules=None, engine='none', workers=1, repeats=2,
              cache_dir=None, ads_scripts=None, checklist=None):
    if type(repeats) is not int or not 1 <= repeats <= 5:
        raise ValueError('repeats phải trong khoảng 1..5')
    output = Path(out).resolve()
    output.mkdir(parents=True,exist_ok=True)
    cache_root = Path(cache_dir).resolve() if cache_dir else output/'cache'
    cache_root.mkdir(parents=True,exist_ok=True)
    # A fresh namespace ensures a genuine cold index/verdict cache without deleting user caches.
    session_cache = Path(tempfile.mkdtemp(prefix='benchmark-',dir=cache_root))
    runs=[]
    for index in range(repeats):
        result = run(target,rules=rules,out=output/f'run-{index+1}',engine=engine,workers=workers,
                     cache_dir=session_cache,ads_scripts=ads_scripts,checklist=checklist,trace=True)
        runs.append({'label':'cold' if index==0 else 'warm','summary':result['summary'],
                     'metrics':result['metrics'],'findings':result['findings'],'output':result['output']})
    result = {'schema_version':1,'engine':engine,'workers':workers,'runs':runs,
              'cache_dir':str(session_cache),'comparisons':[compare_reports(runs[0],r) for r in runs[1:]],
              'note':'Không có mục tiêu giây cố định. Cache warm không phải tăng tốc một lượt AI đọc mới; engine none không đo chất lượng AI.'}
    write_json(output/'benchmark.json',result)
    return result
