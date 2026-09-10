# Nhật ký phiên làm việc

## Trạng thái hiện tại

- Cập nhật: 2026-09-10 17:22 (Asia/Ho_Chi_Minh).
- Mục tiêu: Triển khai khung apk-audit theo thiết kế v2, để người dùng thêm chuẩn ads/init sau.
- Trạng thái: Hoàn tất trong phạm vi bản khung.
- Kết quả: Dự án `apk-audit/`, CLI, facts, tool/MCP, rule loader/checks tổng quát, agent guardrails/replay/cache, báo cáo, dữ liệu mẫu và README.
- Kiểm tra: 16 unittest đạt; MCP stdio kiểm tra ngoài sandbox; CLI/demo và build wheel/sdist đạt; smoke test jadx với archive thử nghiệm tối giản.
- Giới hạn: Chưa nối tải Play/apkcombo/apkpure, AI live Claude/Codex, baksmali, web/ask; chưa thử APK thương mại hoặc Windows/macOS.
- Bước tiếp theo: Người dùng thêm context, extract và luật trong `apk-audit/rulepacks/default/`; hoặc yêu cầu nối các adapter. Không tự suy ra chuẩn ads/init.

## Lịch sử phiên

### 2026-09-10 17:22 — Dựng khung apk-audit

- Mục tiêu: Đọc `2026-09-10-apk-audit-design.md` và bắt đầu triển khai tool, chỉ làm khung.
- Đã làm: Tạo dự án Python/uv tại `apk-audit/`, 9 tool đọc workspace, MCP stdio, intake APK/XAPK/APKM qua jadx, facts, 7 phép check tổng quát, rule pack rỗng, guardrails/cache/replay agent, CLI và báo cáo Markdown/JSON.
- File thay đổi: Toàn bộ dự án mới `apk-audit/`; cập nhật nhật ký này. Thiết kế gốc giữ nguyên.
- Quyết định: Engine mặc định none; không có luật trả cảnh báo no_rules, không xác nhận đạt chuẩn. Provider tải và AI live là điểm mở rộng trả lỗi rõ ràng. Facts/xref ghi ngoài workspace đầu vào.
- Kiểm tra: 16 kiểm thử đạt; MCP stdio thật với FastMCP 3.4.7; uv build; chạy demo và jadx 1.5.6 với gói thử nghiệm manifest/assets. Không gọi AI, không tải app thực tế.
- Môi trường: Thư viện nằm trong `.venv`, khóa bằng `uv.lock`. Cần chạy MCP test ngoài sandbox phiên này do timeout bắt tay trong sandbox.
- Còn lại theo thiết kế đầy đủ: adapter tải/AI, smali extraction, extractor SDK/DEX, nhóm phiên AI/observations, web/skill; chuẩn ads/init do người dùng bổ sung.
- Bước tiếp theo: Xem `apk-audit/README.md` và `apk-audit/docs/implementation-plan.md`.


### 2026-09-10 — Khởi tạo

- Yêu cầu: Khởi tạo file hướng dẫn agent để quản lý các phiên làm việc.
- Đã làm: Kiểm tra thư mục; tạo quy trình bắt đầu, thực hiện và bàn giao phiên.
- File tạo mới: `AGENTS.md`, `SESSION_LOG.md`.
- Kiểm tra: Đọc lại hai file sau khi tạo; thay đổi chỉ gồm tài liệu, không cần chạy kiểm thử mã.
- Ghi nhận: Thư mục có tài liệu `2026-09-10-apk-audit-design.md`; chưa đánh giá nội dung hoặc trạng thái triển khai của tài liệu này.
- Việc còn lại: Không có trong phạm vi yêu cầu.

## Mẫu cho phiên tiếp theo

```markdown
### YYYY-MM-DD HH:mm — Tên công việc (Asia/Ho_Chi_Minh)

- Mục tiêu:
- Trạng thái: Đang làm / Bị chặn / Hoàn tất.
- Đã làm:
- File thay đổi:
- Quyết định quan trọng:
- Kiểm tra và kết quả:
- Việc còn lại / trở ngại:
- Bước tiếp theo:
```

### 2026-09-10 17:41 — Chuẩn bị xuất bản repository

- Người dùng yêu cầu push lên https://github.com/NguyenMinhVu02/Tool-Auto-Check-Ads.git.
- Khởi tạo Git tại thư mục dự án, nhánh main; origin HTTPS, push qua SSH đã xác thực. Remote chưa có nhánh ở thời điểm kiểm tra.
- Đưa bản thiết kế vào docs; cập nhật đường dẫn README. Loại .venv, cache, output và dist qua .gitignore.
- Kiểm tra trước push: 16 unittest đạt; git diff --cached --check đạt.
- Trạng thái tại thời điểm ghi commit: sẵn sàng push; kết quả push sẽ được xác minh với remote.
