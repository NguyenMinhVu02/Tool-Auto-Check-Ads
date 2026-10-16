# Nhật ký phiên làm việc

## Trạng thái hiện tại

- Cập nhật: 2026-10-16 15:29 (Asia/Ho_Chi_Minh).
- Mục tiêu: Commit và push các cải tiến audit lên GitHub theo yêu cầu người dùng.
- Trạng thái: Đang làm; đã kiểm thử và kiểm tra remote, chuẩn bị commit/push.
- Kết quả: Nhận hai mẫu CSV thật; kiểm kê key/ID, Package, App ID; thêm rule giao thoa thành 11 rule; siết prompt theo nhánh và hợp đồng app; sửa bằng chứng một lần với đủ context; xác minh được đoạn nhiều dòng; cache theo từng rule và tiến độ n/11 trên web. Web mã mới chạy tại http://127.0.0.1:8765.
- Kiểm tra: 35/35 unittest đạt, frontend build đạt, rule pack hợp lệ, git diff --check đạt. CSV thật có 24 placement, local release 23, 23 ID chung khớp, thiếu inter_onboarding; Package và App ID khớp. Đã chạy các lượt đủ 11 rule (~11–12 phút) và kiểm chứng riêng sau hiệu chỉnh; bản tổng hợp tại out/cast-tv-final-review/validation.md.
- Giới hạn: Chưa chạy lại toàn bộ 11 rule sau sửa cuối về đoạn trích nhiều dòng; đã xác minh trực tiếp 5/5 đoạn của rule ID và chạy live rule giao thoa. Kết luận mã tĩnh vẫn cần rà ngữ nghĩa; các FAIL cũ về page 1/Welcome/Splash retry đã được ghi rõ và hiệu chỉnh. Chưa kiểm runtime; job mất khi restart server; lượt đầu web vẫn cần nhiều phút.
- Bước tiếp theo: Người dùng thử APK và CSV trên web; kiểm runtime các nhánh quảng cáo/Firebase khi cần; commit/push chỉ khi được yêu cầu.

## Lịch sử phiên

### 2026-10-16 15:29 — Chuẩn bị push cải tiến audit (Asia/Ho_Chi_Minh)

- Mục tiêu: Đưa toàn bộ cải tiến CSV, inventory, bằng chứng, rule và tiến độ web lên GitHub.
- Trạng thái: Đang làm.
- Đã làm: Kiểm tra Git main và remote; fetch HTTPS thiếu đăng nhập, fetch trực tiếp SSH thành công; HEAD và main trên remote cùng commit trước khi commit mới.
- File thay đổi: Mã và tài liệu trong lượt triển khai trước, kèm SESSION_LOG.md. APK/CSV đối tác, cache và báo cáo out/ bị Git ignore.
- Kiểm tra: Chạy mới 35/35 unittest đạt; npm run build đạt; git diff --check đạt.
- Bước tiếp theo: Commit, push main và xác minh commit trên remote; ghi kết quả xuất bản.

### 2026-10-16 15:21 — Cơ chế và phần cần hoàn thiện (Asia/Ho_Chi_Minh)

- Mục tiêu: Giải thích luồng xử lý và xác định tiêu chí để coi công cụ audit tĩnh đủ ổn định.
- Trạng thái: Hoàn tất đánh giá, không triển khai mã mới.
- Đã làm: Đối chiếu pipeline, web job, nhật ký và Git; phân biệt đối chiếu deterministic với Codex suy luận, xác minh đoạn trích với xác minh ngữ nghĩa, local web với lời gọi AI qua Codex.
- File thay đổi: SESSION_LOG.md.
- Kiểm tra: Đọc mã hiện tại; không chạy thêm audit hoặc test, kết quả 35/35 test thuộc lượt triển khai ngay trước đó.
- Việc còn lại: Kiểm thử đầu cuối bản cuối qua web; tập APK có lỗi đã biết để đo sai lệch; xác minh đường đi/callback trước FAIL; lưu job/checkpoint/lịch sử; cập nhật và version hóa base rules; runtime cho kết luận load/show/Firebase; đo cache và tối ưu sau benchmark.
- Bước tiếp theo: Ưu tiên chất lượng kết luận và kiểm thử web đầu cuối trước tối ưu thời gian hoặc bổ sung runtime.

