# Thêm Claude CLI và chọn engine trên web

Mục tiêu: máy chạy backend tự phát hiện Codex/Claude CLI, người dùng chọn engine trước khi upload; cùng pipeline JADX, rule và verifier cho cả hai.

- [x] Adapter Claude chạy non-interactive, JSON schema, chỉ cấp Read/Glob/Grep, bỏ MCP/customization, giới hạn tool calls và timeout; lỗi CLI thành UNKNOWN như Codex.
- [x] API engines trả installed/default và API job lưu engine đã chọn; không đổi engine giữa chừng và không tự chuyển sang tài khoản khác khi lỗi.
- [x] Web Select và nút phát hiện lại, tên engine hiển thị đúng ở tiến độ/kết quả; không cho chạy nếu không có CLI.
- [x] Test adapter (structured output, timeout, budget, CLI lỗi), detection và propagation API; build frontend, smoke Claude trên workspace mẫu nếu tài khoản sẵn sàng; cập nhật README/SESSION_LOG.

Detection chỉ kiểm tra binary trên PATH của backend. Không tự cài hay đăng nhập; dùng phiên đăng nhập hiện có. Claude dùng model mặc định của CLI; Codex vẫn gpt-6-luna. Chưa thêm bộ chọn model. Giữ toàn bộ sửa CSV đang có, chưa commit/push.

Kiểm chứng 2026-10-16: 51/51 unittest đạt, frontend build đạt, HTTP engines/assets đạt. Máy có Claude Code 2.1.278 nhưng phiên OAuth hết hạn; lượt smoke thực trả UNKNOWN/engine_error với thông báo xác thực rõ ràng. Chưa kiểm chứng verdict thành công từ model Claude thật; cần đăng nhập lại rồi chạy.
