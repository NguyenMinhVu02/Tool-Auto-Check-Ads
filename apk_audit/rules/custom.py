"""Deterministic checks that need the decompiled workspace, not just facts paths.

They run without AI: cheap, repeatable, and every claim points at a file/line.
"""
import fnmatch
import json
import re
from pathlib import Path

from ..documents import normalize_ads_document
from ..utils import read_text


def _line_of(text, key):
    needle = f'"{key}"'
    for number, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return number, line.strip()
    return 1, ''


def _evidence(file, line, excerpt):
    return {'file': file, 'line': line, 'excerpt': excerpt, 'verified': True}


def _ua_value(config):
    """UA flag of one placement: the app's JSON adapter reads `enable_ua_check`; accept camelCase too."""
    for name in ('enable_ua_check', 'enableUaCheck'):
        if isinstance(config.get(name), bool):
            return config[name]
    return None


def ad_config_flags(rule, facts, documents, workspace):
    """isEnable follows ADS SCRIPTS state; enable_ua_check is true only for the listed placements."""
    files = rule.params.get('files', ['ad_config.json', 'ad_config_debug.json'])
    ua_patterns = rule.params.get('ua_check_true', [])
    ads = normalize_ads_document((documents or {}).get('ads_scripts', {}))
    rows = {row['name']: row for row in (ads.get('placements') or []) if isinstance(row, dict) and row.get('name')} \
        if isinstance(ads, dict) else {}
    optional = {name.lower() for name in rule.params.get('optional', ['inter_onboarding'])}
    issues, evidence, checked = [], [], []
    for name in files:
        config = facts.get('assets', {}).get('json', {}).get(name)
        if not isinstance(config, dict):
            continue
        relative = f'resources/assets/{name}'
        try:
            text = read_text(Path(workspace) / relative) if workspace else ''
        except OSError:
            text = ''
        checked.append(name)
        for key, value in config.items():
            if not isinstance(value, dict) or 'id' not in value:
                continue
            line, excerpt = _line_of(text, key)
            ua_expected = any(fnmatch.fnmatch(key, pattern) for pattern in ua_patterns)
            ua_value = _ua_value(value)
            ua_actual = ua_value is True
            if ua_actual != ua_expected:
                issues.append({'file': name, 'placement': key, 'field': 'enable_ua_check',
                               'expected': ua_expected, 'actual': 'không khai báo (mặc định false)' if ua_value is None else ua_value})
                evidence.append(_evidence(relative, line, excerpt))
            row = rows.get(key)
            if row and key.lower() not in optional and row.get('state') in {'active', 'disabled'}:
                enable_expected = row['state'] == 'active'
                if value.get('isEnable') is not enable_expected:
                    issues.append({'file': name, 'placement': key, 'field': 'isEnable',
                                   'expected': enable_expected, 'actual': value.get('isEnable')})
                    evidence.append(_evidence(relative, line, excerpt))
    finding_fields = {'expected': {'enable_ua_check_true': ua_patterns, 'isEnable': 'theo trạng thái ADS SCRIPTS'
                                   if rows else 'chưa có ADS SCRIPTS, chỉ kiểm enable_ua_check'}}
    if not checked:
        return dict(finding_fields, status='UNKNOWN', reason='missing_fact',
                    reasoning='Không tìm thấy ad_config.json/ad_config_debug.json trong assets của APK.',
                    marketing_summary='Không tìm thấy file cấu hình quảng cáo trong app, cần dev kiểm tra.')
    ua_bad = sorted({i['placement'] for i in issues if i['field'] == 'enable_ua_check'})
    enable_bad = sorted({i['placement'] for i in issues if i['field'] == 'isEnable'})
    if not issues:
        return dict(finding_fields, status='PASS', actual={'files': checked},
                    reasoning=f"Kết luận: isEnable và enable_ua_check đúng yêu cầu trong {', '.join(checked)}.",
                    marketing_summary='Cờ bật/tắt quảng cáo và kiểm tra người dùng UA trong app đã đúng yêu cầu.')
    parts = []
    if ua_bad:
        parts.append('enable_ua_check sai ở ' + ', '.join(ua_bad))
    if enable_bad:
        parts.append('isEnable lệch ADS SCRIPTS ở ' + ', '.join(enable_bad))
    plain = []
    if ua_bad:
        plain.append(f'{len(ua_bad)} vị trí quảng cáo chưa đặt đúng chế độ kiểm tra người dùng UA '
                     '(chỉ 4 native full screen Onboarding được bật), nên có thể hiện quảng cáo sai nhóm người dùng')
    if enable_bad:
        plain.append(f'{len(enable_bad)} vị trí quảng cáo bật/tắt khác ADS SCRIPTS')
    return dict(finding_fields, status='FAIL', actual={'files': checked, 'issues': issues}, evidence=evidence[:40],
                reasoning='Kết luận: ' + '; '.join(parts) + '.\nCần sửa: chỉnh giá trị trong '
                          + ', '.join(sorted({i['file'] for i in issues})) + ' theo yêu cầu.',
                marketing_summary='; '.join(plain) + '.')


