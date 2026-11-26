"""Plain-language summary of the first screens for Marketing readers.

Deterministic: placement/ID rows come from ADS SCRIPTS vs the app's local ad_config.json,
screen verdicts from the matching rule. AI text is only shown as the rule's own summary.
"""
import re

from .dev_view import STATUS_LABELS, STATUS_LEVELS
from .placement_policy import config_key
from .documents import normalize_ads_document

SCREENS = (
    ('splash', 'Màn Splash (mở app)', 'ADS_SPLASH_PLACEMENT', ('splash',)),
    ('language', 'Màn chọn ngôn ngữ', 'ADS_LANGUAGE_PLACEMENT', ('language',)),
    ('onboarding', 'Màn giới thiệu (Onboarding)', 'ADS_ONBOARDING_PLACEMENT', ('onboarding',)),
    ('welcome', 'Quay lại app (Welcome back / App Open)', 'ADS_WELCOME_RESUME', ('welcome', 'resume')),
)
AD_TYPES = {'interstitial': 'Toàn màn hình (Inter)', 'inter': 'Toàn màn hình (Inter)', 'banner': 'Banner',
            'native': 'Native', 'app_open': 'App Open', 'open': 'App Open', 'reward': 'Reward'}
CONFIG_CHECKS = (
    ('ADS_CONFIG_FLAGS', 'Cờ bật quảng cáo (isEnable) và kiểm tra UA trong ad_config'),
    ('ADS_LANGUAGE_DEV_TOGGLE', 'Dev setting ở màn Language (Unlimited ads để test)'),
    ('ADS_DEBUG_TEST_IDS', 'ID quảng cáo test ở bản debug'),
    ('ADS_REMOTE_KEYS', 'Cấu hình điều khiển từ xa (Remote Config) và consent'),
    ('ADS_INTERSTITIAL_INTERVAL', 'Khoảng cách giữa hai quảng cáo toàn màn hình'),
    ('ADS_SCREEN_NAMES', 'Tên 4 màn đầu theo quy định'),
    ('ADS_SCREEN_ORIENTATION', 'Chặn xoay màn hình ở 4 màn đầu'),
    ('ADS_MEDIATION_ADAPTERS', 'Mạng mediation đủ adapter và SDK'),
    ('ADS_SPLASH_ADS_NOTICE', 'Chữ "This action may contain ads" ở Splash'),
    ('ADS_LANGUAGE_DONE_DELAY', 'Thời gian chờ nút Done ở màn ngôn ngữ (tham khảo)'),
    ('ADS_UNINSTALL_SETUP', 'Shortcut Uninstall, màn xác nhận gỡ và màn khảo sát'),
)
REQUIREMENT_ICONS = {'ok': '✅', 'issue': '❌', 'unknown': '❔', 'na': '➖'}
VERDICTS = {status: (STATUS_LEVELS[status], label) for status, label in STATUS_LABELS.items()}


def _ad_type(row, name):
    value = str(row.get('ad_type') or '').lower()
    for key, label in AD_TYPES.items():
        if key in value or name.startswith(key):
            return label
    return row.get('ad_type') or ''


def _placement(name, row, local, optional):
    doc_id = (row or {}).get('id') or ''
    app_id = (local or {}).get('id') or ''
    state = (row or {}).get('state')
    if row is None:
        status, problem = 'Có trong app, không có trong ADS SCRIPTS', False
    elif state == 'disabled':
        status, problem = 'Không dùng (tài liệu đánh dấu tắt)', False
    elif state == 'unknown':
        status, problem = 'Tài liệu chưa rõ có dùng không', False
    elif not doc_id:
        status, problem = 'Tài liệu chưa có ID', False
    elif local is None:
        status, problem = ('Không bắt buộc, app chưa khai báo', False) if name in optional else ('Thiếu: app chưa khai báo vị trí này', True)
    elif app_id == doc_id:
        status, problem = 'Đúng ID', False
    elif not app_id:
        status, problem = 'Sai: app để trống ID', True
    else:
        status, problem = 'Sai ID: app khác ADS SCRIPTS', True
    return {'name': name, 'ad_type': _ad_type(row or local or {}, name), 'document_id': doc_id,
            'app_id': app_id, 'status': status, 'problem': problem}


def _publisher(ad_id):
    match = re.match(r'ca-app-pub-(\d+)', str(ad_id or ''))
    return match.group(1) if match else None


