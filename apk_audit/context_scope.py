"""Trim shared documents/inventory to what one rule needs before it reaches the AI.

Every tool call in a CLI session re-sends the whole prompt, so bytes cut here are
saved many times over. Areas without a placement focus keep every placement in a
compact form; nothing is dropped from the source documents themselves.
"""
import re

SCOPE_VERSION = 1

# Placement-name fragments relevant to each rule area; None keeps every placement.
AREA_PLACEMENTS = {
    'init': ('open', 'resume', 'app_open'),
    'splash': ('splash', 'language'),
    'language': ('language', 'onboarding'),
    'onboarding': ('onboarding',),
    'welcome': ('welcome', 'resume', 'open'),
    'banner': ('banner',),
}
AREA_TERMS = {
    'init': ('sdk', 'init', 'application', 'open', 'resume', 'interval', 'lifecycle', 'admob'),
    'remote_config': ('remote', 'config', 'firebase', 'fallback', 'timeout', 'debug', 'release'),
    'config': ('id', 'config', 'admob', 'remote', 'placement', 'package'),
    'splash': ('splash', 'uninstall', 'language'),
    'language': ('language', 'click', 'onboarding'),
    'onboarding': ('onboarding', 'fullscreen', 'full screen'),
    'welcome': ('welcome', 'resume', 'open'),
    'render': ('native', 'load', 'show', 'reload', 'purchase', 'offline', 'gate'),
    'tracking': ('event', 'firebase', 'tracking', 'log'),
    'banner': ('banner', 'reload', 'collapsible'),
}
GENERIC_TERMS = ('ads', ' ad ', 'admob', 'native', 'inter', 'banner', 'reward', 'open', 'id', 'remote', 'event')
PLACEMENT_KEYS = ('name', 'ad_type', 'id', 'state', 'line', 'description', 'format', 'note')
CHECKLIST_KEYS = ('line', 'phase', 'task', 'detail', 'status')
MAX_CHECKLIST_ROWS = 40
MAX_CODE_REFS = 3


def _wanted(name, fragments):
    return fragments is None or any(fragment in str(name).lower() for fragment in fragments)


def _compact(row, keys):
    return {key: row[key] for key in keys if row.get(key) not in (None, '', False, [])}


def scope_documents(documents, area):
    fragments = AREA_PLACEMENTS.get(area)
    terms = AREA_TERMS.get(area, GENERIC_TERMS)
    scoped = {}
    ads = documents.get('ads_scripts')
    if isinstance(ads, dict):
        placements = [p for p in ads.get('placements', []) if isinstance(p, dict) and _wanted(p.get('name'), fragments)]
        scoped['ads_scripts'] = {
            **{key: ads[key] for key in ('app_id', 'notes', 'warnings', 'sheet', 'formatting_available') if key in ads},
            'placements': [_compact(p, PLACEMENT_KEYS) for p in placements],
            'scope': {'area': area, 'kept': len(placements), 'total': len(ads.get('placements', []))},
        }
    checklist = documents.get('checklist')
    if isinstance(checklist, dict) and isinstance(checklist.get('checklist_rows'), list):
        rows = checklist['checklist_rows']
        pattern = re.compile('|'.join(re.escape(term) for term in terms), re.I) if terms else None
        kept = [row for row in rows if isinstance(row, dict) and pattern
                and pattern.search(' '.join(str(row.get(k, '')) for k in ('task', 'detail', 'document')))]
        scoped['checklist'] = {
            'checklist_rows': [_compact(row, CHECKLIST_KEYS) for row in kept[:MAX_CHECKLIST_ROWS]],
            'scope': {'area': area, 'kept': min(len(kept), MAX_CHECKLIST_ROWS), 'total': len(rows)},
        }
    elif isinstance(checklist, dict):
        scoped['checklist'] = checklist  # key/value working files are already small
    return scoped


def scope_inventory(inventory_context, area):
    fragments = AREA_PLACEMENTS.get(area)
    scoped = {}
    for key, value in inventory_context.items():
        if key in {'missing_local', 'extra_local', 'mismatched_ids', 'optional_placements',
                   'disabled_placements', 'uncertain_placements'} and isinstance(value, list):
            value = [name for name in value if _wanted(name, fragments)]
        elif key == 'code_references' and isinstance(value, dict):
            # Group by file so long source paths are written once: {file: {placement: [lines]}}.
            grouped = {}
            for name, refs in value.items():
                if not _wanted(name, fragments):
                    continue
                for ref in refs[:MAX_CODE_REFS]:
                    if isinstance(ref, dict) and ref.get('file'):
                        grouped.setdefault(ref['file'], {}).setdefault(name, []).append(ref.get('line'))
            key, value = 'code_references_by_file', grouped
        scoped[key] = value
    return scoped


def compact_prior(prior, max_reasoning=700, max_claims=6):
    """Cross-flow needs each rule's verdict and key claims, not every excerpt again."""
    compact = []
    for item in prior or []:
        claims = [{key: claim.get(key) for key in ('statement', 'kind', 'scope', 'applicability')}
                  for claim in (item.get('claims') or []) if isinstance(claim, dict)][:max_claims]
        evidence = [{'file': entry.get('file'), 'line': entry.get('line'), 'excerpt': str(entry.get('excerpt') or '')[:160]}
                    for entry in (item.get('evidence') or []) if isinstance(entry, dict)][:8]
        compact.append({'rule_id': item.get('rule_id'), 'status': item.get('status'), 'reason': item.get('reason'),
                        'reasoning': str(item.get('reasoning') or '')[:max_reasoning],
                        'claims': claims, 'evidence': evidence})
    return compact