### 2026-10-16 15:14 — Triển khai cải thiện audit và web (Asia/Ho_Chi_Minh)

- Mục tiêu: Lập kế hoạch và triển khai các sửa đổi sau pilot để đọc CSV thật, rà JADX sâu hơn và hiện tiến độ từng rule.
- Trạng thái: Hoàn tất lát cắt đã lên kế hoạch; chưa commit/push.
- Đã làm: Tạo kế hoạch docs/2026-10-16-audit-depth-plan.md; tách parser documents.py; tạo inventory.py với key/ID/Package/App ID và vị trí chuỗi config/placement; thêm rule giao thoa, điều chỉnh Init/Onboarding/Welcome theo logic thực và hợp đồng app; sửa verifier hỗ trợ đoạn nhiều dòng; thêm một lượt sửa dẫn chứng có đầy đủ context; cache từng rule và dependency của rule cuối; web dùng cache trong out/web/cache và hiện rule hiện tại/số hoàn thành/kiểm kê.
- File thay đổi: README.md, SESSION_LOG.md, apk_audit/{agent,documents,inventory,pipeline,verdict_cache,web}.py, frontend/src/{App.jsx,style.css}, apk_audit/web_assets/{app.js,app.css}, rulepacks/default/rules/ads-flow.yaml, tests/{test_documents,test_inventory,test_framework,test_integration,test_web}.py, kế hoạch trong docs. Artifact local trong out/ bị Git ignore.
- Kiểm tra và kết quả: 35/35 unittest đạt ngoài sandbox cho socket/MCP; npm run build đạt; rule pack check và git diff --check đạt. Parser nhận trực tiếp hai CSV gốc (24 placement/65 hàng working); 23 ID chung khớp config release, thiếu inter_onboarding, Package/App ID khớp. Các lượt đủ 11 rule mất 673s và 721s; một lượt sau bị chủ động dừng để sửa prompt repair thiếu docs. Rule Init hiệu chỉnh PASS với 14 evidence; rule ID v5 được xác minh lại đủ 5/5 đoạn nhiều dòng; rule giao thoa cuối UNKNOWN, 12/12 evidence đúng.
- Rà chất lượng: Bác bỏ kết luận page 1 không có native do nhầm mask page 2; không ép slot Welcome ngoài ADS SCRIPTS; bác bỏ Splash kẹt vì onResume có Runnable retry. Bản tổng hợp đã rà ở out/cast-tv-final-review/validation.md (1 PASS, 8 FAIL, 2 UNKNOWN theo rule, không phải một lượt mới duy nhất).
- Việc còn lại: Chưa kiểm runtime quảng cáo/Remote Config live/Firebase; chưa benchmark cache toàn lượt sau sửa cuối; job chưa lưu bền qua restart; chưa xây bộ tìm mọi bug Java ngoài luồng ads.
- Bước tiếp theo: Dùng web với APK/CSV thật và lấy runtime evidence khi cần; chỉ commit/push khi người dùng yêu cầu.

### 2026-10-12 14:55 — Đánh giá độ sâu audit và thời gian web (Asia/Ho_Chi_Minh)

- Mục tiêu: Trả lời liệu công cụ hiện đã đọc JADX đủ kỹ để tìm bug/khác biệt và người dùng phải chờ bao lâu trên web.
- Trạng thái: Hoàn tất rà soát; cải tiến chưa triển khai.
- Đã làm: Đọc pipeline, Codex adapter, evidence verifier, JADX unpack/cache, web job và 10 rule; đo số liệu từ pilot Cast TV.
- File thay đổi: `SESSION_LOG.md` (chỉ nhật ký). Không sửa source, không commit/push.
- Kiểm tra và kết quả: 10 rule chạy tuần tự trong ~842 giây, JADX ~34 giây; 124 tool calls, 92 evidence/24 file (20 Java), 89 evidence đúng file/dòng. Web dùng cùng engine và pipeline, cache của pilot đặt riêng trong `/tmp` nên web mặc định chưa tận dụng lượt pilot này. Hai CSV bảng gốc bị từ chối ngay ở `load_document`.
- Việc còn lại / trở ngại: Chưa có chế độ tìm bug ngoài ads, smali xrefs, evidence liên kết logic đủ mạnh, CSV parser theo mẫu, tiến độ từng rule/ETA, job bền vững và kiểm thử runtime.
- Bước tiếp theo: Ưu tiên parser CSV và tiến độ, sau đó bổ sung phân tích call graph/nhánh lỗi và kiểm chứng verdict; đo lại thời gian trên web với dữ liệu thật.