def _publisher_note(documented, local):
    expected = {_publisher(row.get('id')) for row in documented.values() if row.get('state') == 'active'} - {None}
    actual = {_publisher(value.get('id')) for value in local.values()} - {None}
    if expected and actual and not expected & actual:
        return ('Toàn bộ ID trong app thuộc tài khoản AdMob khác (pub-' + ', pub-'.join(sorted(actual))
                + ') so với ADS SCRIPTS (pub-' + ', pub-'.join(sorted(expected))
                + '). Có thể app chưa được thay ID của đối tác, hoặc đây là bản build dùng ID test/nội bộ.')
    return None


def build_marketing_summary(documents, facts, inventory, findings):
    ads = normalize_ads_document((documents or {}).get('ads_scripts', {}))
    rows = ads.get('placements') if isinstance(ads, dict) else None
    documented = {row['name']: row for row in rows or [] if isinstance(row, dict) and row.get('name')}
    config = facts.get('assets', {}).get('json', {}).get('ad_config.json', {})
    local = {key: value for key, value in (config if isinstance(config, dict) else {}).items()
             if isinstance(value, dict) and 'id' in value}
    optional = set(inventory.get('optional_placements', []))
    by_rule = {f['rule_id']: f for f in findings}
    screens, problems = [], []
    for key, title, rule_id, fragments in SCREENS:
        claimed = {config_key(name, local, row.get('id'), documented.keys()) for name, row in documented.items()} - {None}
        names = sorted(name for name in documented.keys() | (local.keys() - claimed)
                       if any(fragment in name.lower() for fragment in fragments))
        placements = []
        for name in names:
            key = config_key(name, local, (documented.get(name) or {}).get('id'), documented.keys())
            item = _placement(name, documented.get(name), local.get(key) if key else None, optional)
            if key and key != name:
                item['app_name'] = key
                item['status'] += f' (app đặt tên {key})'
            elif not key and item['status'].startswith('Thiếu') and name in documented:
                # Same family under another index (e.g. fullscreen_1_2 vs 1_3) is a naming difference to confirm, not proof of absence.
                family = re.sub(r'(?:_\d+)+$', '', name)
                similar = sorted(k for k in local.keys() - claimed if family and k.startswith(family + '_'))
                if similar:
                    item['candidates'] = similar
                    item['status'] = ('Chưa khớp tên: tài liệu ghi ' + name + ', app có ' + ', '.join(similar)
                                      + ' (cần xác nhận có phải cùng vị trí)')
            placements.append(item)
        finding = by_rule.get(rule_id)
        flow_level, flow_label = VERDICTS.get(finding['status'], VERDICTS['UNKNOWN']) if finding else ('check', 'Chưa kiểm')
        if finding and finding['status'] == 'FAIL' and (finding.get('verification') or {}).get('confidence') == 'trung bình':
            flow_label += ' (nên dev xác nhận)'
        id_issues = sum(item['problem'] for item in placements)
        # One headline per screen: wrong IDs lose revenue even when the ad flow logic is fine.
        level = 'issue' if flow_level == 'issue' or id_issues else flow_level
        label = (f'{id_issues} ID ads có vấn đề' if id_issues else 'ID ads đúng') + ' · Luồng quảng cáo: ' + flow_label
        explanation = (finding or {}).get('marketing_summary') or ''
        if finding and finding['status'] == 'UNKNOWN' and 'usage limit' in str(finding.get('reasoning')):
            explanation = 'Chưa kiểm được màn này vì AI hết hạn mức sử dụng giữa chừng. Chạy lại sau khi hạn mức làm mới (các rule đã xong được dùng lại).'
        elif finding and finding['status'] == 'UNKNOWN' and finding.get('reason') in {'engine_error', 'repair_error', 'review_error'}:
            explanation = 'Chưa kiểm được màn này vì lỗi khi gọi AI. Chạy lại để kiểm.'
        elif finding and finding['status'] == 'UNKNOWN' and key == 'welcome' and 'open_resume' in inventory.get('uncertain_placements', []):
            explanation = ('Tài liệu không cho biết vị trí open_resume có đang dùng hay không (thường do file CSV mất màu/gạch ngang). '
                           'Chọn lại ADS SCRIPTS dạng XLSX để tool kết luận được màn này.')
        elif finding and finding['status'] == 'UNKNOWN':
            explanation = ('Tool chưa đủ căn cứ để kết luận, cần dev xem lại.'
                           + (' Ghi chú của AI: ' + explanation if explanation else ''))
        report = (finding or {}).get('screen_report') or {}
        screens.append({'key': key, 'title': title, 'rule_id': rule_id, 'level': level, 'label': label,
                        'logic': ({'load': report.get('load', ''), 'show': report.get('show', ''),
                                   'verified': bool(report.get('verified'))} if report else None),
                        'requirements': report.get('requirements', []),
                        'flow_level': flow_level, 'flow_label': flow_label, 'id_issues': id_issues,
                        'explanation': explanation, 'placements': placements})
        problems += [{'screen': title, **item} for item in placements if item['problem']]
    checks = []
    for rule_id, title in CONFIG_CHECKS:
        finding = by_rule.get(rule_id)
        if not finding:
            continue
        check_level, check_label = VERDICTS.get(finding['status'], VERDICTS['UNKNOWN'])
        issues = (finding.get('actual') or {}).get('issues', []) if isinstance(finding.get('actual'), dict) else []
        checks.append({'rule_id': rule_id, 'title': title, 'level': check_level, 'label': check_label,
                       'explanation': finding.get('marketing_summary') or '',
                       'issues': [{'file': i['file'], 'placement': i['placement'], 'field': i['field'],
                                   'expected': i['expected'], 'actual': i['actual']} for i in issues]})
    return {
        'config_checks': checks,
        'documents_available': bool(documented),
        'publisher_note': _publisher_note(documented, local),
        'id_source': 'ad_config.json trong APK (cấu hình local, bản release)',
        'app_id_match': inventory.get('app_id_match'),
        'package_match': inventory.get('package_match'),
        'id_problems': problems,
        'screens': screens,
    }