def language_dev_toggle(rule, facts, documents, workspace):
    """The Language screen title must open the DevConfig admin/organic toggle (Unlimited ads bypass)."""
    marker = rule.params.get('marker', 'setOnAdminAdToggleListener')
    sources = Path(workspace or '') / 'sources'
    if not workspace or not sources.is_dir():
        return {'status': 'UNKNOWN', 'reason': 'missing_fact', 'reasoning': 'Không có thư mục sources đã giải mã.'}
    library = any(sources.glob('com/itg/devconfig/**/*.java'))
    hits, screens = [], []
    for path in sources.rglob('*.java'):
        relative = path.relative_to(workspace).as_posix()
        name = path.name.lower()
        if 'language' not in name or '/itg/devconfig/' in relative:
            continue
        if name.endswith(('activity.java', 'fragment.java')):
            screens.append(relative)
        try:
            for number, line in enumerate(read_text(path).splitlines(), 1):
                if marker in line:
                    hits.append(_evidence(relative, number, line.strip()))
        except OSError:
            continue
    if hits:
        return {'status': 'PASS', 'actual': {'files': sorted({h['file'] for h in hits})}, 'evidence': hits[:5],
                'reasoning': f'Kết luận: màn Language đã gắn mở Dev setting ({marker}).',
                'marketing_summary': 'Màn chọn ngôn ngữ đã gắn mở Dev setting, có thể bật Unlimited ads để test.'}
    if not screens:
        return {'status': 'UNKNOWN', 'reason': 'missing_fact',
                'reasoning': 'Không xác định được màn Language trong mã đã giải mã (có thể bị obfuscate).',
                'marketing_summary': 'Chưa tìm được màn chọn ngôn ngữ trong app, cần dev kiểm tra Dev setting.'}
    return {'status': 'FAIL', 'actual': {'language_screens': screens[:5], 'devconfig_library': library},
            'reasoning': 'Kết luận: màn Language chưa gắn ' + marker
                         + ('' if library else '; app cũng chưa tích hợp thư viện DevConfig') + '.\n'
                         + 'Cần sửa: gắn setOnAdminAdToggleListener vào tiêu đề màn Language như base.',
            'marketing_summary': 'Màn chọn ngôn ngữ chưa gắn mở Dev setting, nên không bật được Unlimited ads '
                                 '(luôn coi là người dùng non-organic) để test quảng cáo.'}


def _app_sources(workspace, facts):
    """Sources of the app's own package when it exists, otherwise every decompiled source."""
    root = Path(workspace or '')
    sources = root / 'sources'
    package = (facts.get('source') or {}).get('package') or ''
    own = sources / package.replace('.', '/') if package else None
    return (own if own and own.is_dir() else sources), root


