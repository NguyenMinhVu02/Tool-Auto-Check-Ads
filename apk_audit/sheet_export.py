"""Shape an audit report into KOG APK Tester's report format and reuse its Google Sheet exporter.

No new judgement here: rows come from the Dev view groups (one per rule) and the Marketing
ID table that the report already contains.
"""

from .kog_sheet_exporter import SheetExporter

STATUS = {"PASS": "PASS", "FAIL": "FAIL"}  # KOG: PASS -> Pass, FAIL -> Fail, anything else -> Pending


def to_kog_report(report):
    checklist = {}
    for group in (report.get("dev_view") or {}).get("groups", []):
        items = []
        for rule in group.get("rules", []):
            notes = []
            if rule.get("fixes"):
                notes.append("Cần sửa: " + rule["fixes"])
            if rule.get("locations"):
                notes.append("Vị trí: " + ", ".join(rule["locations"]))
            if rule.get("status") == "UNKNOWN" and rule.get("unverified"):
                notes.append("Chưa xác minh: " + rule["unverified"])
            items.append({
                "id": rule.get("rule_id", ""), "function": group.get("title", ""), "title": rule.get("title", ""),
                "actual": rule.get("conclusion", ""), "expected": "Đạt yêu cầu: " + rule.get("title", ""),
                "status": STATUS.get(rule.get("status"), "MANUAL_CHECK"), "notes": notes,
            })
        if items:
            checklist[group.get("key", group.get("title"))] = {"title": group.get("title", ""), "items": items}
    id_items = []
    for screen in (report.get("marketing") or {}).get("screens", []):
        for placement in screen.get("placements", []):
            if not placement.get("problem"):
                continue
            id_items.append({
                "id": placement.get("name", ""), "function": screen.get("title", ""),
                "title": f"ID quảng cáo {placement.get('name', '')} ({placement.get('ad_type', '')})",
                "actual": f"{placement.get('status', '')}. ID trong app: {placement.get('app_id') or 'không có'}",
                "expected": f"ID theo ADS SCRIPTS: {placement.get('document_id') or 'không có'}",
                "status": "FAIL", "notes": [],
            })
    if id_items:
        checklist["ads_ids"] = {"title": "ID quảng cáo so với ADS SCRIPTS", "items": id_items}
    summary = report.get("summary") or {}
    total = summary.get("total") or 0
    return {
        "apk_info": {"app_name": report.get("package", ""), "package_name": report.get("package", ""),
                     "version_name": report.get("version_name", ""), "version_code": "-", "file_size_mb": "-"},
        "summary": {"pass": summary.get("pass", 0), "total": total,
                    "compliance_score": round(100 * summary.get("pass", 0) / total, 1) if total else 0},
        "checklist": checklist,
    }


def sheet_tsv(report, only_fails=False, prefix=None):
    package = report.get("package") or "APP"
    return SheetExporter.to_tsv(to_kog_report(report), app_prefix=prefix or package.rsplit(".", 1)[-1].upper(),
                                only_fails=only_fails)


def partner_summary(report, partner_name="Đối tác"):
    return SheetExporter.to_summary_markdown(to_kog_report(report), partner_name=partner_name)
