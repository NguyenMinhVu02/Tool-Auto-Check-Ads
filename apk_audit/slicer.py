"""Pre-extract the code each rule needs so the AI starts with the answer's raw material.

Instead of letting the model grep a whole decompiled app (a dozen commands, each re-sending the
whole conversation), the tool cuts out, deterministically, the methods that matter for the rule's
scope: initialisation, Remote Config / consent / local fallback, ad IDs, and the first four
screens. Anchors that survive obfuscation drive the selection: manifest class names, string
literals (placement names, config keys), Android lifecycle names and well-known API calls.
Blocks carry real file paths and real line numbers, so the model can cite them directly and the
usual evidence verification still applies. This is a navigation aid, never proof.
"""
from pathlib import Path
import re

from .utils import read_text

SLICE_VERSION = 2
SKIP_METHODS = {'if', 'for', 'while', 'switch', 'catch', 'synchronized', 'return', 'new', 'else', 'try', 'do'}
SIGNATURE = re.compile(
    r'^\s*(?:@\w+(?:\([^)]*\))?\s+)*(?:(?:public|private|protected|static|final|synchronized|abstract|native)\s+)*'
    r'(?:[\w<>\[\]?,.\s]+?\s+)?(\w+)\s*\([^;{}]*\)\s*(?:throws [\w.,\s]+)?\{\s*$')
AD_PATTERN = re.compile(
    r'\b(?:load\w*|show\w*|observe|postValue|getShouldDisplay\w*|AppOpenAd|InterstitialAd|NativeAd|AdView|MobileAds|'
    r'ERainAd\w*|FirebaseRemoteConfig|fetchAndActivate|setDefaultsAsync|ConsentInformation|UserMessagingPlatform|'
    r'ConsentHandler|ITGAdConsent|loadAndShowConsent|requestConsent\w*|onConsent\w*|isConfirmConsent|isUserGlobal|'
    r'canRequestAds|requestConsentInfoUpdate|isEnable|enable_ua_check|getId|fromAssets|fromJson)\b')
LIFECYCLE = {'onCreate', 'onResume', 'onStart', 'onViewCreated', 'onCreateView', 'onPause', 'attachBaseContext'}
REMOTE_LITERALS = ('ad_remote_config', 'on_show_dialog_consent', 'delay_button_done_language',
                   'time_delay_show_language_done_button', 'ad_config.json', 'ad_config_debug.json', 'fetchAndActivate',
                   'ConsentInformation', 'UserMessagingPlatform', 'enable_ua_check')
# Consent lives in Splash: event literals and the GDPR module calls survive R8 and point at the handler.
CONSENT_LITERALS = ('load_consent', 'display_consent', 'agree_consent', 'refuse_consent', 'consent_error',
                    'ITGAdConsent', 'loadAndShowConsent', 'requestConsentInfoUpdate')
SCREENS = {'splash': ('splash',), 'language': ('language',), 'onboarding': ('onboarding',), 'welcome': ('welcome',)}
SCREEN_PLACEMENTS = {'splash': ('splash',), 'language': ('language',), 'onboarding': ('onboarding',),
                     'welcome': ('welcome', 'resume')}
AREA_BUDGET = {'init': 14000, 'remote_config': 30000, 'config': 24000, 'splash': 26000, 'language': 24000,
               'onboarding': 26000, 'welcome': 22000}
AREA_BUDGET['splash'] = 30000  # +consent handler
# Third-party code is noise for these rules (the app's own and obfuscated app packages stay in).
LIBRARY_PREFIXES = tuple('sources/' + p for p in (
    'android/', 'androidx/', 'kotlin/', 'kotlinx/', 'com/google/', 'com/facebook/', 'com/applovin/', 'com/adjust/',
    'com/bytedance/', 'com/vungle/', 'com/mbridge/', 'com/unity3d/', 'com/ironsource/', 'com/squareup/', 'okhttp3/',
    'retrofit2/', 'org/', 'dagger/', 'javax/', 'com/amazon/', 'com/fyber/', 'com/inmobi/', 'com/chartboost/',
    'com/yandex/', 'com/bumptech/', 'com/airbnb/', 'com/github/', 'com/ads/', 'com/itg/devconfig/', 'com/itg/iaumodule/', 'io/'))