def _grep(workspace, facts, pattern, limit=20):
    base, root = _app_sources(workspace, facts)
    regex = re.compile(pattern)
    hits = []
    if not base.is_dir():
        return None
    for path in sorted(base.rglob('*.java')):
        try:
            for number, line in enumerate(read_text(path).splitlines(), 1):
                match = regex.search(line)
                if match:
                    hits.append((path.relative_to(root).as_posix(), number, line.strip(), match))
                    if len(hits) >= limit:
                        return hits
        except OSError:
            continue
    return hits


def remote_config_keys(rule, facts, documents, workspace):
    """Remote Config keys the base reads must exist in the app (string literals in its own code)."""
    required = rule.params.get('required', [])
    optional = rule.params.get('optional', [])
    found, missing, evidence = {}, [], []
    for key in required + optional:
        hits = _grep(workspace, facts, r'"' + re.escape(key) + r'"', limit=1)
        if hits is None:
            return {'status': 'UNKNOWN', 'reason': 'missing_fact',
                    'reasoning': 'Không có thư mục sources đã giải mã để kiểm key Remote Config.'}
        if hits:
            found[key] = f'{hits[0][0]}:{hits[0][1]}'
            evidence.append(_evidence(hits[0][0], hits[0][1], hits[0][2]))
        elif key in required:
            missing.append(key)
    expected = {'required': required, 'optional': optional}
    if missing:
        return {'status': 'FAIL', 'expected': expected, 'actual': {'missing': missing, 'found': found}, 'evidence': evidence,
                'reasoning': 'Kết luận: thiếu key Remote Config bắt buộc: ' + ', '.join(missing)
                             + '.\nCần sửa: khai báo và đọc các key này như base (RemoteConfigUtils).',
                'marketing_summary': f'App chưa có {len(missing)} cấu hình điều khiển từ xa bắt buộc ('
                                     + ', '.join(missing) + '), nên không chỉnh được quảng cáo qua Firebase.'}
    return {'status': 'PASS', 'expected': expected, 'actual': {'found': found}, 'evidence': evidence,
            'reasoning': 'Kết luận: đủ key Remote Config bắt buộc trong mã app.',
            'marketing_summary': 'App có đủ các cấu hình điều khiển từ xa bắt buộc.'}


def interstitial_interval(rule, facts, documents, workspace):
    """Interval between two interstitials set on the SDK config (ADS SCRIPTS default: 35s)."""
    expected = rule.params.get('seconds', 35)
    hits = _grep(workspace, facts, r'setIntervalInterstitialAd\(\s*(\d+)\s*\)')
    if hits is None:
        return {'status': 'UNKNOWN', 'reason': 'missing_fact', 'reasoning': 'Không có thư mục sources đã giải mã.'}
    if not hits:
        return {'status': 'UNKNOWN', 'expected': expected, 'reason': 'missing_fact',
                'reasoning': 'Không thấy lệnh đặt khoảng cách giữa hai inter (setIntervalInterstitialAd) trong mã app.',
                'marketing_summary': 'Chưa tìm thấy cấu hình khoảng cách giữa hai quảng cáo toàn màn hình, cần dev kiểm tra.'}
    values = sorted({int(h[3].group(1)) for h in hits})
    evidence = [_evidence(h[0], h[1], h[2]) for h in hits[:5]]
    if values == [expected]:
        return {'status': 'PASS', 'expected': expected, 'actual': values, 'evidence': evidence,
                'reasoning': f'Kết luận: khoảng cách giữa hai inter là {expected} giây đúng yêu cầu.',
                'marketing_summary': f'Khoảng cách giữa hai quảng cáo toàn màn hình là {expected} giây, đúng yêu cầu.'}
    return {'status': 'FAIL', 'expected': expected, 'actual': values, 'evidence': evidence,
            'reasoning': f'Kết luận: khoảng cách giữa hai inter là {values} giây, yêu cầu {expected} giây.\n'
                         f'Cần sửa: setIntervalInterstitialAd({expected}).',
            'marketing_summary': f'Khoảng cách giữa hai quảng cáo toàn màn hình đang là {", ".join(map(str, values))} giây, '
                                 f'yêu cầu là {expected} giây.'}