### 2026-10-12 14:27 — Pilot Cast TV APK và tài liệu thật (Asia/Ho_Chi_Minh)

- Mục tiêu: Chạy thử toàn bộ audit với APK Cast TV 1.0.8 và hai CSV đối tác; đánh giá độ hữu ích và giới hạn của kết quả.
- Trạng thái: Hoàn tất pilot tĩnh; runtime và parser CSV còn việc.
- Đã làm: Xác nhận ba file đầu vào; phát hiện CLI chỉ nhận CSV `key,value`; chuyển tạm hai CSV thành JSON ở `/tmp/apk-audit-cast-docs/`; chạy Codex Luna đủ 10 rule; đối chiếu thủ công các verdict và inventory placement; lưu `report.md`, `report.json`, trace, `validation.md` trong `out/cast-tv-pilot/`.
- File thay đổi: `SESSION_LOG.md`; `out/cast-tv-pilot/` (artifact audit, bị Git ignore). Không sửa source, không commit/push.
- Kiểm tra và kết quả: 1 PASS, 7 FAIL, 2 UNKNOWN; 124 tool calls, ~842 giây. Package và AdMob App ID khớp docs; 23 ID chung khớp CSV, thiếu key `inter_onboarding` trong release config. Xác nhận code path config debug, preload Splash không phủ hết nhánh, UA gate Onboarding, tracking event và banner reload bằng mã giải biên dịch. Không kiểm thử runtime hoặc chạy unittest mới.
- Việc còn lại / trở ngại: Parser không hỗ trợ CSV ADS SCRIPTS/working file dạng bảng; các kết luận runtime về Remote Config/App Open/show ad/Firebase cần thiết bị và log để kiểm chứng.
- Bước tiếp theo: Triển khai parser CSV đúng mẫu, thử lại qua web, rồi thu runtime evidence; chỉ commit/push theo yêu cầu người dùng.

### 2026-10-12 13:54 — Đề xuất bước tiếp theo (Asia/Ho_Chi_Minh)

- Mục tiêu: Xếp thứ tự việc cần triển khai tiếp.
- Trạng thái: Hoàn tất đề xuất.
- Đã làm: Đối chiếu bộ 10 rule, pipeline AI, web job và các giới hạn trong README; xác định kiểm định kết quả trên APK thật là bước cần làm trước.
- File thay đổi: SESSION_LOG.md (nhật ký phiên).
- Kiểm tra và kết quả: Đã đọc mã và tài liệu liên quan; server localhost vẫn nghe cổng 8765. Không chạy test hoặc audit mới trong phiên này.
- Việc còn lại / trở ngại: Chưa có APK đối tác và cặp tài liệu thật để đo sai lệch verdict; base rule pack đang bám commit `e8f4337` và không tự cập nhật; web chưa có tiến độ từng rule, job chỉ lưu trong bộ nhớ.
- Bước tiếp theo: Chạy pilot với dữ liệu thật, ghi kết quả kỳ vọng từng rule, chỉnh bộ luật và evidence, rồi hoàn thiện trải nghiệm web.

### 2026-10-12 13:51 — Chạy web audit local (Asia/Ho_Chi_Minh)

- Mục tiêu: Khởi động web theo yêu cầu người dùng.
- Trạng thái: Hoàn tất.
- Đã làm: Chạy `.venv/bin/apk-audit serve` và mở `http://127.0.0.1:8765` trong phiên Google Chrome hiện có.
- File thay đổi: SESSION_LOG.md (nhật ký phiên, giữ thay đổi ghi nhận từ lượt rà soát trước).
- Kiểm tra và kết quả: HTTP GET trang chủ trả `200 OK`; chưa upload APK trong phiên này.
- Việc còn lại / trở ngại: Audit trên APK đối tác thật cùng tài liệu chưa được kiểm định; server chỉ chạy khi tiến trình hiện tại còn sống.
- Bước tiếp theo: Người dùng chọn APK trên web và bấm Bắt đầu kiểm tra.

