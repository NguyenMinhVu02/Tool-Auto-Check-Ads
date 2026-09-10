from pathlib import Path
from .utils import write_json

def write_report(report, output, format="both"):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if format in {"json", "both"}:
        write_json(output / "report.json", report)
    if format not in {"md", "both"}:
        return
    s = report["summary"]
    lines = ["# APK audit", "", f"Đạt: {s['pass']} · Sai: {s['fail']} · Chưa rõ: {s['unknown']} · Bỏ qua: {s['skipped']}", ""]
    if not s["total"]:
        lines += ["> Chưa có luật để chấm. Báo cáo này không xác nhận app đạt chuẩn ads/init.", ""]
    for status, label in [("FAIL","Sai"),("UNKNOWN","Chưa rõ"),("SKIPPED","Bỏ qua"),("PASS","Đạt")]:
        lines += ["## " + label, ""]
        group = sorted((x for x in report["findings"] if x["status"] == status), key=lambda x:(x["area"],x["rule_id"]))
        for finding in group:
            lines += [f"### [{finding['area']}] {finding['rule_id']} — {finding['title']}", "", finding["reasoning"] or finding["reason"], "", f"- Mong đợi: {finding['expected']}", f"- Thực tế: {finding['actual']}"]
            for e in finding["evidence"]:
                lines.append(f"- Bằng chứng: `{e['file']}:{e['line']}` — xác minh: {e['verified']}")
            if finding["hint"]:
                lines.append("- Xem tiếp: " + finding["hint"])
            lines.append("")
        if not group:
            lines += ["Không có.", ""]
    lines += ["## Quan sát ngoài bộ luật", "", *[str(x) for x in report["observations"]], "", "## Thông tin chạy", "", f"- Package: {report['package']}", f"- APK SHA256: {report['apk_sha256']}", f"- Engine: {report['engine']}", f"- Rule pack: {report['rulepack']['name']} {report['rulepack']['version']}", f"- Tool calls: {s['tool_calls']}", f"- Cache hits: {s['from_cache']}", f"- Thời gian: {s['duration_seconds']:.3f}s", "", "## Cảnh báo", "", *["- " + w for w in report["warnings"]], ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