def screen_class_names(rule, facts, documents, workspace):
    """The four first screens must be named as the guidance requires (checked in the manifest)."""
    screens = rule.params.get('screens', {})
    activities = (facts.get('manifest') or {}).get('activities') or []
    if not activities:
        return {'status': 'UNKNOWN', 'reason': 'missing_fact', 'reasoning': 'Không đọc được danh sách Activity trong manifest.'}
    names = {a['name'].rsplit('.', 1)[-1]: a for a in activities if isinstance(a, dict) and a.get('name')}
    missing, found = [], {}
    for label, accepted in screens.items():
        match = next((n for n in accepted if n in names), None)
        if match:
            found[label] = names[match]['name']
        else:
            missing.append(f"{label} (cần {' hoặc '.join(accepted)})")
    if missing:
        return {'status': 'FAIL', 'expected': screens, 'actual': {'found': found, 'missing': missing},
                'reasoning': 'Kết luận: tên màn hình chưa đúng quy định: ' + '; '.join(missing) + '.\n'
                             'Cần sửa: đặt tên class Activity đúng theo tài liệu hướng dẫn.',
                'marketing_summary': 'Có màn hình chưa đặt đúng tên theo quy định: ' + '; '.join(missing) + '.'}
    return {'status': 'PASS', 'expected': screens, 'actual': {'found': found},
            'reasoning': 'Kết luận: 4 màn đầu đặt tên đúng quy định.',
            'marketing_summary': '4 màn đầu (Splash, ngôn ngữ, Onboarding, Welcome) đã đặt tên đúng quy định.'}


DEMO_PUBLISHER = '3940256099942544'
# Google demo ad units by placement type (the first entry is the canonical one).
DEMO_UNITS = {
    'open': ['9257395921'], 'banner': ['6300978111', '9214589741'], 'interstitial': ['1033173712'],
    'reward': ['5224354917', '5354046379'], 'native': ['2247696110', '1044960115'],
}


def _placement_type(name):
    lowered = name.lower()
    if lowered.startswith(('open', 'app_open')):
        return 'open'
    for prefix, kind in (('banner', 'banner'), ('inter', 'interstitial'), ('reward', 'reward'), ('native', 'native')):
        if lowered.startswith(prefix):
            return kind
    return None


def _unit(ad_id):
    match = re.fullmatch(r'ca-app-pub-(\d+)/(\d+)', str(ad_id or '').strip())
    return (match.group(1), match.group(2)) if match else (None, None)


