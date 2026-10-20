"""Bounded rule scheduling; cross-flow sees finalized findings, never partial futures."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass, field
import time

from .contracts import Finding

CROSS_FLOW_RULE = 'ADS_CROSS_FLOW_BUGS'
MAX_WORKERS = 10  # one per independent rule; cross-flow always runs after them


def valid_workers(workers):
    return type(workers) is int and 1 <= workers <= MAX_WORKERS


@dataclass
class RuleOutcome:
    finding: Finding
    trace: dict = field(default_factory=dict)
    duration_seconds: float = 0.0
    allocated_tool_calls: int = 0


def execute_rules(rules, execute, *, max_tool_calls=400, workers=1, progress=None):
    if not valid_workers(workers):
        raise ValueError(f'workers phải từ 1 đến {MAX_WORKERS}')
    if type(max_tool_calls) is not int or max_tool_calls < 0:
        raise ValueError('max_tool_calls phải >= 0')
    results = {}
    active = {}
    used = 0
    reserved = 0
    completed = 0
    normal = [(i,r) for i,r in enumerate(rules) if r.id != CROSS_FLOW_RULE]
    cross = [(i,r) for i,r in enumerate(rules) if r.id == CROSS_FLOW_RULE]

    def emit(event, index, rule, outcome=None):
        if progress:
            detail = {'index': index+1, 'total': len(rules), 'completed': completed,
                      'rule_id': rule.id, 'title': rule.title,
                      'active_rules': [{'rule_id': r.id, 'title': r.title} for _,r,_ in active.values()]}
            if outcome:
                detail.update(status=outcome.finding.status, from_cache=outcome.finding.from_cache,
                              duration_seconds=outcome.duration_seconds)
            progress(event, detail)

    def invoke(rule, allocation, prior):
        started = time.monotonic()
        outcome = execute(rule, allocation, prior)
        outcome.duration_seconds = time.monotonic()-started
        outcome.allocated_tool_calls = allocation
        return outcome

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='audit-rule') as pool:
        for group in (normal, cross):
            queue = list(group)
            while queue or active:
                while queue and len(active) < workers:
                    available = max(0, max_tool_calls-used-reserved)
                    if not available and active:
                        break  # Wait for unused reservations, don't issue premature UNKNOWN.
                    index,rule = queue.pop(0)
                    allocation = min(rule.budget.get('max_tool_calls',25),available) if rule.mode == 'agent' else 0
                    prior = [results[i].finding.to_dict() for i,_ in normal if i in results] if rule.id == CROSS_FLOW_RULE else None
                    future = pool.submit(invoke,rule,allocation,prior)
                    active[future] = (index,rule,allocation)
                    reserved += allocation
                    emit('start', index, rule)
                if not active:
                    continue
                ready,_ = wait(active,return_when=FIRST_COMPLETED)
                # Stable completion ordering when multiple futures finish in one batch.
                for future in sorted(ready,key=lambda f: active[f][0]):
                    index,rule,allocation = active.pop(future)
                    reserved -= allocation
                    outcome = future.result()
                    calls = 0 if outcome.finding.from_cache else outcome.finding.tool_calls
                    # Keep observed overruns visible; never conceal them in accounting.
                    used += calls
                    results[index] = outcome
                    completed += 1
                    emit('complete',index,rule,outcome)
    return [results[i] for i in range(len(rules))],used
