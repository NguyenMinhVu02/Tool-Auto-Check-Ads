# Copied from KOG APK Tester (sheet_exporter.py, KOG-KH/KOG-APK-Tester) with the team's permission.
# Only change: cells are quoted with embedded double quotes doubled, so pasting into Google Sheets
# does not split a cell that contains `"` (see _cell). Feed it through apk_audit.sheet_export.
"""
sheet_exporter.py - Xuất dữ liệu kiểm thử theo định dạng Google Sheet chuẩn của đối tác
Cung cấp định dạng TSV (Tab-Separated Values) để Tester chỉ cần bấm "Copy" và "Ctrl + V" vào Google Sheet.
Cột chuẩn: [ID, Function, Test Scenario Group, Actual, Test Condition, Steps to Reproduce, Expected, Round 1, Round 2, Link Bug]
"""

from typing import Dict, List, Any

def _cell(text) -> str:
    text = str(text or "")
    if "\n" in text or "\t" in text or '"' in text:
        return '"' + text.replace('"', '""') + '"'
    return text


class SheetExporter:
    @staticmethod
    def to_tsv(report: Dict[str, Any], app_prefix: str = "APP", only_fails: bool = False) -> str:
        """
        Sinh chuỗi định dạng TSV (Tab-Separated Values)
        Tester copy chuỗi này rồi paste (Ctrl + V) thẳng vào Google Sheet là tự chia đều các cột!
        """
        lines = []
        # Header (Có thể bỏ nếu paste nối vào sheet có sẵn, nhưng có kèm để tham khảo)
        header = ["ID", "Function", "Test Scenario Group", "Actual", "Test Condition", "Steps to Reproduce", "Expected", "Round 1", "Round 2", "Link Bug"]
        lines.append("\t".join(header))

        checklist = report.get("checklist", {})
        idx = 1

        for phase_key, phase_data in checklist.items():
            for item in phase_data.get("items", []):
                status = item.get("status", "MANUAL_CHECK")
                
                # Nếu chỉ muốn xuất các lỗi cần đối tác fix (Fail hoặc Cần verify)
                if only_fails and status == "PASS":
                    continue

                row_id = f"{app_prefix}_{idx}"
                func = item.get("function", "")
                title = item.get("title", "")
                actual = item.get("actual", "")
                
                # Ghi chú note thêm nếu có
                notes = item.get("notes", [])
                if notes:
                    actual = actual + ("\n- " + "\n- ".join(notes) if actual else "\n- ".join(notes))
                
                # Thay thế ký tự ngắt dòng trong ô để không bị vỡ dòng khi paste vào Google Sheet
                actual_cell = _cell(actual)
                expected = item.get("expected", "")
                expected_cell = _cell(expected)
                
                # Trạng thái Round 1: Pass / Fail / Pending
                round_1 = "Pass" if status == "PASS" else ("Fail" if status == "FAIL" else "Pending")

                row = [
                    row_id,
                    func,
                    _cell(title),
                    actual_cell,
                    "", # Test Condition
                    "", # Steps to Reproduce
                    expected_cell,
                    round_1,
                    "", # Round 2
                    ""  # Link Bug
                ]
                lines.append("\t".join(row))
                idx += 1

        return "\n".join(lines)

    @staticmethod
    def to_summary_markdown(report: Dict[str, Any], partner_name: str = "Đối tác") -> str:
        """Sinh văn bản nhận xét tổng quan bằng Markdown gửi nhanh qua chat/email"""
        apk_info = report.get("apk_info", {})
        summary = report.get("summary", {})

        md = []
        md.append(f"# [BÁO CÁO KIỂM THỬ TUÂN THỦ TÍCH HỢP ADS - {partner_name.upper()}]")
        md.append(f"- **Tên ứng dụng / Gói**: `{apk_info.get('app_name')}` (`{apk_info.get('package_name')}`)")
        md.append(f"- **Phiên bản**: v{apk_info.get('version_name')} (Build: {apk_info.get('version_code')}) | Dung lượng: {apk_info.get('file_size_mb')} MB")
        md.append(f"- **Đánh giá tổng quan**: Đạt **{summary.get('pass')}/{summary.get('total')} tiêu chí** (Tỷ lệ tuân thủ tự động: {summary.get('compliance_score')}%)")
        md.append("\n---\n")

        checklist = report.get("checklist", {})
        has_issues = False

        for phase_key, phase_data in checklist.items():
            failed_in_phase = [it for it in phase_data.get("items", []) if it.get("status") == "FAIL"]
            if failed_in_phase:
                has_issues = True
                md.append(f"### ❌ {phase_data.get('title')}:")
                for item in failed_in_phase:
                    md.append(f"**[{item.get('id')}] [{item.get('function').upper()}] {item.get('title')}**")
                    md.append(f"- **Hiện trạng thực tế**: {item.get('actual')}")
                    md.append(f"- **Yêu cầu chuẩn**: {item.get('expected')}")
                    if item.get("notes"):
                        md.append(f"- **Hướng dẫn khắc phục**: {' '.join(item.get('notes'))}")
                    md.append("")

        if not has_issues:
            md.append("✅ **Chúc mừng! Không phát hiện lỗi cấu hình nghiêm trọng nào trong tệp APK.**")

        md.append("\n*Chi tiết tài liệu tham chiếu: https://docs.itgproduct.com/s/android-sdk-publisher/doc/erain-studio-ad-integration-guide-uiux-standards-RBa1FbknOR*")
        return "\n".join(md)