def debug_test_ids(rule, facts, documents, workspace):
    """ad_config_debug.json must use Google demo ad units; ad_config.json (release) must not."""
    debug_name = rule.params.get('debug_file', 'ad_config_debug.json')
    release_name = rule.params.get('release_file', 'ad_config.json')
    assets = facts.get('assets', {}).get('json', {})
    debug = assets.get(debug_name)
    if not isinstance(debug, dict):
        return {'status': 'UNKNOWN', 'reason': 'missing_fact',
                'reasoning': f'Không tìm thấy {debug_name} trong assets của APK.',
                'marketing_summary': 'Không tìm thấy file cấu hình quảng cáo bản debug trong app, cần dev kiểm tra.'}
    issues, evidence = [], []

    def locate(name, key):
        try:
            return _line_of(read_text(Path(workspace) / 'resources' / 'assets' / name), key)
        except (OSError, ValueError, TypeError):
            return 1, ''

    for key, value in debug.items():
        if not isinstance(value, dict) or 'id' not in value:
            continue
        publisher, unit = _unit(value.get('id'))
        kind = _placement_type(key)
        blank = not str(value.get('id') or '').strip()
        if blank and value.get('isEnable') is not True:
            continue  # unused placement with no ID is fine
        if blank:
            problem = 'Debug để trống ID dù đang bật, cần ID test của Google'
        elif publisher != DEMO_PUBLISHER:
            problem = 'Debug đang dùng ID thật, cần ID test của Google'
        elif kind and unit not in DEMO_UNITS[kind]:
            problem = 'ID test sai loại quảng cáo (cần ID test của loại ' + kind + ')'
        else:
            continue
        issues.append({'file': debug_name, 'placement': key, 'field': 'id', 'expected': 'ID test Google'
                       + (f' ({", ".join(DEMO_UNITS[kind])})' if kind else ''), 'actual': value.get('id'), 'problem': problem})
        line, excerpt = locate(debug_name, key)
        evidence.append(_evidence(f'resources/assets/{debug_name}', line, excerpt))
    release = assets.get(release_name)
    if isinstance(release, dict):
        for key, value in release.items():
            if isinstance(value, dict) and _unit(value.get('id'))[0] == DEMO_PUBLISHER:
                issues.append({'file': release_name, 'placement': key, 'field': 'id', 'expected': 'ID thật của đối tác',
                               'actual': value.get('id'), 'problem': 'Bản release đang dùng ID test'})
                line, excerpt = locate(release_name, key)
                evidence.append(_evidence(f'resources/assets/{release_name}', line, excerpt))
    expected = {'debug': 'ID test Google (ca-app-pub-3940256099942544/...)', 'release': 'ID thật, không phải ID test'}
    if not issues:
        return {'status': 'PASS', 'expected': expected, 'actual': {'files': [debug_name, release_name]},
                'reasoning': 'Kết luận: bản debug dùng toàn bộ ID test của Google đúng loại, bản release không dùng ID test.',
                'marketing_summary': 'Bản debug dùng ID quảng cáo test, không đụng tới ID thật.'}
    real = sorted({i['placement'] for i in issues if i['file'] == debug_name and i['problem'].startswith('Debug đang dùng ID thật')})
    blank = sorted({i['placement'] for i in issues if i['file'] == debug_name and 'để trống' in i['problem']})
    wrong = sorted({i['placement'] for i in issues if i['file'] == debug_name and 'sai loại' in i['problem']})
    leaked = sorted({i['placement'] for i in issues if i['file'] == release_name})
    parts = []
    if real:
        parts.append(f'{len(real)} vị trí ở bản debug dùng ID thật: ' + ', '.join(real))
    if blank:
        parts.append('bản debug để trống ID ở vị trí đang bật: ' + ', '.join(blank))
    if wrong:
        parts.append('ID test sai loại ở: ' + ', '.join(wrong))
    if leaked:
        parts.append('bản release dùng ID test ở: ' + ', '.join(leaked))
    plain = []
    if real:
        plain.append(f'Bản debug đang dùng ID quảng cáo thật ở {len(real)} vị trí, khi test có thể tạo lượt hiển thị/click ảo '
                     'và bị AdMob phạt tài khoản')
    if blank:
        plain.append(f'{len(blank)} vị trí đang bật nhưng bản debug để trống ID, sẽ không có quảng cáo test')
    if wrong:
        plain.append(f'{len(wrong)} vị trí dùng ID test nhầm loại quảng cáo')
    if leaked:
        plain.append(f'Bản release đang dùng ID test ở {len(leaked)} vị trí, sẽ không có doanh thu')
    return {'status': 'FAIL', 'expected': expected, 'actual': {'files': [debug_name, release_name], 'issues': issues},
            'evidence': evidence[:40],
            'reasoning': 'Kết luận: ' + '; '.join(parts) + '.\nCần sửa: dùng ID test Google đúng loại trong '
                         + debug_name + ' và ID thật trong ' + release_name + '.',
            'marketing_summary': '. '.join(plain) + '.'}