MAX_BLOCK_LINES = 110
MAX_HOP_LINES = 70


def _strip(line, state):
    """Remove strings/comments so braces inside them do not move the depth counter."""
    out, i = [], 0
    while i < len(line):
        if state['block']:
            end = line.find('*/', i)
            if end < 0:
                return ''.join(out)
            state['block'], i = False, end + 2
            continue
        pair = line[i:i + 2]
        if pair == '/*':
            state['block'], i = True, i + 2
        elif pair == '//':
            break
        elif line[i] in '"\'':
            quote, i = line[i], i + 1
            while i < len(line) and line[i] != quote:
                i += 2 if line[i] == '\\' else 1
            i += 1
        else:
            out.append(line[i])
            i += 1
    return ''.join(out)


def parse_methods(lines):
    """[{name, start, end}] (1-based, inclusive) for every method/constructor with a body."""
    state = {'block': False}
    depth_before, delta = [], []
    depth = 0
    for line in lines:
        clean = _strip(line, state)
        opens, closes = clean.count('{'), clean.count('}')
        depth_before.append(depth)
        delta.append(opens - closes)
        depth += opens - closes
    methods = []
    for index, line in enumerate(lines):
        match = SIGNATURE.match(line)
        if not match or match.group(1) in SKIP_METHODS or delta[index] != 1 or depth_before[index] < 1:
            continue
        start_depth, end = depth_before[index], None
        for later in range(index + 1, len(lines)):
            if depth_before[later] + delta[later] == start_depth:
                end = later
                break
        if end is None:
            continue
        start = index
        while start > 0 and lines[start - 1].strip().startswith('@'):
            start -= 1
        methods.append({'name': match.group(1), 'start': start + 1, 'end': end + 1})
    return methods


