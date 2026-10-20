"""Partner placement applicability, independent of APK enable flags."""

import unicodedata


def label(value):
    text = unicodedata.normalize('NFKD', str(value)).replace('đ', 'd').replace('Đ', 'D')
    return ' '.join(''.join(c for c in text if not unicodedata.combining(c)).casefold().split())


def flag(value):
    if isinstance(value, bool):
        return value
    text = label(value)
    if text in {'true', '1', 'yes', 'on', 'enabled', 'active', 'bat', 'co', 'su dung'}:
        return True
    if text in {'false', '0', 'no', 'off', 'disabled', 'inactive', 'tat', 'khong', 'khong dung', 'khong su dung', 'bo qua'}:
        return False
    return None


def normalize_ads_document(document, *, csv_format=False):
    if not isinstance(document, dict) or not isinstance(document.get('placements'), list):
        return document
    result = dict(document)
    result['formatting_available'] = document.get('formatting_available', not csv_format)
    rows = []
    for row in document['placements']:
        if not isinstance(row, dict):
            continue
        row = dict(row)
        open_resume = label(row.get('name', '')) == 'open_resume'
        switches = [flag(row[k]) for k in ('enabled', 'isEnable', 'status') if k in row]
        state = label(row.get('state', ''))
        if open_resume and not str(row.get('id') or '').strip():
            row.update(state='disabled', state_reason='empty_id')
        elif flag(row.get('strikethrough')) is True:
            row.update(state='disabled', state_reason='strikethrough')
        elif flag(row.get('highlighted')) is True:
            row.update(state='disabled', state_reason='highlighted')
        elif False in switches or state == 'disabled':
            row.update(state='disabled', state_reason=row.get('state_reason') or 'explicit_disabled')
        elif row.get('formula_id') or row.get('formatting_uncertain'):
            row.update(state='unknown', state_reason='formula_or_conditional_formatting')
        elif True in switches or state == 'active':
            row.update(state='active', state_reason='explicit_active')
        elif state == 'unknown' or (open_resume and not result['formatting_available']):
            row.update(state='unknown', state_reason=row.get('state_reason') or ('formatting_not_available' if not state else 'unspecified'))
        else:
            row.update(state='active', state_reason='document_id')
        rows.append(row)
    result['placements'] = rows
    if any(row.get('formula_id') or row.get('formatting_uncertain') for row in rows):
        result['warnings'] = list(document.get('warnings', [])) + [
            'Có ID công thức hoặc vùng conditional formatting; tool không thực thi công thức '
            'hay suy đoán màu hiển thị. Cần giá trị/định dạng tĩnh để kết luận trạng thái.'
        ]
    if csv_format:
        result['warnings'] = list(document.get('warnings', [])) + [
            'CSV không giữ màu hoặc gạch ngang. Với open_resume có ID, cần cột Status/Enabled '
            'để xác định đang dùng; nếu thiếu thì không bắt buộc bật App Open.'
        ]
    return result


def integration_policy(ads):
    rows = ads.get('placements') if isinstance(ads, dict) else None
    supplied = isinstance(rows, list)
    resume = next((row for row in rows or [] if label(row.get('name', '')) == 'open_resume'), None)
    state = resume['state'] if resume else 'not_required' if supplied else 'unknown'
    return {
        'inter_onboarding': {'required': False, 'reason': 'optional_at_onboarding_exit'},
        'open_resume': {'state': state, 'required': state == 'active',
                        'reason': resume['state_reason'] if resume else 'absent_from_ads_scripts' if supplied else 'missing_ads_scripts'},
    }
