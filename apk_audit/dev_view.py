"""Developer view: findings grouped by screen with a short, uniform summary per rule.

Same labels as the Marketing summary so both readers use one vocabulary.
"""
import re

STATUS_LABELS = {'PASS': 'Đạt', 'FAIL': 'Cần sửa', 'UNKNOWN': 'Cần dev xem lại', 'SKIPPED': 'Không áp dụng'}
STATUS_LEVELS = {'PASS': 'ok', 'FAIL': 'issue', 'UNKNOWN': 'check', 'SKIPPED': 'skip'}

GROUPS = (
    ('splash', 'Màn Splash', ('ADS_SPLASH_PLACEMENT',)),
    ('language', 'Màn chọn ngôn ngữ', ('ADS_LANGUAGE_PLACEMENT', 'ADS_LANGUAGE_DEV_TOGGLE')),
    ('onboarding', 'Màn Onboarding', ('ADS_ONBOARDING_PLACEMENT',)),
    ('welcome', 'Welcome back / App Open', ('ADS_WELCOME_RESUME',)),
    ('config', 'Cấu hình và khởi tạo', ('ADS_INIT_ORDER', 'ADS_REMOTE_FALLBACK', 'ADS_ID_SOURCE_AND_COVERAGE',
                                        'ADS_CONFIG_FLAGS', 'ADS_DEBUG_TEST_IDS', 'ADS_SCREEN_ORIENTATION', 'ADS_REMOTE_KEYS', 'ADS_INTERSTITIAL_INTERVAL',
                                        'ADS_SCREEN_NAMES')),
    ('flow', 'Load, hiển thị, event, banner', ('ADS_LOAD_OBSERVE_GATES', 'ADS_FIREBASE_EVENTS', 'ADS_BANNER_RELOAD')),
    ('cross', 'Lỗi chéo giữa các luồng', ('ADS_CROSS_FLOW_BUGS',)),
)
OTHER = ('other', 'Khác')

REASON_LABELS = {
    'unverified_evidence': 'AI dẫn chứng chưa khớp code, kết quả bị chặn để tránh kết luận sai',
    'unverified_claims': 'Nhận định của AI chưa được dẫn chứng đủ chặt',
    'engine_error': 'Lỗi khi gọi AI (CLI lỗi, hết quota hoặc quá thời gian)',
    'repair_error': 'Lỗi ở lượt AI sửa bằng chứng',
    'review_error': 'Lỗi ở lượt review kết quả FAIL',
    'review_budget': 'Hết ngân sách để review kết quả FAIL',
    'review_unknown': 'Review không xác nhận được kết quả FAIL',
    'invalid_review': 'Kết quả review không hợp lệ',
    'tool_budget': 'Hết ngân sách đọc code',
    'global_budget': 'Hết ngân sách đọc code của cả lượt audit',
    'missing_fact': 'Thiếu dữ liệu cần thiết trong APK',
    'invalid_json': 'AI trả kết quả sai định dạng',
    'engine_disabled': 'Chưa bật AI cho lượt này',
    'not_applicable_by_document': 'Tài liệu xác định không dùng phần này',
    'passed_previously': 'Đã đạt ở bản trước, bỏ qua theo cấu hình (chọn kiểm lại mọi rule để chạy lại)',
}
SECTION = re.compile(r'^(Kết luận|Cần sửa|Đã đúng|Chưa xác minh):\s*(.*)$')


def parse_sections(text):
    sections, current = {}, None
    for line in str(text or '').splitlines():
        match = SECTION.match(line.strip())
        if match:
            current = match.group(1)
            sections[current] = [match.group(2)] if match.group(2) else []
        elif current and not line.startswith('>'):
            sections[current].append(line.strip())
    return {key: ' '.join(part for part in value if part).strip() for key, value in sections.items()}


DRAFT = re.compile(r'kết luận (PASS|FAIL) từ bản nháp AI')


def _draft(text):
    """(leaning, sections) of the AI draft quoted inside a guard-downgraded UNKNOWN."""
    match = DRAFT.search(str(text or ''))
    if not match:
        return None, {}
    quoted = '\n'.join(line[1:].strip() for line in str(text).splitlines() if line.startswith('>'))
    return match.group(1), parse_sections(quoted)


def _locations(finding, limit=5):
    evidence = finding.get('evidence') or []
    wanted = []
    for claim in finding.get('claims') or []:
        if isinstance(claim, dict) and claim.get('kind') == 'violation':
            wanted += [i for i in claim.get('evidence_indices', []) if type(i) is int]
    pool = [evidence[i] for i in dict.fromkeys(wanted) if 0 <= i < len(evidence)] or evidence
    seen, locations = set(), []
    for item in pool:
        if not isinstance(item, dict) or not item.get('file'):
            continue
        key = (item['file'], item.get('line'))
        if key not in seen:
            seen.add(key)
            locations.append(f"{item['file']}:{item.get('line')}")
    return locations[:limit]


