"""Single-file HTML report (inline CSS, no scripts) for people who do not run the tool."""
import csv
import io
from html import escape

CSS = """
:root{--bg:#f5f7fb;--card:#fff;--text:#1d2939;--muted:#667085;--line:#dbe4f0;--ok:#12a26b;--issue:#d92d20;--check:#dc8a05;--skip:#98a2b3}
@media (prefers-color-scheme:dark){:root{--bg:#10151f;--card:#18202c;--text:#e6ebf2;--muted:#9aa6b8;--line:#2a3547}}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 system-ui,sans-serif}
main{max-width:1100px;margin:auto;padding:24px 16px}
h1{font-size:22px}h2{font-size:18px;margin-top:28px}h3{font-size:15px;margin:0 0 6px}
.card{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--skip);border-radius:10px;padding:12px 14px;margin:10px 0}
.card.ok{border-left-color:var(--ok)}.card.issue{border-left-color:var(--issue)}.card.check{border-left-color:var(--check)}
.tag{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;border:1px solid var(--line);margin-right:4px}
.tag.ok{color:var(--ok)}.tag.issue{color:var(--issue)}.tag.check{color:var(--check)}
table{border-collapse:collapse;width:100%;font-size:12.5px;margin-top:6px}th,td{border-bottom:1px solid var(--line);padding:4px 6px;text-align:left;vertical-align:top}
td.id{font-family:ui-monospace,monospace;font-size:11.5px;word-break:break-all}tr.bad td{background:rgba(217,45,32,.08)}
.muted{color:var(--muted)}code{font-family:ui-monospace,monospace;font-size:12px}
"""


def _tag(level, text):
    return f'<span class="tag {escape(level)}">{escape(str(text))}</span>'


def _marketing(m):
    out = ['<h2>Tóm tắt cho Marketing</h2>']
    for note in (m.get('publisher_note'),):
        if note:
            out.append(f'<div class="card issue"><b>ID ads thuộc tài khoản AdMob khác.</b> {escape(note)}</div>')
    if m.get('app_id_match') is False:
        out.append('<div class="card issue">AdMob App ID trong app không khớp ADS SCRIPTS.</div>')
    problems = m.get('id_problems', [])
    if problems:
        rows = ''.join(f"<li><b>{escape(p['name'])}</b> ({escape(p['screen'])}) — {escape(p['status'])}</li>" for p in problems)
        out.append(f'<div class="card issue"><h3>{len(problems)} ID ads đang có vấn đề</h3><ul>{rows}</ul></div>')
    elif m.get('documents_available'):
        out.append('<div class="card ok">Không thấy ID ads nào sai hoặc thiếu ở các màn đầu.</div>')
    for check in m.get('config_checks', []):
        rows = ''.join(f"<tr><td>{escape(i['file'])}</td><td><code>{escape(i['placement'])}</code></td><td>{escape(i['field'])}</td>"
                       f"<td>{escape(str(i['expected']))}</td><td>{escape(str(i['actual']))}</td></tr>" for i in check['issues'])
        table = ('<table><tr><th>File</th><th>Vị trí</th><th>Trường</th><th>Cần là</th><th>Đang là</th></tr>' + rows + '</table>') if rows else ''
        out.append(f"<div class=\"card {escape(check['level'])}\"><h3>{escape(check['title'])} {_tag(check['level'], check['label'])}</h3>"
                   f"<div>{escape(check['explanation'])}</div>{table}</div>")
    for screen in m.get('screens', []):
        rows = ''.join(
            f"<tr class=\"{'bad' if p['problem'] else ''}\"><td><code>{escape(p['name'])}</code></td><td>{escape(p['ad_type'])}</td>"
            f"<td>{escape(p['status'])}</td><td class=\"id\">{escape(p['document_id'] or '—')}</td><td class=\"id\">{escape(p['app_id'] or '—')}</td></tr>"
            for p in screen['placements'])
        table = ('<table><tr><th>Vị trí</th><th>Loại</th><th>Tình trạng</th><th>ID trong ADS SCRIPTS</th><th>ID trong app</th></tr>' + rows + '</table>') if rows else ''
        logic = screen.get('logic') or {}
        logic_html = ''
        if logic.get('load') or logic.get('show'):
            tag = '' if logic.get('verified') else ' <span class="muted">(chưa xác minh đủ)</span>'
            logic_html = (f"<p><b>Logic hiện tại</b>{tag}<br>Tải quảng cáo: {escape(logic.get('load') or '—')}"
                          f"<br>Hiển thị: {escape(logic.get('show') or '—')}</p>")
        icons = {'ok': '✅', 'issue': '❌', 'unknown': '❔', 'na': '➖'}
        checks = ''.join(f"<li>{icons.get(r['status'], '❔')} {escape(r['text'])}"
                         + (f" <span class=\"muted\">— {escape(r['note'])}</span>" if r['note'] else '') + '</li>'
                         for r in screen.get('requirements', []))
        checks_html = f'<p><b>Đã đúng yêu cầu chưa?</b></p><ul>{checks}</ul>' if checks else ''
        out.append(f"<div class=\"card {escape(screen['level'])}\"><h3>{escape(screen['title'])}</h3>"
                   f"{_tag('issue' if screen['id_issues'] else 'ok', str(screen['id_issues']) + ' ID có vấn đề' if screen['id_issues'] else 'ID đúng')}"
                   f"{_tag(screen['flow_level'], 'Luồng quảng cáo: ' + screen['flow_label'])}"
                   f"<p>{escape(screen['explanation'])}</p>{logic_html}{checks_html}{table}</div>")
    return out


