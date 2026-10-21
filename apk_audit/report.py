from pathlib import Path
from .dev_view import dev_markdown, STATUS_LABELS
from .marketing import marketing_markdown
from .utils import write_json

def write_report(report, output, format="both"):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if format in {"json", "both"}:
        write_json(output / "report.json", report)
    if format not in {"md", "both"}:
        return
    s = report["summary"]
    lines = ["# APK audit", "", f"{STATUS_LABELS['PASS']}: {s['pass']} · {STATUS_LABELS['FAIL']}: {s['fail']} · {STATUS_LABELS['UNKNOWN']}: {s['unknown']} · {STATUS_LABELS['SKIPPED']}: {s['skipped']}", ""]
    if not s["total"]:
        lines += ["> Chưa có luật để chấm. Báo cáo này không xác nhận app đạt chuẩn ads/init.", ""]
    if report.get("marketing"):
        lines += marketing_markdown(report["marketing"])
    lines += ["## Chi tiết kỹ thuật (cho dev)", ""]
    if report.get("dev_view"):
        lines += dev_markdown(report["dev_view"])
        lines += ["## Bằng chứng chi tiết", ""]
        for finding in sorted(report["findings"], key=lambda x: (x["area"], x["rule_id"])):
            if not finding["evidence"] and not finding["expected"] and not finding["actual"]:
                continue
            lines += [f"<details><summary>{finding['rule_id']} — {finding['title']}</summary>", ""]
            if finding["expected"] is not None:
                lines.append(f"- Mong đợi: {finding['expected']}")
            if finding["actual"] is not None:
                lines.append(f"- Thực tế: {finding['actual']}")
            for e in finding["evidence"]:
                lines.append(f"- Bằng chứng: `{e['file']}:{e['line']}` — xác minh: {e['verified']}")
            lines += ["", "</details>", ""]
    else:
        for status in ("FAIL", "UNKNOWN", "SKIPPED", "PASS"):
            lines += ["### " + STATUS_LABELS[status], ""]
            group = sorted((x for x in report["findings"] if x["status"] == status), key=lambda x: (x["area"], x["rule_id"]))
            for finding in group:
                lines += [f"#### [{finding['area']}] {finding['rule_id']} — {finding['title']}", "", finding["reasoning"] or finding["reason"], ""]
                for e in finding["evidence"]:
                    lines.append(f"- Bằng chứng: `{e['file']}:{e['line']}` — xác minh: {e['verified']}")
                lines.append("")
            if not group:
                lines += ["Không có.", ""]
    lines += ["## Quan sát ngoài bộ luật", "", *[str(x) for x in report["observations"]], "", "## Thông tin chạy", "", f"- Package: {report['package']}", f"- APK SHA256: {report['apk_sha256']}", f"- Engine: {report['engine']}", f"- Rule pack: {report['rulepack']['name']} {report['rulepack']['version']}", f"- Tool calls: {s['tool_calls']}", f"- Cache hits: {s['from_cache']}", f"- Thời gian: {s['duration_seconds']:.3f}s", "", "## Cảnh báo", "", *["- " + w for w in report["warnings"]], ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
