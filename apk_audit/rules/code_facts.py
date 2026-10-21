"""How trustworthy is "I did not find X" for this decompiled APK?

The input is JADX output, often R8-obfuscated: class and method names can be renamed and some
methods fail to decompile. Absence of a *name* proves nothing then, while strings, manifest
attributes and asset JSON are never renamed. Static rules use this profile to answer
"not found" honestly (inconclusive) instead of reporting a defect.
"""
from pathlib import Path
import re

GAP_MARKERS = re.compile(r'Code restructure failed|Method dump skipped|Failed to decompile|Can\'t decompile')
MAX_READ = 400_000
_cache = {}


def app_roots(facts):
    """Source directories of the app's own code: the manifest package and the Application class package.

    The applicationId often differs from the code package (templates), so both are used.
    """
    roots = set()
    package = (facts.get('source') or {}).get('package') or ''
    if package:
        roots.add('sources/' + package.replace('.', '/') + '/')
    application = (facts.get('manifest') or {}).get('application_class') or ''
    if application.count('.') >= 3:
        roots.add('sources/' + '/'.join(application.split('.')[:3]) + '/')
    return tuple(sorted(roots))


def code_profile(workspace, roots=()):
    root = Path(workspace or '').resolve()
    key = (str(root), tuple(roots))
    if key in _cache:
        return _cache[key]
    sources = root / 'sources'
    classes = short = gaps = app_gaps = 0
    gap_samples = []
    if sources.is_dir():
        for path in sources.rglob('*.java'):
            stem = path.stem
            if stem in {'R', 'BuildConfig'} or stem.startswith('R$'):
                continue
            classes += 1
            short += len(stem) <= 2
            try:
                with path.open('rb') as handle:
                    head = handle.read(MAX_READ).decode('utf-8', 'replace')
            except OSError:
                continue
            if GAP_MARKERS.search(head):
                gaps += 1
                relative = path.relative_to(root).as_posix()
                if not roots or relative.startswith(tuple(roots)):
                    app_gaps += 1
                    if len(gap_samples) < 3:
                        gap_samples.append(relative)
    ratio = short / classes if classes else 0.0
    level = 'cao' if ratio >= 0.3 else 'vừa' if ratio >= 0.1 else 'thấp'
    profile = {'classes': classes, 'short_name_ratio': round(ratio, 3), 'obfuscation': level,
               'decompile_gap_files': app_gaps, 'all_gap_files': gaps, 'gap_samples': gap_samples,
               'app_roots': list(roots)}
    _cache[key] = profile
    return profile


def absence_is_conclusive(profile, subject):
    """May "not found" become a defect?

    literal: strings survive obfuscation; only decompile gaps (code missing from the output) can hide them.
    name: renamed methods/classes make absence meaningless unless obfuscation is low.
    """
    if subject == 'literal':
        return profile['decompile_gap_files'] == 0
    return profile['obfuscation'] == 'thấp' and profile['decompile_gap_files'] == 0


def limits_note(profile):
    return (f"mức làm rối {profile['obfuscation']} ({round(100 * profile['short_name_ratio'])}% tên lớp ≤2 ký tự), "
            f"{profile['decompile_gap_files']} file JADX giải mã lỗi")
