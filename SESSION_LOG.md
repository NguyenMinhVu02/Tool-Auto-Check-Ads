# Nhật ký phiên làm việc

## Trạng thái hiện tại

- Cập nhật: 2026-09-25 10:19 (Asia/Ho_Chi_Minh).
- Mục tiêu: Push bản rule pack và web localhost lên Git trước khi làm bước tiếp theo.
- Trạng thái: Hoàn tất push tính năng; chấm logic tự động vẫn còn lại.
- Kết quả: Commit tính năng `0e42266` đã push lên `origin/main`; `apk-audit serve` mở `http://127.0.0.1:8765`, lưu upload và report trong `out/web`.
- Kiểm tra: 18/18 unittest đạt; rule pack hợp lệ với 10 luật; `git diff --cached --check` đạt trước commit.
- Giới hạn: Engine AI/static semantic chưa nối; 10 luật logic vẫn UNKNOWN với engine none. Web chỉ xử lý một file mỗi lần, danh sách job trong bộ nhớ phiên server. Chưa thử APK thương mại.
- Bước tiếp theo: Nối bộ chấm logic có evidence; sau đó cải thiện web theo nhu cầu sử dụng thực tế.

## Lịch sử phiên

### 2026-09-25 10:19 — Push rule pack và web localhost (Asia/Ho_Chi_Minh)

- Mục tiêu: Push toàn bộ thay đổi đã triển khai lên Git trước bước tiếp theo.
- Trạng thái: Hoàn tất.
- Đã làm: Kiểm tra remote, staged 13 file mã/tài liệu/test từ hai phiên trước, commit `0e42266` và push `origin/main`.
- File thay đổi: SESSION_LOG.md (ghi nhận kết quả push).
- Quyết định quan trọng: Giữ nguyên nhánh main; không thêm thay đổi chức năng trong lượt push này.
- Kiểm tra và kết quả: 18/18 unittest đạt, `rules check` đạt 10 luật, staged diff check đạt, GitHub nhận commit `0e42266`.
- Việc còn lại / trở ngại: Không có cho yêu cầu push; engine chấm logic và thử APK thực tế thuộc bước sau.
- Bước tiếp theo: Chờ yêu cầu triển khai bước tiếp theo.

### 2026-09-25 10:16 — Web localhost bản khung (Asia/Ho_Chi_Minh)

- Mục tiêu: Cho người dùng nhìn và dùng thử khung web local trước khi hoàn thiện các phần kiểm tra khác.
- Trạng thái: Hoàn tất trong phạm vi web khung.
- Đã làm: Tạo HTTP server chỉ bind 127.0.0.1, giao diện kéo thả APK/XAPK/APKM, upload stream, xử lý một job một lúc, gọi pipeline chung, polling kết quả và tải report JSON; cập nhật CLI/README.
- File thay đổi: apk_audit/web.py, apk_audit/web_assets/{index.html,app.css,app.js}, apk_audit/cli.py, tests/test_web.py, README.md, SESSION_LOG.md.
- Quyết định quan trọng: Dùng thư viện chuẩn Python; hiển thị UNKNOWN trung thực khi engine none; giữ output/upload trong out/web; không sửa các thay đổi sẵn có từ phiên trước.
- Kiểm tra và kết quả: 18/18 unittest đạt; Chrome headless render trang; upload archive smoke qua HTTP trả package demo.web và 10 UNKNOWN; wheel chứa web assets; git diff --check đạt.
- Việc còn lại / trở ngại: Chưa nối semantic/AI engine, chưa thử APK thực tế; job list chỉ sống trong tiến trình server.
- Bước tiếp theo: Triển khai logic chấm có bằng chứng rồi thử APK đối tác.

### 2026-09-25 10:05 — Trích chuẩn ads/init từ base (Asia/Ho_Chi_Minh)

- Mục tiêu: Lấy logic init, remote config, phân phối ID, placement Splash/Language/Onboarding/Welcome, observer và tracking từ base để cấp dữ liệu cho apk-audit.
- Trạng thái: Hoàn tất dữ liệu/rule pack; chấm tự động và web để phase sau.
- Đã làm: Fetch và xác nhận base main e8f4337; đọc mã thực tế, commit tracking 56eb8b1; viết contract có inventory/timing và ba điểm không nhất quán trong base; tạo 10 luật agent, regex extract, cập nhật README.
- File thay đổi: README.md, SESSION_LOG.md, rulepacks/default/{context.md,extract.yaml,pack.yaml,rules/ads-flow.yaml}, docs/base-ads-contract.md.
- Quyết định quan trọng: Chấm logic thay vì tên hàm, không áp ID mẫu base lên app khác; thiếu ADS SCRIPTS/working checklist thì không kết luận ID/token đúng; không sao chép lỗi show inter Onboarding và mapping event theo index cứng.
- Kiểm tra và kết quả: `rules check` đạt 10 luật; smoke CLI tạo 10 UNKNOWN khi engine none; 16/16 unittest đạt; `git diff --check` đạt. Chưa chạy APK đối tác thật.
- Việc còn lại / trở ngại: Agent live chưa nối; web localhost thuộc phase sau. Muốn đối chiếu ID cụ thể cần tài liệu app đối tác.
- Bước tiếp theo: Nối semantic checker có evidence và kiểm bằng APK thật trước khi thêm web kéo thả.

### 2026-09-25 09:43 — Pull và rà soát mức triển khai (Asia/Ho_Chi_Minh)

- Mục tiêu: Kéo mã mới nhất từ Git và báo trạng thái dự án.
- Trạng thái: Hoàn tất.
- Đã làm: Kiểm tra remote/nhánh; fetch và pull qua SSH; so sánh HEAD với FETCH_HEAD; rà lại bộ luật mặc định.
- File thay đổi: SESSION_LOG.md; không có thay đổi mã từ remote.
- Quyết định quan trọng: Dùng SSH vì URL fetch HTTPS yêu cầu đăng nhập; pull chỉ cho phép fast-forward, giữ thay đổi cục bộ.
- Kiểm tra và kết quả: HEAD = FETCH_HEAD = 9edd0d0; pull báo Already up to date. 15/16 unittest đạt trong sandbox; MCP stdio timeout ở sandbox, chạy riêng ngoài sandbox đạt.
- Việc còn lại / trở ngại: Không có cho yêu cầu pull; chuẩn ads/init và các adapter live chưa triển khai.
- Bước tiếp theo: Chờ yêu cầu bổ sung rule pack hoặc tích hợp.


### 2026-09-25 09:40 — Giải thích chức năng dự án (Asia/Ho_Chi_Minh)

- Mục tiêu: Trả lời dự án đang làm gì và chức năng ra sao.
- Trạng thái: Hoàn tất.
- Đã làm: Đối chiếu README, mã nguồn chính và bộ luật mặc định; xác định luồng đầu vào, xử lý, báo cáo và giới hạn hiện tại.
- File thay đổi: SESSION_LOG.md.
- Quyết định quan trọng: Mô tả theo trạng thái mã nguồn hiện tại; không xem bộ khung là bộ kiểm chuẩn ads/init đã hoàn thiện.
- Kiểm tra và kết quả: Git sạch trước khi ghi nhật ký; các file liên quan đã đọc. Không chạy kiểm thử vì không sửa mã.
- Việc còn lại / trở ngại: Không có trong phạm vi yêu cầu giải thích.
- Bước tiếp theo: Chờ yêu cầu bổ sung luật ads/init hoặc tích hợp còn thiếu.


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