class Slicer:
    def __init__(self, workspace, facts, files, placements):
        self.root = Path(workspace).resolve()
        self.facts = facts
        self.placements = tuple(sorted(placements))
        self.files = [Path(p) for p in files if str(p).endswith('.java')]
        self._lines, self._methods, self._hits = {}, {}, None
        manifest_package = (facts.get('source') or {}).get('package') or ''
        application = (facts.get('manifest') or {}).get('application_class') or ''
        self.roots = tuple(r for r in (('sources/' + manifest_package.replace('.', '/') + '/') if manifest_package else '',
                                       ('sources/' + '/'.join(application.split('.')[:3]) + '/') if application.count('.') >= 3 else '') if r)
        self.getters = tuple(f'get{n[:1].upper()}{n[1:]}(' for n in self.placements)
        self.by_name = {}
        self.default_pkg = {}   # R8 puts many classes in the default package: referenced by bare name, never imported
        for path in self.files:
            self.by_name.setdefault(path.stem, []).append(path)
            if path.parent.name == 'defpackage' or path.parent == self.root / 'sources':
                self.default_pkg.setdefault(path.stem, path)

    # -- file helpers -----------------------------------------------------------------
    def rel(self, path):
        return Path(path).resolve().relative_to(self.root).as_posix()

    def lines(self, path):
        key = str(path)
        if key not in self._lines:
            try:
                self._lines[key] = read_text(Path(path)).splitlines()
            except (OSError, ValueError):
                self._lines[key] = []
        return self._lines[key]

    def methods(self, path):
        key = str(path)
        if key not in self._methods:
            self._methods[key] = parse_methods(self.lines(path))
        return self._methods[key]

    def score(self, text):
        hits = len(AD_PATTERN.findall(text))
        names = sum(1 for name in self.placements if f'"{name}"' in text)
        getters = sum(1 for getter in self.getters if getter in text)
        return hits + 4 * (names + getters)

    # -- seeds ------------------------------------------------------------------------
    def hits(self):
        """{file: set(literals)} from ONE pass over every source file."""
        if self._hits is None:
            needles = set(REMOTE_LITERALS) | set(CONSENT_LITERALS) | {f'"{n}"' for n in self.placements} | set(self.getters) | {'OPEN_RESUME'}
            self._hits = {}
            for path in self.files:
                if self.rel(path).startswith(LIBRARY_PREFIXES):
                    continue
                try:
                    text = read_text(path)
                except (OSError, ValueError):
                    continue
                found = {n for n in needles if n in text}
                if found:
                    self._hits[path] = found
        return self._hits

    def files_with(self, needles):
        return [p for p, found in self.hits().items() if found & set(needles)]

    def declared_activities(self, fragments):
        found = []
        for activity in (self.facts.get('manifest') or {}).get('activities') or []:
            name = activity.get('name', '')
            if any(f in name.rsplit('.', 1)[-1].lower() for f in fragments) and name.startswith(self.roots_packages()):
                found.append(activity)
        return found

    def roots_packages(self):
        return tuple(r[len('sources/'):].rstrip('/').replace('/', '.') for r in self.roots) or ('',)

    def activity_files(self, fragments):
        base = {}
        for activity in self.declared_activities(fragments):
            if activity.get('file') and (self.root / activity['file']).is_file():
                base[activity['file']] = self.root / activity['file']
        return list(base.values())

    def missing_screen_files(self, area):
        return [a['name'] for a in self.declared_activities(SCREENS.get(area, ()))
                if not (a.get('file') and (self.root / a['file']).is_file())]

    def seeds(self, area):
        manifest = self.facts.get('manifest') or {}
        application = manifest.get('application_file')
        app_file = [self.root / application] if application and (self.root / application).is_file() else []
        if area == 'init':
            return [(p, 10) for p in app_file]
        if area == 'remote_config':
            return [(p, 0) for p in self.files_with(REMOTE_LITERALS)] + [(p, 12) for p in self.activity_files(SCREENS['splash'])] \
                + [(p, 6) for p in app_file]
        if area == 'config':
            keyed = [p for p, found in self.hits().items() if sum(f.startswith('"') for f in found) >= 2]
            return [(p, 0) for p in keyed + self.files_with(('enable_ua_check',))]
        if area in SCREENS:
            screen = self.activity_files(SCREENS[area])
            fragments = SCREEN_PLACEMENTS[area]
            # A registry that names almost every placement (the config parser) is context for the ID rule, not for a screen.
            literal = [p for p, found in self.hits().items()
                       if sum(f.startswith('"') or f.startswith('get') for f in found) <= 6
                       and any((f.startswith('"') or f.startswith('get') or f == 'OPEN_RESUME')
                               and any(frag in f.lower() for frag in fragments) for f in found)]
            siblings = [s for p in screen for s in p.parent.glob('*.java')
                        if s != p and any(f in s.stem.lower() for f in SCREENS[area]) and len(self.lines(s)) <= 260]
            consent = [(p, 6) for p in self.files_with(CONSENT_LITERALS)] if area == 'splash' else []
            return [(p, 20) for p in screen] + [(p, 8) for p in siblings] + consent + [(p, 0) for p in literal]
        return []

    # -- extraction -------------------------------------------------------------------
    def pick(self, path, wanted=None, hop=False, bonus=0):
        lines, picked = self.lines(path), []
        for method in self.methods(path):
            body = '\n'.join(lines[method['start'] - 1:method['end']])
            score = self.score(body)
            if wanted is not None and method['name'] not in wanted:
                continue
            if hop and (method['end'] - method['start'] > MAX_HOP_LINES and not score):
                continue
            if wanted is None and not score and method['name'] not in LIFECYCLE:
                continue
            extra = bonus + (6 if method['name'] in LIFECYCLE else 0)
            picked.append((max(score + extra - (3 if hop else 0), 1), path, method))
        return picked

    def hops(self, blocks):
        """One hop: app classes the selected methods call or instantiate (`X.m(`, `new X(`, `new pkg.X(`)."""
        wanted, whole = {}, set()
        for _, path, method in blocks:
            lines = self.lines(path)
            text = '\n'.join(lines[method['start'] - 1:method['end']])
            imports = {}
            for line in lines[:80]:
                m = re.match(r'import ([\w.]+)\.(\w+);', line)
                if m:
                    imports[m.group(2)] = m.group(1).replace('.', '/') + '/' + m.group(2) + '.java'
            def resolve(name):
                if name in imports and (self.root / 'sources' / imports[name]).is_file():
                    return self.root / 'sources' / imports[name]
                near = [p for p in self.by_name.get(name, []) if p.parent == path.parent]
                return near[0] if near else self.default_pkg.get(name)
            for cls, call in set(re.findall(r'\b([A-Za-z_]\w*)\.(\w+)\(', text)):
                target = resolve(cls)
                if target and target != path and self.in_scope(target, path):
                    wanted.setdefault(target, set()).add(call)
            for token in set(re.findall(r'\b([A-Za-z_]\w{1,5})\b', text)):   # bare references to default-package classes
                target = self.default_pkg.get(token)
                if target and target != path and token not in imports:
                    whole.add(target)
            for qualified in set(re.findall(r'\bnew ([A-Za-z_][\w.]*)\(', text)):
                parts = qualified.split('.')
                target = (self.root / 'sources' / '/'.join(parts)).with_suffix('.java') if len(parts) > 1 else resolve(parts[0])
                if target and target.is_file() and target != path and self.in_scope(target, path):
                    whole.add(target)
        picked = []
        for target, names in wanted.items():
            picked += self.pick(target, wanted=names, hop=True)
        for target in whole:
            lines = self.lines(target)
            if len(lines) <= 130:
                picked.append((12, target, {'name': target.stem, 'start': 1, 'end': len(lines)}))
            else:
                picked += self.pick(target, hop=True)
        return picked

    def in_scope(self, target, origin):
        relative = self.rel(target)
        return target.parent == origin.parent or (relative.startswith(self.roots or ('sources/',))
                                                  or not relative.startswith(LIBRARY_PREFIXES))

    def format_block(self, path, method):
        lines = self.lines(path)
        start, end = method['start'], min(method['end'], method['start'] + MAX_BLOCK_LINES - 1)
        width = len(str(end))
        body = '\n'.join(f'{n:>{width}}| {lines[n - 1]}' for n in range(start, end + 1))
        note = '' if end == method['end'] else f"\n{' ' * width}| ... (cắt, hàm dài tới dòng {method['end']})"
        return f"// {self.rel(path)}:{start}-{end} ({method['name']})\n{body}{note}\n"

    def build(self, area):
        budget = AREA_BUDGET.get(area)
        if not budget:
            return ''
        seeds, seen = [], set()
        for path, bonus in self.seeds(area):
            if path not in seen:
                seen.add(path)
                seeds.append((path, bonus))
        blocks = [b for path, bonus in seeds for b in self.pick(path, bonus=bonus)]
        for path, bonus in seeds:   # tiny helpers/enums (e.g. a route enum) are cheap and often decisive: take them whole
            lines = self.lines(path)
            if 0 < len(lines) <= 40 and not any(b[1] == path for b in blocks):
                blocks.append((max(bonus, 2), path, {'name': path.stem, 'start': 1, 'end': len(lines)}))
        first = self.hops(sorted(blocks, key=lambda b: -b[0])[:12])
        blocks += first
        blocks += self.hops(sorted(first, key=lambda b: -b[0])[:6])   # second hop: helpers of helpers (obfuscated chains)
        out, used, taken = [], 0, set()
        for score, path, method in sorted(blocks, key=lambda b: (-b[0], self.rel(b[1]), b[2]['start'])):
            key = (str(path), method['start'])
            if key in taken:
                continue
            block = self.format_block(path, method)
            if used + len(block) > budget:
                continue
            taken.add(key)
            used += len(block)
            out.append((self.rel(path), method['start'], block))
        out.sort(key=lambda item: (item[0], item[1]))
        notes = ''.join(f'// KHÔNG CÓ MÃ: {name} khai báo trong manifest nhưng JADX không xuất được file; '
                        'không kết luận lỗi chỉ vì không thấy mã của màn này\n' for name in self.missing_screen_files(area))
        return notes + '\n'.join(block for _, _, block in out)


def build_slices(workspace, facts, files, placements, areas=AREA_BUDGET):
    slicer = Slicer(workspace, facts, files, placements)
    return {area: slicer.build(area) for area in areas}