def _dev(view, findings):
    by_id = {f['rule_id']: f for f in findings}
    out = ['<h2>Chi tiết kỹ thuật (cho dev)</h2>']
    for group in view['groups']:
        out.append(f"<h3>{escape(group['title'])}</h3>")
        for rule in group['rules']:
            conf = f" {_tag('muted', 'Độ tin cậy: ' + rule['confidence'])}" if rule.get('confidence') else ''
            parts = [f"<h3>{escape(rule['title'] or rule['rule_id'])} {_tag(rule['level'], rule['status_label'])}{conf}</h3>",
                     f"<div>{escape(rule['conclusion'])}</div>"]
            if rule.get('unknown_reason') and rule['status'] != 'PASS':
                parts.append(f"<div class=\"muted\">Lý do: {escape(rule['unknown_reason'])}</div>")
            if rule['fixes']:
                parts.append(f"<div><b>Cần sửa:</b> {escape(rule['fixes'])}</div>")
            if rule['locations']:
                parts.append('<div><b>Vị trí code:</b> ' + ', '.join(f'<code>{escape(loc)}</code>' for loc in rule['locations']) + '</div>')
            evidence = by_id.get(rule['rule_id'], {}).get('evidence') or []
            if evidence:
                items = ''.join(f"<li><code>{escape(str(e['file']))}:{e['line']}</code></li>" for e in evidence)
                parts.append(f'<details><summary>Bằng chứng ({len(evidence)})</summary><ul>{items}</ul></details>')
            out.append(f"<div class=\"card {escape(rule['level'])}\">{''.join(parts)}</div>")
    return out


def render_html(report):
    s = report['summary']
    head = (f"<h1>APK audit — {escape(str(report.get('package') or ''))}</h1>"
            f"<p class=\"muted\">Đạt {s['pass']} · Cần sửa {s['fail']} · Cần dev xem lại {s['unknown']} · "
            f"Không áp dụng {s['skipped']} · Engine {escape(str(report.get('engine')))}</p>")
    body = (_marketing(report['marketing']) if report.get('marketing') else []) + \
           (_dev(report['dev_view'], report['findings']) if report.get('dev_view') else [])
    return ('<!doctype html><html lang="vi"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><title>APK audit report</title>'
            f'<style>{CSS}</style></head><body><main>{head}{"".join(body)}</main></body></html>')


def ids_csv(marketing):
    """Wrong/missing ADS IDs for pasting into a sheet or chat."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Màn', 'Vị trí', 'Loại', 'Tình trạng', 'ID trong ADS SCRIPTS', 'ID trong app'])
    for screen in (marketing or {}).get('screens', []):
        for p in screen['placements']:
            if p['problem']:
                writer.writerow([screen['title'], p['name'], p['ad_type'], p['status'], p['document_id'], p['app_id']])
    return '﻿' + buffer.getvalue()  # BOM so Excel reads Vietnamese correctly
