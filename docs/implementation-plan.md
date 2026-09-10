# Kế hoạch khung apk-audit

Mục tiêu: khung chạy cục bộ theo thiết kế v2, không chứa luật nghiệp vụ ads/init.
Thiết kế gốc: 2026-09-10-apk-audit-design.md.
Stack: Python >=3.11, PyYAML, platformdirs, FastMCP tùy chọn; quản lý bằng uv.

- [x] Hợp đồng và CLI: dataclass Facts/Rule/Finding, lỗi có mã thoát, config, package.
- [x] Intake và facts: nhận workspace hoặc APK/XAPK/APKM; kiểm tra ZIP; jadx; parse manifest/assets/strings; chỉ mục smali. Provider tải Play là giao diện mở rộng, chưa scrape website.
- [x] Tool: chín hàm chỉ đọc có giới hạn kết quả; chặn traversal/symlink; MCP stdio bọc hàm.
- [x] Rule pack: metadata/schema/ID; bảy phép kiểm tra tổng quát; bộ luật mặc định rỗng.
- [x] Agent: giao diện Engine, engine none và replay, guardrails, cache theo hash nội dung. Claude/Codex để adapter chưa kích hoạt, không giả lập kết luận.
- [x] Pipeline/report: API run, report JSON/Markdown, facts, rules check/list, doctor, MCP; báo rõ chức năng chưa nối.
- [x] Kiểm chứng: viết test trước, chạy thấy thiếu implementation; sau đó kiểm tra workspace mẫu, lỗi rule, evidence giả, cache, ZIP độc hại, CLI và MCP.
- [x] Bàn giao: README chỉ rõ chỗ thêm logic, phạm vi đã chạy/chưa chạy; cập nhật SESSION_LOG.

Các quyết định: workspace đầu vào chỉ đọc; facts và xref mới ghi vào output. Cache bao gồm nội dung luật/context/docs/workspace và phiên bản tool. Thiếu engine không được tạo PASS. Không làm web M7 ở bản khung. Không commit/push.

## Kết quả kiểm chứng 2026-09-10

- 16 kiểm thử unittest đạt; MCP stdio chạy ngoài sandbox vì sandbox gây timeout bắt tay.
- CLI help, doctor, rules check và demo workspace chạy được.
- jadx 1.5.6 đã xử lý gói ZIP/APK thử nghiệm chỉ chứa manifest/assets để kiểm chứng đường gọi subprocess và xuất báo cáo; chưa kiểm thử APK Android phát hành thật.
- Build sdist và wheel thành công. Chưa kiểm thử Windows/macOS hoặc engine AI live.
