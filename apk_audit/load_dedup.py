"""Find ad slots loaded more than once across or within the first four screens.

Zero AI cost: each screen rule already lists the load calls it read (screen_report.loads, with a
quoted anchor line). This module keeps only loads whose anchor really is at the cited line, then
compares them across screens. It reports; it does not change rule verdicts.
"""

from pathlib import Path

from .utils import read_text

SCREEN_RULES = (
    ('splash', 'Màn Splash', 'ADS_SPLASH_PLACEMENT'),
    ('language', 'Màn chọn ngôn ngữ', 'ADS_LANGUAGE_PLACEMENT'),
    ('onboarding', 'Màn Onboarding', 'ADS_ONBOARDING_PLACEMENT'),
    ('welcome', 'Welcome back / App Open', 'ADS_WELCOME_RESUME'),
)
TRIGGER_LABELS = {'enter': 'khi vào màn', 'resume': 'khi quay lại màn (onResume/onStart)', 'click': 'khi bấm',
                  'callback': 'trong callback', 'other': 'khác'}


def _anchor_at(workspace, item):
    """True when the quoted anchor is on the cited line (±2 lines), whitespace-insensitive."""
    anchor = ''.join(item.get('anchor', '').split())
    if not anchor:
        return False
    try:
        path = (Path(workspace) / item['file']).resolve()
        if not path.is_relative_to(Path(workspace).resolve()):
            return False
        lines = read_text(path).splitlines()
    except (OSError, ValueError):
        return False
    start, end = max(item['line'] - 3, 0), min(item['line'] + 2, len(lines))
    return any(anchor in ''.join(line.split()) or ''.join(line.split()) in anchor and len(line.strip()) > 8
               for line in lines[start:end])


def find_duplicate_loads(findings, workspace):
    by_rule = {f.get('rule_id'): f for f in findings}
    loads = {}
    for key, title, rule_id in SCREEN_RULES:
        report = (by_rule.get(rule_id) or {}).get('screen_report') or {}
        for item in report.get('loads') or []:
            if workspace and not _anchor_at(workspace, item):
                continue
            loads.setdefault(item['slot'], []).append({**item, 'screen': key, 'screen_title': title})
    issues = []
    for slot, items in sorted(loads.items()):
        screens = []
        for item in items:
            if item['screen'] not in screens:
                screens.append(item['screen'])
        sites = [{'screen': i['screen_title'], 'location': f"{i['file']}:{i['line']}",
                  'trigger': TRIGGER_LABELS.get(i['trigger'], i['trigger']), 'guarded': i['guarded']} for i in items]
        if len(screens) > 1:
            issues.append({'slot': slot, 'kind': 'cross_screen', 'sites': sites,
                           'message': f"{slot} được tải ở {len(screens)} màn: "
                                      + ', '.join(dict.fromkeys(i['screen_title'] for i in items))
                                      + '. Mỗi vị trí chỉ nên được tải ở một màn (preload rồi dùng lại).'})
            continue
        unguarded = [i for i in items if not i['guarded']]
        distinct = {(i['file'], i['line']) for i in items}
        if any(i['trigger'] == 'resume' and not i['guarded'] for i in items):
            issues.append({'slot': slot, 'kind': 'reload_on_resume', 'sites': sites,
                           'message': f"{slot} được tải lại mỗi lần quay lại {items[0]['screen_title']} "
                                      '(onResume/onStart) mà không có điều kiện chặn.'})
        elif len(distinct) > 1 and len(unguarded) > 1:
            issues.append({'slot': slot, 'kind': 'same_screen_twice', 'sites': sites,
                           'message': f"{slot} có {len(distinct)} chỗ gọi tải trong {items[0]['screen_title']} "
                                      'mà không có điều kiện chặn, có thể bị tải 2 lần.'})
    return {'issues': issues, 'checked_slots': len(loads),
            'screens_reported': [key for key, _, rule_id in SCREEN_RULES
                                 if ((by_rule.get(rule_id) or {}).get('screen_report') or {}).get('loads')]}
