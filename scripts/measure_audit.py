#!/usr/bin/env python3
"""Run one audit and print time, tokens and verdicts, for before/after comparisons.

Spends AI quota when --engine is claude/codex. Example:
  .venv/bin/python scripts/measure_audit.py APK --engine claude --workers 6 \
      --ads-scripts ads.csv --checklist working.csv --label baseline
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apk_audit import run  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('target')
    parser.add_argument('--engine', default='claude', choices=['claude', 'codex', 'none'])
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--ads-scripts', type=Path)
    parser.add_argument('--checklist', type=Path)
    parser.add_argument('--cache-dir', type=Path, default=Path('out/measure/cache'))
    parser.add_argument('--label', default='run')
    parser.add_argument('--cross-flow', action='store_true')
    parser.add_argument('--refresh', action='store_true', help='Ignore verdict cache (force fresh AI calls)')
    args = parser.parse_args()
    out = Path('out/measure') / f"{time.strftime('%Y%m%d-%H%M%S')}-{args.label}"
    started = time.monotonic()
    report = run(args.target, engine=args.engine, workers=args.workers, out=out, cache_dir=args.cache_dir,
                 ads_scripts=args.ads_scripts, checklist=args.checklist, cross_flow=args.cross_flow,
                 refresh=args.refresh, trace=True)
    wall = time.monotonic() - started
    metrics, summary = report['metrics'], report['summary']
    totals = metrics.get('usage_totals', {})
    print(f"{args.label}: wall={wall:.0f}s rules={metrics['phases'].get('rules', 0):.0f}s "
          f"PASS={summary['pass']} FAIL={summary['fail']} UNKNOWN={summary['unknown']} SKIPPED={summary['skipped']} "
          f"tool_calls={summary['tool_calls']} from_cache={summary['from_cache']}")
    print(f"tokens: input={totals.get('input', 0)} cache_read={totals.get('cache_read', 0)} "
          f"cache_write={totals.get('cache_write', 0)} output={totals.get('output', 0)}")
    for finding, rule in zip(report['findings'], metrics['rules']):
        usage = rule.get('usage', {})
        print(f"  {finding['status']:8} {rule['rule_id']:30} {rule['duration_seconds']:6.1f}s calls={rule['tool_calls']:3} "
              f"att={rule['attempts']} resumed={rule.get('resumed_attempts', 0)} "
              f"cw={usage.get('cache_write', 0)} cr={usage.get('cache_read', 0)} out={usage.get('output', 0)} {finding.get('reason', '')}")
    (out / 'measure.json').write_text(json.dumps({'label': args.label, 'wall_seconds': wall, 'summary': summary,
                                                  'usage_totals': totals, 'phases': metrics['phases']}, indent=2))
    print(f'report: {out}')


if __name__ == '__main__':
    main()