### 2026-10-12 13:49 — Rà soát tiến độ dự án (Asia/Ho_Chi_Minh)

- Mục tiêu: Cho biết dự án đã triển khai đến đâu.
- Trạng thái: Hoàn tất rà soát.
- Đã làm: Đối chiếu Git, README, nhật ký và trạng thái web server; chạy lại bộ kiểm thử.
- File thay đổi: SESSION_LOG.md (chỉ nhật ký phiên).
- Kiểm tra và kết quả: HEAD = nhánh theo dõi cục bộ `origin/main` = `7163042`; working tree sạch trước khi ghi nhật ký; 24/24 unittest đạt; không thấy server lắng nghe cổng 8765. Chưa kiểm tra remote GitHub trực tiếp.
- Việc còn lại / trở ngại: Chưa audit APK đối tác thật với cặp ADS SCRIPTS/working file, chưa kiểm định chất lượng 10 verdict AI; job web chỉ lưu trong bộ nhớ; các mục mở rộng trong README chưa triển khai.
- Bước tiếp theo: Chạy audit thực tế, rà bằng chứng và hiệu chỉnh rule/AI nếu cần.

### 2026-10-06 17:55 — Push Ant Design và Codex Luna (Asia/Ho_Chi_Minh)

- Mục tiêu: Đưa toàn bộ thay đổi mã hiện tại lên Git theo yêu cầu người dùng.
- Trạng thái: Hoàn tất sau khi push `origin/main`.
- Đã làm: Fetch main qua SSH và xác nhận remote chưa có commit mới; build frontend; chạy test; commit mã, frontend build và nhật ký; push `origin/main`.
- File thay đổi: .gitignore, README.md, SESSION_LOG.md, apk_audit/{agent.py,cli.py,config.py,engines.py,pipeline.py,web.py}, apk_audit/web_assets/{index.html,app.js,app.css}, frontend/*, tests/{test_codex_engine.py,test_framework.py,test_integration.py,test_web.py}.
- Kiểm tra và kết quả: `npm run build -- --logLevel error` đạt; 24/24 unittest đạt; `git diff --check` đạt; remote main trước push = `403267f`.
- Việc còn lại / trở ngại: Chưa chạy và kiểm định 10 rule với APK đối tác thật cùng cặp tài liệu thực tế.
- Bước tiếp theo: Audit APK đối tác và rà từng verdict AI.

### 2026-10-06 17:24 — Đổi giao diện sang Ant Design (Asia/Ho_Chi_Minh)

- Mục tiêu: Dùng Ant Design cho web audit local.
- Trạng thái: Hoàn tất trong phạm vi giao diện; chưa commit/push.
- Đã làm: Tạo frontend React/Vite với Ant Design và Poppins; thay màn upload, tài liệu, tiến độ, thống kê, danh sách rule bằng component Ant Design; giữ API/job hiện tại; build file tĩnh vào `apk_audit/web_assets`; cập nhật CSP để Ant Design tạo style; mở lại web trong Google Chrome.
- File thay đổi: .gitignore, README.md, SESSION_LOG.md, apk_audit/web.py, apk_audit/web_assets/{index.html,app.js,app.css}, frontend/{package.json,package-lock.json,vite.config.js,index.html,src/*}, tests/test_web.py. Các thay đổi Codex Luna từ phiên trước vẫn được giữ nguyên.
- Kiểm tra và kết quả: `npm run build` đạt; Chrome screenshot cho thấy bố cục Ant Design; Chrome DevTools xác nhận chọn APK chỉ bật nút Bắt đầu kiểm tra, không tự audit; 24/24 unittest đạt; `uv build --offline` tạo wheel chứa assets mới; `git diff --check` đạt.
- Việc còn lại / trở ngại: Chưa kiểm định verdict AI bằng APK và tài liệu đối tác thật; chưa commit/push theo quy tắc dự án.
- Bước tiếp theo: Người dùng kiểm tra giao diện tại localhost; sau đó audit APK thật và rà chất lượng rule.

### 2026-10-06 17:11 — Mở web trong Chrome (Asia/Ho_Chi_Minh)

- Mục tiêu: Mở giao diện web audit local bằng Google Chrome.
- Trạng thái: Hoàn tất.
- Đã làm: Khởi động `apk-audit serve` trên 127.0.0.1:8765, mở URL bằng `google-chrome` trong phiên trình duyệt hiện có.
- File thay đổi: SESSION_LOG.md (nhật ký).
- Kiểm tra và kết quả: HTTP GET tới trang chủ trả `200 OK` ngoài sandbox; chưa thao tác upload trong phiên này.
- Việc còn lại / trở ngại: Server chạy trong phiên terminal hiện tại; tích hợp AI chưa kiểm định bằng APK đối tác thật.
- Bước tiếp theo: Người dùng có thể chọn APK và bấm Bắt đầu kiểm tra trong Chrome.

### 2026-10-06 16:59 — Kết nối Codex Luna và rà soát tiến độ (Asia/Ho_Chi_Minh)

- Mục tiêu: Dùng Codex `gpt-6-luna` đánh giá rule ads qua CLI/web và báo tiến độ.
- Trạng thái: Đang làm; tích hợp và smoke test xong, kiểm định với APK đối tác còn lại.
- Đã làm: Thay adapter Codex mẫu bằng lời gọi Codex CLI có JSON schema, phiên chỉ đọc, timeout và ngân sách tool; đặt làm engine mặc định cho CLI/web; chỉ chấp nhận PASS/FAIL khi có evidence file/dòng hợp lệ; cập nhật giao diện, README và kiểm thử.
- File thay đổi: README.md, SESSION_LOG.md, apk_audit/{agent.py,cli.py,config.py,engines.py,pipeline.py,web.py}, apk_audit/web_assets/index.html, tests/{test_codex_engine.py,test_framework.py,test_integration.py,test_web.py}.
- Kiểm tra và kết quả: 24/24 unittest đạt ngoài sandbox. Chạy live `ADS_INIT_ORDER` trên `examples/workspace` bằng Codex `gpt-6-luna`: 4 tool calls, report tạo thành công, UNKNOWN có evidence xác minh vì workspace mẫu thiếu mã SDK. `git diff --check` đạt. Không thử APK đối tác hay 10 luật live cùng lúc.
- Việc còn lại / trở ngại: Cần APK và cặp tài liệu thật để xác nhận độ chính xác của verdict; các thay đổi chưa commit/push. Chưa kiểm tra remote GitHub trực tiếp.
- Bước tiếp theo: Chạy audit thực tế với tài liệu đối tác, rà từng verdict và hiệu chỉnh rule nếu cần.

### 2026-10-01 15:04 — Rà soát tiến độ (Asia/Ho_Chi_Minh)

- Mục tiêu: Cho biết phần đã triển khai và phần chưa triển khai.
- Trạng thái: Hoàn tất rà soát.
- Đã làm: Đối chiếu SESSION_LOG, README, mã nguồn, trạng thái Git và tiến trình web server.
- File thay đổi: SESSION_LOG.md (chỉ nhật ký phiên).
- Kiểm tra và kết quả: HEAD = origin/main theo nhánh theo dõi cục bộ = `403267f`; chưa có thay đổi mã trước khi ghi nhật ký; không thấy tiến trình `apk-audit serve`. Kết quả 22/22 test thuộc phiên trước; chưa chạy lại.
- Việc còn lại / trở ngại: Engine AI/semantic chưa kết nối, nên 10 luật logic trả UNKNOWN với `engine none`; chưa audit APK đối tác thật với tài liệu ADS SCRIPTS/working thực tế; job web chỉ lưu trong bộ nhớ. Kiểm tra HTTP localhost bị sandbox chặn socket, nên chưa xác nhận cổng trực tiếp.
- Bước tiếp theo: Nối engine chấm logic có bằng chứng và chạy đối chiếu APK cùng tài liệu thật.

### 2026-09-25 10:46 — Push UI và tiến độ audit (Asia/Ho_Chi_Minh)

- Mục tiêu: Đưa các thay đổi web của hai phiên gần nhất lên Git trước bước tiếp theo.
- Trạng thái: Hoàn tất sau khi commit nhật ký phiên này và push `origin/main`.
- Đã làm: Xác nhận remote main không có commit mới; chạy test; chuẩn hóa khoảng trắng trong giấy phép font; commit mã và tài liệu `7d9a5f3`, push thành công.
- File thay đổi: README.md, SESSION_LOG.md, apk_audit/pipeline.py, apk_audit/web.py, apk_audit/web_assets/{index.html,app.css,app.js,fonts/*}, tests/{test_integration.py,test_web.py}.
- Kiểm tra và kết quả: 22/22 unittest đạt; `node --check` và `git diff --cached --check` đạt; GitHub nhận `7d9a5f3`. Kiểm tra trạng thái Git cuối phiên sau push nhật ký.
- Việc còn lại / trở ngại: Không có cho yêu cầu push. Engine none vẫn trả UNKNOWN cho 10 luật logic.
- Bước tiếp theo: Chờ yêu cầu triển khai bộ chấm logic có evidence.

### 2026-09-25 10:39 — Cảnh báo rời trang và trạng thái audit (Asia/Ho_Chi_Minh)

- Mục tiêu: Hiện xác nhận khi người dùng rời tab đang audit và cho biết pipeline đang ở bước nào.
- Trạng thái: Hoàn tất trong phạm vi yêu cầu; chưa commit/push.
- Đã làm: Thêm callback tiến độ cho `pipeline.run`; job API trả `stage`; web tô sáng 5 bước và cập nhật mô tả; dùng `beforeunload` để yêu cầu xác nhận; lưu job ID trong sessionStorage và lấy lại kết quả sau Reload; cập nhật README.
- File thay đổi: README.md, SESSION_LOG.md, apk_audit/pipeline.py, apk_audit/web.py, apk_audit/web_assets/{index.html,app.css,app.js}, tests/{test_integration.py,test_web.py}.
- Kiểm tra và kết quả: 22/22 unittest đạt; Chrome/CDP xác nhận dialog beforeunload và khôi phục báo cáo; HTTP smoke với APK mẫu hoàn tất; node --check và git diff --check đạt. Server localhost đang chạy ở 127.0.0.1:8765.
- Việc còn lại / trở ngại: Job list nằm trong bộ nhớ server; engine none vẫn cho 10 UNKNOWN. Chưa thử APK thực tế của đối tác.
- Bước tiếp theo: Tích hợp bộ chấm logic live với evidence.

### 2026-09-25 10:32 — UI chọn file trước khi kiểm tra (Asia/Ho_Chi_Minh)

- Mục tiêu: Tách bước chọn APK khỏi chạy kiểm tra, thêm ô ADS SCRIPTS/working file và dùng font Poppins.
- Trạng thái: Hoàn tất trong phạm vi UI/input; chưa commit/push.
- Đã làm: Thêm nút Bắt đầu kiểm tra; chọn/drag APK chỉ lưu trạng thái; hai ô tài liệu CSV/JSON chỉ gửi khi chọn đủ cặp; API nhận tài liệu và truyền vào `apk_audit.run`; nhúng Poppins và OFL cho chế độ offline; cập nhật README.
- File thay đổi: README.md, SESSION_LOG.md, apk_audit/web.py, apk_audit/web_assets/{index.html,app.css,app.js,fonts/*}, tests/test_web.py.
- Quyết định quan trọng: Thiếu một tài liệu thì bỏ qua cả hai; giới hạn 5 MiB/tài liệu; chỉ nạp JSON object hoặc CSV key,value theo parser hiện có. Engine none vẫn trả UNKNOWN dù có tài liệu.
- Kiểm tra và kết quả: 20/20 unittest đạt; Chrome screenshot và CDP xác nhận chọn APK chưa có API request, bấm nút mới chạy; HTTP smoke với cặp tài liệu thành công; wheel chứa 4 font và giấy phép; git diff --check đạt.
- Việc còn lại / trở ngại: Chưa có engine chấm logic nên tài liệu được truyền vào pipeline nhưng chưa tạo verdict tự động; chưa thử file ADS SCRIPTS/working thực tế.
- Bước tiếp theo: Thử với tài liệu thật và nối bộ chấm logic ở phiên tiếp theo.

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