def marketing_markdown(summary):
    lines = ['## Tóm tắt cho Tester (các màn đầu)', '']
    if not summary['documents_available']:
        lines += ['> Chưa có ADS SCRIPTS nên chưa đối chiếu được ID.', '']
    if summary.get('publisher_note'):
        lines += ['- ⚠️ ' + summary['publisher_note']]
    if summary['app_id_match'] is False:
        lines += ['- ⚠️ AdMob App ID trong app **không khớp** ADS SCRIPTS.']
    if summary['package_match'] is False:
        lines += ['- ⚠️ Package của app **không khớp** working file.']
    if summary['id_problems']:
        lines += [f"**{len(summary['id_problems'])} ID ads đang có vấn đề:**", '']
        lines += [f"- {p['screen']}: `{p['name']}` — {p['status']}" for p in summary['id_problems']]
    elif summary['documents_available']:
        lines += ['Không thấy ID ads nào sai/thiếu ở các màn đầu.']
    lines += ['', f"_Nguồn ID trong app: {summary['id_source']}._", '']
    for check in summary.get('config_checks', []):
        lines += [f"### {check['title']} — {check['label']}", '']
        if check['explanation']:
            lines += [check['explanation'], '']
        if check['issues']:
            lines += ['| File | Vị trí | Trường | Cần là | Đang là |', '|---|---|---|---|---|']
            lines += [f"| {i['file']} | {i['placement']} | {i['field']} | {i['expected']} | {i['actual']} |" for i in check['issues']]
            lines.append('')
    for screen in summary['screens']:
        lines += [f"### {screen['title']} — {screen['label']}", '']
        if screen['explanation']:
            lines += [screen['explanation'], '']
        logic = screen.get('logic')
        if logic and (logic['load'] or logic['show']):
            note = '' if logic['verified'] else ' _(chưa xác minh đủ)_'
            lines += [f"**Logic hiện tại{note}**", '', f"- Tải quảng cáo: {logic['load'] or '—'}",
                      f"- Hiển thị: {logic['show'] or '—'}", '']
        if screen.get('requirements'):
            lines += ['**Đã đúng yêu cầu chưa?**', '']
            lines += [f"- {REQUIREMENT_ICONS.get(r['status'], '❔')} {r['text']}" + (f" — {r['note']}" if r['note'] else '')
                      for r in screen['requirements']]
            lines.append('')
        if screen['placements']:
            lines += ['| Vị trí | Loại | ID trong ADS SCRIPTS | ID trong app | Tình trạng |', '|---|---|---|---|---|']
            lines += [f"| {p['name']} | {p['ad_type']} | {p['document_id'] or '—'} | {p['app_id'] or '—'} | "
                      f"{'❌ ' if p['problem'] else ''}{p['status']} |" for p in screen['placements']]
            lines.append('')
    return lines
