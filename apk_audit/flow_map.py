"""Deterministic map of where the app's ad flow lives, so the AI starts at the right files.

Built once per audit with plain regex over the app's own sources: screen Activities from the
manifest and the lines that load/show/gate ads. It is a navigation aid, not evidence.
"""
import re
from pathlib import Path

from .utils import read_text

SCREENS = (
    ('splash', 'Splash', ('splash',)),
    ('language', 'Language', ('language',)),
    ('onboarding', 'Onboarding', ('onboarding',)),
    ('welcome', 'Welcome', ('welcome',)),
)
CALL_SITES = re.compile(
    r'\b(?:load\w*(?:Native|Inter|Banner|Splash|Ad)\w*|show\w*(?:Inter|Ad|Banner)\w*|getShouldDisplay\w*|'
    r'setOnAdminAdToggleListener\w*|AppOpenAd\.load|fetchAd|initializeFromAssets|fetchAndActivate|'
    r'setIntervalInterstitialAd|preload\w*)\s*\(')
MAX_FILES = 24
MAX_LINES_PER_FILE = 10


def build_flow_map(workspace, facts, files=None):
    root = Path(workspace).resolve()
    package = (facts.get('source') or {}).get('package') or ''
    own = f"sources/{package.replace('.', '/')}/" if package else 'sources/'
    activities = (facts.get('manifest') or {}).get('activities') or []
    screens = {}
    for key, label, fragments in SCREENS:
        matches = [a for a in activities if isinstance(a, dict)
                   and any(f in a.get('name', '').rsplit('.', 1)[-1].lower() for f in fragments)
                   and a.get('name', '').startswith(package) and a.get('file')]
        if matches:
            screens[key] = {'label': label, 'activity': matches[0]['name'].rsplit('.', 1)[-1], 'file': matches[0]['file']}
    candidates = [p for p in (files if files is not None else root.rglob('*.java'))
                  if Path(p).suffix == '.java' and Path(p).resolve().relative_to(root).as_posix().startswith(own)]
    sites = {}
    for path in sorted(candidates):
        relative = Path(path).resolve().relative_to(root).as_posix()
        try:
            lines = read_text(Path(path)).splitlines()
        except (OSError, ValueError):
            continue
        hits = [n for n, line in enumerate(lines, 1) if CALL_SITES.search(line)]
        if hits:
            sites[relative] = hits[:MAX_LINES_PER_FILE]
    ranked = sorted(sites.items(), key=lambda item: (-len(item[1]), item[0]))[:MAX_FILES]
    return {'note': 'Bản đồ điều hướng tạo tự động bằng regex, không phải bằng chứng. Mở file/dòng để xác minh.',
            'screens': screens, 'ad_call_sites': dict(sorted(ranked))}