FIXED_ORIENTATIONS = {'portrait', 'reversePortrait', 'sensorPortrait', 'userPortrait', 'locked'}


def screen_orientation_lock(rule, facts, documents, workspace):
    """The first screens must block rotation (android:screenOrientation) so ads are not reloaded or re-laid out."""
    import xml.etree.ElementTree as ET
    screens = rule.params.get('screens', {})
    path = Path(workspace or '') / 'resources' / 'AndroidManifest.xml'
    try:
        text = read_text(path)
        root = ET.fromstring(text)
    except (OSError, ValueError, ET.ParseError):
        return {'status': 'UNKNOWN', 'reason': 'missing_fact', 'reasoning': 'Không đọc được AndroidManifest.xml đã giải mã.'}
    android = '{http://schemas.android.com/apk/res/android}'
    activities = {}
    for node in root.iter('activity'):
        name = node.get(android + 'name') or ''
        activities[name.rsplit('.', 1)[-1]] = node
    issues, evidence, found = [], [], {}
    for label, accepted in screens.items():
        match = next((n for n in accepted if n in activities), None)
        if not match:
            continue  # missing screens are reported by ADS_SCREEN_NAMES
        node = activities[match]
        orientation = node.get(android + 'screenOrientation')
        changes = node.get(android + 'configChanges') or ''
        found[label] = {'activity': match, 'screenOrientation': orientation}
        line = next((n for n, row in enumerate(text.splitlines(), 1) if f'{match}"' in row), 1)
        if orientation not in FIXED_ORIENTATIONS:
            issues.append({'file': 'AndroidManifest.xml', 'placement': label + ' (' + match + ')', 'field': 'screenOrientation',
                           'expected': 'portrait (khóa hướng màn hình)',
                           'actual': (orientation or 'không khai báo') + (' · tự xử lý xoay bằng configChanges' if 'orientation' in changes else '')})
            evidence.append(_evidence('resources/AndroidManifest.xml', line, next(
                (row.strip() for n, row in enumerate(text.splitlines(), 1) if n == line), '')))
    expected = {'screenOrientation': sorted(FIXED_ORIENTATIONS)}
    if not found:
        return {'status': 'UNKNOWN', 'reason': 'missing_fact', 'expected': expected,
                'reasoning': 'Không tìm thấy Activity của 4 màn đầu trong manifest.'}
    if not issues:
        return {'status': 'PASS', 'expected': expected, 'actual': found,
                'reasoning': 'Kết luận: cả 4 màn đầu đã khóa hướng màn hình (không xoay).',
                'marketing_summary': 'Các màn đầu đã chặn xoay màn hình, quảng cáo không bị tải lại khi xoay.'}
    names = ', '.join(i['placement'] for i in issues)
    return {'status': 'FAIL', 'expected': expected, 'actual': {'found': found, 'issues': issues}, 'evidence': evidence,
            'reasoning': f'Kết luận: chưa chặn xoay màn hình ở: {names}.\nCần sửa: thêm android:screenOrientation="portrait" cho các Activity này trong manifest.',
            'marketing_summary': f'{len(issues)} màn đầu chưa chặn xoay màn hình ({names}); khi người dùng xoay máy, màn bị dựng lại '
                                 'và quảng cáo có thể bị tải lại, hiển thị lỗi hoặc tính lượt hiển thị sai.'}


CUSTOM_CHECKS = {'screen_orientation_lock': screen_orientation_lock, 'debug_test_ids': debug_test_ids, 'ad_config_flags': ad_config_flags, 'language_dev_toggle': language_dev_toggle,
                 'remote_config_keys': remote_config_keys, 'interstitial_interval': interstitial_interval,
                 'screen_class_names': screen_class_names}