def _short(text, limit=320):
    text = ' '.join(str(text or '').split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + '…'


def rule_view(finding, id_problem_count=0):
    status = finding.get('status', 'UNKNOWN')
    sections = parse_sections(finding.get('reasoning'))
    reason = finding.get('reason') or ''
    conclusion = sections.get('Kết luận') or _short(finding.get('reasoning') or reason)
    fixes = sections.get('Cần sửa', '')
    leaning, draft = _draft(finding.get('reasoning')) if status == 'UNKNOWN' else (None, {})
    if leaning:
        word = 'đạt' if leaning == 'PASS' else 'có lỗi'
        conclusion = f"AI nghiêng về kết luận {word} nhưng dẫn chứng chưa đủ chặt để chấp nhận. " + (draft.get('Kết luận') or '')
        fixes = draft.get('Cần sửa', '')
        sections = {**sections, 'Đã đúng': draft.get('Đã đúng', ''), 'Chưa xác minh': draft.get('Chưa xác minh', '')}
    if status == 'PASS' or fixes.lower().startswith(('không xác định', 'không có', 'chưa xác định')):
        fixes = ''
    if finding.get('rule_id') == 'ADS_ID_SOURCE_AND_COVERAGE' and id_problem_count and status == 'FAIL':
        fixes = f'{id_problem_count} ID sai/thiếu, danh sách đầy đủ ở tab Marketing.'
    view = {
        'rule_id': finding.get('rule_id'), 'title': finding.get('title'), 'status': status,
        'status_label': STATUS_LABELS.get(status, status), 'level': STATUS_LEVELS.get(status, 'check'),
        'conclusion': _short(conclusion), 'fixes': _short(fixes, 500),
        'locations': _locations(finding) if status in {'FAIL', 'UNKNOWN'} else [],
        'verified': _short(sections.get('Đã đúng', ''), 400) if status != 'PASS' else '',
        'unverified': _short(sections.get('Chưa xác minh', ''), 400),
        'tool_calls': finding.get('tool_calls', 0), 'mode': finding.get('mode'),
    }
    if status == 'UNKNOWN':
        view['unknown_reason'] = REASON_LABELS.get(reason, 'Chưa đủ căn cứ trong mã để kết luận' if not reason else reason)
        if 'usage limit' in str(finding.get('reasoning')):
            view['unknown_reason'] = 'AI hết hạn mức sử dụng giữa chừng, chạy lại sau khi hạn mức được làm mới'
    if status == 'SKIPPED':
        view['unknown_reason'] = REASON_LABELS.get(reason, 'Không áp dụng cho app này')
    return view


def build_dev_view(findings, marketing=None):
    problems = len((marketing or {}).get('id_problems', []))
    by_id = {f['rule_id']: f for f in findings}
    used, groups = set(), []
    for key, title, rule_ids in GROUPS:
        rules = [rule_view(by_id[r], problems) for r in rule_ids if r in by_id]
        used.update(rule_ids)
        if rules:
            groups.append({'key': key, 'title': title, 'rules': rules})
    rest = [rule_view(f, problems) for f in findings if f['rule_id'] not in used]
    if rest:
        groups.append({'key': OTHER[0], 'title': OTHER[1], 'rules': rest})
    for group in groups:
        counts = {s: sum(r['status'] == s for r in group['rules']) for s in STATUS_LABELS}
        group['summary'] = counts
        group['level'] = ('issue' if counts['FAIL'] else 'check' if counts['UNKNOWN']
                          else 'ok' if counts['PASS'] else 'skip')
    return {'groups': groups}


def dev_markdown(view):
    lines = []
    for group in view['groups']:
        lines += [f"### {group['title']}", '']
        for rule in group['rules']:
            lines += [f"#### [{rule['status_label']}] {rule['title']} (`{rule['rule_id']}`)", '']
            if rule['conclusion']:
                lines += [rule['conclusion'], '']
            if rule.get('unknown_reason') and rule['status'] != 'PASS':
                lines += [f"- Lý do: {rule['unknown_reason']}"]
            if rule['fixes']:
                lines += [f"- Cần sửa: {rule['fixes']}"]
            if rule['locations']:
                lines += ['- Vị trí code: ' + ', '.join(f'`{loc}`' for loc in rule['locations'])]
            if rule['unverified']:
                lines += [f"- Chưa xác minh: {rule['unverified']}"]
            lines.append('')
    return lines
