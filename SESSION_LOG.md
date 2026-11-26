# Nhật ký phiên làm việc

## Trạng thái hiện tại

- Phát hành 2026-11-26 11:25 (Asia/Ho_Chi_Minh): **Hoàn tất Release v0.2.1** (https://github.com/NguyenMinhVu02/Tool-Auto-Check-Ads/releases/tag/v0.2.1, ZIP 1,4 MB + ghi chú). Repo đã public. Tag v0.2.0 tồn tại nhưng workflow lỗi (2 test cần Codex CLI, đã sửa bằng `engine='none'`) nên không có Release. Thêm workflow `test.yml` chạy test mỗi lần push. Updater có đường dự phòng qua trang `/releases/latest` khi API GitHub giới hạn 60 lần/giờ/IP (có trên nhánh, chưa nằm trong ZIP v0.2.1). Đã thử thật: bản cài 0.2.0 tự cập nhật lên 0.2.1 từ GitHub và tự khởi động lại. README viết lại ngắn gọn kèm ảnh. Nhánh `feat/one-click-setup` chưa merge vào `main`.
- Tự cập nhật 2026-11-26 10:55 (Asia/Ho_Chi_Minh): **Hoàn tất code, chưa commit, server chính chưa restart**. Giao diện tối (antd darkAlgorithm + CSS). `apk_audit/updater.py`: kiểm GitHub Releases (`/api/update/status`, cache 6 giờ), cập nhật tại chỗ (`POST /api/update/apply`: tải ZIP, SHA256, thay thư mục phát hành, `uv sync`, khôi phục khi lỗi, bỏ qua thư mục git, chặn khi đang audit), thoát mã 75 để launcher (start-linux.sh / start-macos.command / start-windows.bat) chạy lại. Web: thông báo bản mới + thẻ "Cập nhật tool" ở Thiết lập máy. Version 0.2.0. 270 unittest + 10 test frontend đạt; chạy thử đầu-cuối 0.1.9 → 0.2.0 bằng feed file:// đạt (tự khởi động lại, giữ out/). Cần repo public (hoặc `APK_AUDIT_GITHUB_TOKEN`) để máy người dùng đọc được Release. Bản cài cũ (shortcut tạo trước bản này) chưa có vòng khởi động lại: lần cập nhật đầu cần mở lại biểu tượng.
- Tham khảo KOG 2026-11-26 10:45 (Asia/Ho_Chi_Minh): **Hoàn tất code, chưa commit, server chưa restart**. Rule tĩnh mới `ADS_MEDIATION_ADAPTERS` (check `mediation_adapters`, 7 mạng, adapter thiếu SDK = FAIL khi mã ít làm rối; SDK thiếu adapter = UNKNOWN; không có mediation = SKIPPED), pack 0.12.0, 18 rule, ~1 ms, 0 token. Xuất Google Sheet dùng nguyên `sheet_exporter.py` của KOG (người dùng xác nhận được phép dùng) tại `apk_audit/kog_sheet_exporter.py`, chỉ sửa escape dấu `"`; adapter `apk_audit/sheet_export.py` lấy dữ liệu từ dev_view + bảng ID Marketing; API `/api/jobs/{id}/sheet.tsv?only_fails=1`, `/summary.md`; nút "Copy cho Google Sheet", "Copy tóm tắt gửi đối tác" ở tab Marketing. 262 unittest đạt. Mục ADB (KOG device_manager): chưa làm, chờ thử log trên máy giả lập/thiết bị.
- Giao diện + model 2026-11-26 10:20 (Asia/Ho_Chi_Minh): **Hoàn tất, chưa commit** (nhánh `feat/one-click-setup`). Logo Infinity cho shortcut (ico/icns/png) và web; font Nunito; bỏ sidebar, thêm thanh tab trên cùng (Kiểm tra / Lịch sử / Kết quả / Thiết lập máy) theo hash `#/…`. Model AI không còn ghi cứng: Claude alias `sonnet`, Codex `gpt-*-sol` mới nhất theo `codex debug models`, effort low; web chỉ hiện CLI đã cài (một CLI thì không có ô chọn). 256 unittest + 9 test frontend đạt. Server 8765 đã restart.
- Cài đặt 2026-11-26 09:45 (Asia/Ho_Chi_Minh): **Hoàn tất code cài đặt một chạm, chờ thử trên Windows/macOS**. Thêm `installer/` (script cài lần đầu 3 hệ điều hành), `apk-audit shortcut`, `serve --open`, khung **Thiết lập máy** trên web (kiểm tra/cài Java, JADX, Node, Claude, Codex; mở terminal đăng nhập). 251 unittest + test frontend đạt; cài thật Java/JADX/Node/Codex vào thư mục tạm trên Linux đạt. Chưa commit, chưa restart server.
- Tài liệu 2026-11-02 09:19 (Asia/Ho_Chi_Minh): **Hoàn tất tạo `CLAUDE.md`** (lệnh build/test, kiến trúc pipeline, nguyên tắc audit). Không sửa mã chức năng, không chạy test.
- Phương án 2026-10-23 10:22 (Asia/Ho_Chi_Minh): **Hoàn tất đề xuất tối ưu bằng chứng và lượt gọi AI**, chưa triển khai. Đọc verification/claim thật của Claude `06ff1746`: ba UNKNOWN không chỉ là lỗi tọa độ/chỉ số; còn thiếu thân runnable, layout, SDK/applicability và claim full2 ngoài phạm vi chưa được phân định. Đề xuất: hợp đồng yêu cầu/checklist và phạm vi rõ trước AI; catalog evidence có ID; repair theo loại lỗi và patch có giới hạn; review độc lập với gói violation/gate/hợp đồng cần thiết; benchmark cố định và ground truth. Giữ UNKNOWN khi thiếu bằng chứng trong phạm vi, không nới verifier để giảm số UNKNOWN.
- Đánh giá 2026-10-23 09:34 (Asia/Ho_Chi_Minh): **Hoàn tất đánh giá hoạt động/token/thời gian**, không sửa mã chức năng. 241/241 unittest đạt ngoài sandbox (9,742s), frontend build đạt (4,11s); node runner báo 3 file test đạt nhưng có cảnh báo sandbox. Dùng báo cáo live đã lưu, không gọi AI mới. Công cụ phù hợp hỗ trợ kiểm tra có Dev đối chiếu; chưa có ground truth để công bố accuracy. AI chiếm 91–97% thời gian trong các lượt được phân tích. Rủi ro cần sửa: scoped cache chưa theo dõi mọi file cấp sẵn trong prompt/source_slice; PoC tổng hợp cho thấy đổi file không được dẫn chứng/đọc thêm vẫn reuse. Cần benchmark cùng đầu vào/phạm vi/cache và giảm lượt repair/review, không coi A/B slicer cũ là bằng chứng tăng tốc.
- Rà soát 2026-10-23 09:20 (Asia/Ho_Chi_Minh): **Hoàn tất giải thích chức năng dự án**. Đối chiếu README và mã hiện tại: HEAD `1c6566f`, bộ luật `0.11.1` có 17 rule; Git sạch trước khi ghi nhật ký. Các mốc commit/bộ luật bên dưới là ghi nhận cũ. Chưa chạy lại test, audit AI hoặc xác minh server/remote trong phiên này; việc kiểm chứng độ chính xác bằng APK và tài liệu thật vẫn cần tiếp tục.
- Cập nhật: 2026-10-22 (Asia/Ho_Chi_Minh). Trạng thái công việc: **Hoàn tất bàn giao, chờ kiểm thử thực tế**.
- Code: `main` tại 1446c4a đã push (remote HEAD khớp). Bộ luật 0.10.0 (17 rule: 9 AI, 7+ tĩnh), 227/227 unittest, frontend build đạt. Engine: Claude Sonnet 5 low, Codex GPT-6 Sol low; web 6 workers; cross-flow tắt mặc định.
- Đã có: báo cáo Marketing/Dev, logic từng màn + checklist, rule tĩnh theo manifest/assets/chuỗi, hồ sơ làm rối + cổng chặn báo oan + độ tin cậy, alias tên placement, dẫn chứng theo đoạn dòng + anchor, resume phiên Claude/Codex, cache theo file, chọn sheet XLSX.
- Chưa kiểm live: prompt/schema mới nhất (basis, code_profile) với AI thật; Codex với evidence dạng đoạn dòng; token thực tế sau các tối ưu.
- Việc cần làm tiếp: (1) chạy audit lại ≥1 app bằng Claude Sonnet 5 low và đối chiếu bằng mắt các ❌/độ tin cậy; (2) xác nhận `native_onboarding_fullscreen_*_3` tương ứng `_2` trong tài liệu để thêm alias; (3) cân nhắc nút "Đánh dấu báo oan"; (4) git fetch HTTPS đang báo "Repository not found" (repo private) — dùng SSH hoặc đăng nhập lại credential.
- Ghi chú trạng thái các phiên trước được giữ ngay dưới đây.

### Ghi chú trạng thái cũ (lưu)

- 2026-10-21 09:40: Đã lập kế hoạch triển khai `docs/superpowers/plans/2026-10-21-readable-fast-cheap-audit.md` (đo → báo cáo Dev/MKT → rule tĩnh, bỏ rule không áp dụng, cache theo file, bản đồ luồng → cắt context/đầu ra). Chưa bắt đầu code; chờ người dùng đổi model rồi triển khai.
- **Việc cho phiên 2026-10-21 (người dùng ghi chú, Đang làm):**
  1. Kiểm tra ad config đúng yêu cầu chưa: nội dung `ad_config.json`/`ad_config_debug.json` và Remote Config so với ADS SCRIPTS/working file (ID, isEnable, các trường cấu hình), không chỉ so ID.
  2. Kiểm tra bật/tắt ads hợp lý chưa: cờ enable từng placement theo màn/tài liệu (placement bị gạch/tô màu phải tắt, placement đang dùng phải bật).
  3. Logic màn Welcome back / App Open: rà lại luồng Welcome, loại trừ với App Open, điều kiện chọn biến thể chỉ inter/native.
- Cập nhật 2026-10-20 18:55: main tại 45cb80e (đã merge PR #2 token + tóm tắt Marketing). Server đang chạy bản này, Claude Sonnet 5.5 low, 6 workers, cross-flow tắt mặc định. Chưa đo token lượt Sonnet low mới.
- Cập nhật: 2026-10-20 14:47 (Asia/Ho_Chi_Minh).
- Đọc tài liệu linh hoạt: Hoàn tất code và kiểm chứng bước tài liệu. CSV tự tìm header trong 40 dòng đầu (giữ dòng vật lý), nhận comma/semicolon/tab/pipe và alias cột Việt/Anh; XLSX dùng chung aliases. Pipeline dùng Codex/Claude đã chọn để ánh xạ cột khi parser không hiểu, một lần/tài liệu, timeout90s, preview30k ký tự/40 dòng/64 cột/120 ký tự mỗi ô. AI chỉ trả tọa độ, loader kiểm sheet/dòng/cột bắt buộc/không trùng và lấy giá trị từ nguồn; giữ fill/strike/formula của XLSX. Không tự đoán workbook nhiều app. Static/none/max-tool-calls0 không gọi AI tài liệu. UI có Tài liệu đã đọc, report metrics.documents có phương pháp và usage. Backend chưa restart.
- Kiểm tra mới nhất:165/165 unittest đạt (7.438s; /tmp/apk-audit-flexible-documents-tests.log), frontendbuild đạt (/tmp/apk-audit-flexible-documents-build.log; cảnh báo chunk/use-client cũ), diffcheck đạt. CSV SmartZone working AI Learn66dòng/ADS MoneyTracker17placement và XLSX mẫu26placement/3disabled đều đọc trực tiếp, không gọi AI. Hai CSV thuộc hai app khác nhau, đã thông báo không dùng làm cùng hợp đồng audit.
- AI tài liệu thật: out/document-ai-live-smoke/report.json dùng dữ liệu giả lập, Sol6.1medium trả mapping thành công 8.856s,0tools,1placement. Report0rule là smoke bước tài liệu có chủ đích, không là kiểm ads APK. Usage20507input/77output theo CLI, không quy đổi chi phí. Claude mapping kiểm fake CLI, chưa live auth. Chưa có dropdown sheet hoặc đảm bảo semantic mapping mọi mẫu.
- Chẩn đoán XLSX Smart Zone: Hoàn tất đọc hai file thật, cả hai tái hiện lỗi nhiều sheet. ADS SCRIPTS có PA-SZI-1-AI Learn (24 placements), PA-SZI-2-Money Tracker (17), PA-SZI-3-Silly (24), cùng khớp header ở dòng 2. Working file có ba sheet cùng tên ứng dụng khớp mẫu; sheet Index cũng khớp tiêu chí Content/Detail hiện tại. Đây là giới hạn chọn sheet của parser, chưa phải bằng chứng file hỏng. Chưa chỉnh code/file đầu vào hoặc chạy audit. Hướng xử lý: chọn cùng sheet ứng dụng ở hai file, cần dropdown sheet trên web để không phải tách file thủ công; không tự đoán ứng dụng.
- Rà soát sẵn sàng triển khai: Hoàn tất đánh giá chỉ đọc, không sửa code chức năng. Chạy mới 151/151 unittest đạt (7.258s; /tmp/apk-audit-readiness-tests.log), rules check tại repo đạt 11 rule 0.4.0 và git diff --check đạt. Chưa chạy AI trả phí hoặc build/visual QA mới trong lượt rà soát.
- Vấn đề cần ưu tiên: CLI chạy từ /tmp trả thành công nhưng nạp pack empty/0 rule; loader phụ thuộc cwd và cấu hình wheel chỉ đóng gói apk_audit, chưa kèm rulepacks bên ngoài package. Cần đóng gói pack/reference, giải đường dẫn độc lập cwd và fail-fast khi thiếu pack. Local beta có thể dùng đường dẫn --rules tuyệt đối.
- Hiệu năng quan sát: Pilot 3 rule trước tinh chỉnh prompt cuối dành 1063.73/1082.31s (~98.3%) cho AI; context mỗi rule khoảng 87–89KB, vẫn chứa toàn bộ Documents và inventory. Ưu tiên lọc tài liệu theo rule, tái dùng bằng chứng chung, rút gọn repair/review và phân loại blocker tài liệu/code/runtime/engine trước khi điều tra thêm. Chưa có số đo tăng tốc cho bản tinh chỉnh cuối.
- Mục tiêu gần nhất: Dùng code base và AI đọc sâu để giảm UNKNOWN có thể xử lý. Trạng thái: Hoàn tất triển khai và kiểm chứng đại diện3rule; không đánh dấu full11rule hoặc toàn dự án đã hoàn chỉnh.
- Đã sửa: Snapshot portable11profile codebase e8f4337, filehash/commit và static goal/required paths/caveats riêng. Rule0.4.0 bỏ yêu cầu runtime ngoài phạm vi tĩnh; interoptional/openresume theo trạng thái tài liệu giữ nguyên; banner không ép Splashreload khi chưa có yêu cầu riêng. AI sửa excerpt/claim refs kể cả UNKNOWN qua catalog/source windows; một lượt điều tra blocker/tiếp tục khi phần budget đầu bị ngắt; giữ bounded read outputs ở Codex/Claude, finalguard/reviewFAIL vẫn bắt buộc. UNKNOWN lỗi cấu trúc/source không cache hoặc checkpoint reuse.
- Budget/hiển thị: Native rule mặc định35–45calls, phần đầu khoảng60% khi allocation>=20, vẫn trần toànlượt400. Prompt tách currentattemptallowance/ruletotal. Metrics/UI hiện repair/investigation/review và commitbase; không tự đổi model/effort.
- Kiểm tra mới:151/151unittest đạt (7.307s), frontendbuild/JScheck/rulescheck/diffcheck đạt; log/tmp/apk-audit-depth-tests-final.log và /tmp/apk-audit-depth-build.log. Không browservisualQA. Unit/replay chỉ chứng minh hợp đồng, không đo accuracyAPK.
- Pilot thật: out/audit-depth-validation/report/report.json; Sol6.1medium,3rule từngUNKNOWN →1PASS/1FAIL/1UNKNOWN,54tools,1082.31s,0verdictcache. RemoteConfigPASS8tools; LanguageFAIL20tools, reviewaccepted, thiếu offlinefallback trong rendernon-null (đã đọc lại source); IDUNKNOWN26tools/2attempts,6compliance+2uncertain vì hợp đồng CSV cũ/mới và AI mở scope quá rộng.
- Sau pilot: Siết IDquestion/profile/prompt về getter/alias→config.id→SDKload; không đòi remote snapshot hoặc render/navigation của rule khác. Làm rõ attemptbudget trong prompt. Pilot dùng snapshot3rule trước các tinh chỉnh này; không gán số đo đó cho bản prompt mới hoặc full11rule. Xem docs/audit-depth-validation.md.
- XLSX mẫu người dùng: /home/infinity01/Downloads/[PUB INFINITY x INNOVATIVE INSIDE] ADS SCRIPTS.xlsx. Người dùng xác nhận chỉ là mẫu, không cần đúng APK. Đọc26placement/23active/3disabled,2strike/1fill,0activeIDtrống,0unknown. open_resume disabled đúng. Không dùng IDs mẫu để chấm APK IPTV, không cần hỏi thêm file cho kiểm mẫu. Summary không ghi ID ở out/audit-depth-validation/xlsx-input-check.json.
- Vận hành/Git: Giữ feat/audit-optimization và mọi diff trước; chưa commit/push/restartserver hoặc sửa APK. Cần restart backend trước auditweb mới để nạp code/model. Báo cáo web cũ không tự đổi; pilot3rule ở thư mục riêng.
- Bước tiếp theo đề xuất: Sửa đóng gói/đường dẫn và context theo rule trước; benchmark tùy chọn 2 workers đã có với cùng đầu vào/model/cache. Sau đó bổ sung tiến độ live cho repair/investigation/review và hủy audit truyền tới CLI. Trước phát hành ổn định cần kiểm full 11 rule với hợp đồng thật, ca APK có kết luận chuẩn và cài/chạy ngoài repo trên máy mới. Chưa triển khai các đề xuất này trong lượt rà soát; runtime/SDK thiếu mã thật vẫn phải giữ UNKNOWN có lý do.

## 2026-11-26 09:45 — Cài đặt một chạm cho người không rành kỹ thuật (Asia/Ho_Chi_Minh)

- Mục tiêu: người dùng mới không phải gõ lệnh: tải ZIP, bấm đúp file cài, có biểu tượng trên màn hình chính; web tự kiểm tra công cụ thiếu và có nút cài.
- Đã làm: `apk_audit/setup_tools.py` (kiểm tra, cài portable Java Temurin 17/JADX/Node vào `user_data_path/apk-audit/tools` có kiểm SHA256, Claude qua trình cài chính thức, Codex qua npm prefix riêng; `activate()` thêm vào PATH/JAVA_HOME; `SetupJobs` chạy nền một lượt cài, danh sách công cụ cố định; mở terminal đăng nhập). `apk_audit/launcher.py` (tạo shortcut `.lnk`/`.command`/`.desktop`, phát hiện server đang chạy). CLI: `shortcut`, `serve --open`, gọi `activate()` đầu mọi lệnh. Web: `GET /api/setup/status`, `GET /api/setup/jobs/{id}`, `POST /api/setup/install|login/{tool}` (chặn Origin/Host không phải localhost). Engine gọi CLI qua `shutil.which` để Windows chạy được `codex.cmd`. Frontend: `SetupPanel.jsx`, `setupStatus.js` (+ test); panel lên đầu trang khi còn thiếu. README thêm mục Cài đặt nhanh.
- Kiểm tra: `uv run --extra mcp python -m unittest discover -s tests` 251 đạt; `node --test frontend/src/*.test.js` đạt; `npm run build` đạt. Cài thật trên Linux vào thư mục tạm: JADX 1.5.7, Temurin 17.0.21.1, Node 22.23.5 (SHA256 khớp), Codex qua npm; server thật trả status, từ chối Origin lạ và tên công cụ lạ.
- Chưa kiểm: script `.bat`/`.command` và shortcut trên Windows/macOS thật; trạng thái đăng nhập Claude dựa vào `claude auth status` (không xác định thì hiện "chưa xác định"); chưa tạo shortcut thật trên Desktop máy này.
- Bước tiếp theo: thử trên một máy Windows và một máy macOS sạch; đóng gói ZIP phát hành (GitHub Release); cân nhắc nút "Cập nhật tool".

## 2026-11-02 09:19 — Tạo CLAUDE.md (Asia/Ho_Chi_Minh)

- Mục tiêu: Tạo `CLAUDE.md` hướng dẫn Claude Code làm việc trong repo (lệnh, kiến trúc).
- Trạng thái: Hoàn tất.
- Đã làm: Đọc README, `docs/technical-reference.md`, `pyproject.toml`, `frontend/package.json`, `cli.py`, `pipeline.py`; tóm tắt lệnh chạy/test và luồng unpack → facts → documents → inventory → preflight → rules → agent → cache → report.
- File thay đổi: `CLAUDE.md` (mới), `SESSION_LOG.md`.
- Kiểm tra: Không chạy test/build vì không sửa mã chức năng; đã xác nhận tên test mẫu `tests.test_slicer.SlicerTests` tồn tại.
- Bước tiếp theo: Giữ nguyên các việc còn lại ở mục 2026-10-23 10:22.

## 2026-10-23 10:22 — Đề xuất tối ưu bằng chứng và lượt gọi AI (Asia/Ho_Chi_Minh)

- Mục tiêu: Đề xuất phương án cho hai vấn đề bằng chứng không được chấp nhận và token/thời gian qua nhiều lượt xử lý.
- Trạng thái: Hoàn tất đề xuất; chưa triển khai mã.
- Đã làm: Đọc schema, verifier, prompt/repair/review và claim/verification thật của ba UNKNOWN Claude; đối chiếu số lần gọi Codex đã lưu.
- Đính chính: `unverified_claims` của INIT chứa applicability SDK chưa rõ; SPLASH thiếu runnable fail-safe và layout XML; ONBOARDING có blocker full2 ngoài phạm vi chưa phân định. Không thể mặc định các UNKNOWN này chỉ là lỗi định dạng rồi tự chuyển PASS.
- Phương án: (1) xác định requirement_id, phạm vi và applicability từ hợp đồng/tài liệu có căn cứ; bổ sung layout/helper đích vào gói đọc, không chia mỗi requirement thành một request; (2) catalog evidence ổn định và backend điền file/range, AI chọn evidence_id, bằng chứng mới vẫn phải lấy từ code và kiểm; (3) tách lỗi tham chiếu với thiếu mã/thông tin thật, patch giới hạn cho phần cần sửa rồi merge+verify toàn bộ; (4) giữ review độc lập cho FAIL nhưng thu gói đầu vào về vi phạm, gate/callback, điều kiện, fallback và yêu cầu liên quan, cho phép đọc thêm khi thiếu.
- Ràng buộc: PASS chỉ khi đủ mọi yêu cầu bắt buộc; blocker trong phạm vi vẫn UNKNOWN. Không tự suy optional/không áp dụng từ việc không tìm thấy, không sửa hoặc đoán semantic/code bằng máy. Các thay đổi schema/catalog cần tăng policy và vô hiệu cache cũ; cache mọi đoạn code cấp sẵn cần theo dõi phụ thuộc đầy đủ.
- Kiểm tra: Chỉ phân tích chỉ đọc; không chạy AI/test/build mới vì không sửa chức năng. Mốc test/build của phiên 09:34 vẫn là kết quả đã chạy gần nhất.
- File thay đổi: SESSION_LOG.md.
- Bước tiếp theo: Khi có yêu cầu triển khai, ưu tiên scope và gói đọc trước, sau đó catalog/patch/review; benchmark cùng APK/docs/model/scope/cache trên bộ ca đã được Dev đối chiếu. Các mục tiêu giảm token/thời gian là tiêu chí thử nghiệm, chưa là kết quả đã đạt.

## 2026-10-23 09:34 — Đánh giá hoạt động, token và thời gian (Asia/Ho_Chi_Minh)

- Mục tiêu: Đánh giá chất lượng hoạt động và mức tối ưu token/thời gian hiện tại.
- Trạng thái: Hoàn tất trong phạm vi đánh giá; các đề xuất chưa triển khai.
- Đã làm: Đọc pipeline, slicer, agent, scheduler, cache, benchmark và số đo/report đã lưu; chạy kiểm thử và build. Không gọi AI hoặc audit APK mới.
- Kiểm tra: Trong sandbox 241 test có 15 lỗi do MCP timeout/socket bị chặn. Chạy lại ngoài sandbox: 241/241 đạt trong 9,742s (`/tmp/apk-audit-assessment-tests-unrestricted.log`). Build Vite đạt trong 4,11s (`/tmp/apk-audit-assessment-build.log`), cảnh báo import `falloff` không tồn tại nhưng không dùng và bundle 1,64MB; node runner báo 3 file test đạt nhưng có cảnh báo `Failed to create stream fd` nên không dùng kết quả này để khẳng định số assertion chạy. Git sau build chỉ thay đổi SESSION_LOG.md.
- Bằng chứng hoạt động: Hai report `06ff1746` (Claude) và `c91c3df3` (Codex) cùng APK, inventory, rulepack và policy: 7PASS/2FAIL/5UNKNOWN trong 206,1s/54 tools so với 4PASS/7FAIL/3UNKNOWN trong 249,8s/75 tools. Bất đồng ở kết luận AI, không có ground truth để chọn bên đúng. Lượt Claude có 4 repair/1 investigation; Codex 1 repair/5 review/3 investigation.
- Token: Codex `c91c3df3` 4.296.958 input (3.566.720 cached nằm trong input), 58.678 output. Claude `06ff1746`: 90 input mới, 294.985 cache write, 1.737.305 cache read, 57.195 output; cách ghi input hai CLI khác nhau, không cộng cached Codex lần nữa hoặc quy đổi trực tiếp sang chi phí/hạn mức. Source slice, scope tài liệu, static rule, 6 workers, session resume và cache đều đã có trong mã hiện tại.
- Thời gian: AI/rules chiếm 91,4% (`06ff1746`), 93,0% (`c91c3df3`), 93,1% (`b28b6ced`), 96,5% (`9788a153`). Riêng CROSS_FLOW ở `9788a153` 219s, 1.248.085 input, 3 attempts. Tổng report cuối là 585,7s, không phải 565s (đó là thời gian rules). So slicer cũ không hợp lệ làm A/B do khác scope/cache; cả hai report Short Drama còn cảnh báo tài liệu App ID lệch nên không dùng làm ground truth.
- Phát hiện cache: `dependency_paths` chỉ thu evidence và sự kiện source_read, không thu đầy đủ file trong source_slice/evidence_bundle/flow_map. PoC tạm tạo A/B cùng cây đường dẫn: A được dẫn chứng, B ở prompt; đổi B nhưng ScopedIndex.find vẫn trả verdict cũ. Đây là tái hiện cơ chế tổng hợp, chưa chứng minh một verdict APK thật đã sai vì cache. Khóa cache thường chỉ có SLICE_VERSION=1, không có hash mã slicer nên đổi thuật toán mà không tăng phiên bản có thể reuse kết quả cũ.
- File thay đổi: SESSION_LOG.md. Không chỉnh code, cache thực tế hoặc server; không commit/push.
- Việc còn lại / bước tiếp theo: Ưu tiên tính đủ phụ thuộc cache và phiên bản slicer; đối chiếu thủ công bộ APK có kết luận chuẩn; benchmark cố định APK/docs/model/scope/cache; giảm repair bằng chuẩn hóa bằng chứng, thu gọn payload follow-up và review trong khi giữ cổng kiểm chứng.

## 2026-10-23 09:20 — Giải thích mục đích và trạng thái dự án (Asia/Ho_Chi_Minh)

- Mục tiêu: Cho biết dự án đang làm gì.
- Trạng thái: Hoàn tất trong phạm vi giải thích.
- Đã làm: Đọc hướng dẫn, trạng thái/nhật ký gần nhất, README, pipeline, báo cáo, unpack và bộ luật; kiểm tra Git tại máy.
- Kết quả: Công cụ local kiểm tích hợp quảng cáo Infinity trong APK/XAPK/APKM, đối chiếu ADS SCRIPTS/working file và chuẩn base bằng rule tĩnh kết hợp AI; xuất báo cáo Marketing/Dev. HEAD `1c6566f`, pack `0.11.1`, 17 rule.
- File thay đổi: `SESSION_LOG.md`; không sửa mã chức năng.
- Kiểm tra: Git sạch trước khi ghi nhật ký; chỉ đọc mã, không chạy lại test/build/audit AI; không kiểm tra server hoặc remote.
- Việc còn lại: Độ chính xác kết luận trên app thật cần tiếp tục đối chiếu; phân tích tĩnh không xác nhận quảng cáo hiển thị khi chạy.
- Bước tiếp theo: Chờ yêu cầu hiện tại tiếp theo của người dùng; không tự khởi chạy audit từ nhật ký.

## 2026-10-22 (chiều) - Đối chiếu A/B slicer, README chạy local, khớp tên theo ID

- Mục tiêu: so slicer có/không tweak, viết README cho Marketing tự cài chạy local, giảm "Cần dev xem lại".
- Kết quả A/B (AI Short Drama, Codex gpt-6-sol low): tweak 4.99M token/272 s; baseline 6.16M/566 s nhưng có thêm CROSS_FLOW và Language chạy thật. Chênh lệch nằm trong dao động giữa các lần chạy, không chứng minh tweak có ích. Giữ baseline; đã xóa nhánh `exp/graphify-call-graph` và worktree.
- Nguyên nhân UNKNOWN thật: Welcome UNKNOWN vì ADS SCRIPTS là CSV nên `open_resume` không rõ đang dùng (chính sách có chủ đích). ID UNKNOWN là reviewer hạ FAIL hợp lệ.
- Sửa: `placement_policy.config_key` khớp tên gõ sai trong tài liệu (`ative_` so với `native_`) khi cùng ID, cùng số vị trí, ảnh khuyết duy nhất; Marketing giải thích UNKNOWN của Welcome do CSV. Thêm `tests/test_placement_policy.py`. 241 test pass.
- README: viết lại mục cài đặt cho từng máy chạy local (chưa có server chung).
- Chưa làm: giảm token ở lượt repair (gửi chỉ phần sửa khi resume). Chưa commit các thay đổi sau `ba16fc4`.

## Lịch sử phiên

### 2026-10-22 17:30 — Đưa slicer về bản KHÔNG có tweak để so sánh A/B (Asia/Ho_Chi_Minh)

- Theo yêu cầu: `git restore` apk_audit/slicer.py về HEAD (WHOLE_FILE_LINES không tồn tại, ngưỡng nguyên file 130 dòng), 239 test đạt, restart server. Mốc "CÓ tweak" cùng app AI Short Drama (Codex gpt-6-sol low, pack 0.11.1): job b28b6ced54504a5f9cafdc1500ade867 — 7P/5F/2U, 272s, 4.99M in, 66K out, 67 calls; lệnh mỗi rule INIT 6, REMOTE 8, ID 11, SPLASH 16, ONBOARDING 13, WELCOME 13 (Language dùng cache). Khóa verdict cache KHÔNG chứa nội dung slice nên chạy lại cùng app sẽ dùng lại kết quả PASS/FAIL đã lưu (không phải A/B thật): đã chuyển `out/web/cache/verdicts` → `verdicts.backup-with-tweak` (đổi tên lại để khôi phục). Chờ người dùng chạy lại bản KHÔNG tweak rồi so với job mốc.

### 2026-10-22 16:50 — Áp dụng cải tiến slicer từ nhánh thử nghiệm vào server (Asia/Ho_Chi_Minh)

- Theo yêu cầu "áp dụng vào server để chạy thử": lấy riêng `apk_audit/slicer.py` (WHOLE_FILE_LINES=60) từ `exp/graphify-call-graph` vào working tree của main (chưa commit), 239 test đạt, restart server. Graphify KHÔNG được tích hợp vào pipeline (đánh giá: không hiệu quả). Hoàn tác: `git checkout main -- apk_audit/slicer.py` rồi restart.

### 2026-10-22 16:30 — Thử nghiệm Graphify trên nhánh riêng (Asia/Ho_Chi_Minh)

- Tạo worktree `../apk-audit-graphify` trên nhánh `exp/graphify-call-graph` (main và server đang chạy không bị đụng). Xác minh gói `graphifyy` 0.9.93 (metadata trỏ đúng repo Graphify-Labs/graphify, 261 bản phát hành), cài trong venv của worktree, không chạy `graphify install`.
- Đo trên app Silly: dựng 4m23s, 222.567 nút/638.560 cạnh, graph.json 256MB; ghi vào `<sources>/graphify-out` trong workspace cache (đã dọn, workspace sạch). Độ sâu 1 từ Language/Onboarding chứa đủ các lớp AI từng phải tự đọc (cx1, bx1, j5, ex1; o12, rn1) nhưng slicer hiện có với ngân sách không giới hạn cũng tìm đủ ⇒ Graphify không thêm khả năng phát hiện; điểm nghẽn là xếp hạng/nén dưới ngân sách ~25KB. Độ sâu 2 nổ 6–9 nghìn file.
- Kết luận: không hiệu quả để tích hợp; giữ nhánh để tham chiếu, tài liệu ở `docs/graphify-evaluation.md` trên nhánh (commit 84502ee). Thay đổi nhỏ có ích (`WHOLE_FILE_LINES`=60: helper dài chỉ góp hàm liên quan quảng cáo; Language 3/4 lớp cần thay vì 2/4) mới nằm trên nhánh, chưa vào main. Cách hủy: `git worktree remove ../apk-audit-graphify && git branch -D exp/graphify-call-graph`.

### 2026-10-22 15:40 — Giao diện: Three.js theo con trỏ + font nét đều (Asia/Ho_Chi_Minh)

- Font: Poppins không có glyph tiếng Việt nên dấu bị rơi sang font hệ thống → nét to nhỏ lẫn lộn. Thay bằng **Be Vietnam Pro** (nét đều, thiết kế cho tiếng Việt), 3 subset (latin, latin-ext, vietnamese) × 4 độ đậm 400/500/600/700 dạng woff2 bundle trong web_assets/fonts (224KB, OFL.txt), `unicode-range` chuẩn, route mới ở web.py, antd token + :root; font-synthesis none.
- Three.js (`three` 0.186 + `@fontsource/be-vietnam-pro` trong frontend): `PointerField` nền cố định click-through — lưới chấm ShaderMaterial tản ra/lớn lên quanh con trỏ (làm mượt theo dt) + vầng sáng spotlight; `TiltGem` khối icosahedron wireframe ở thanh bên xoay hướng theo chuột. Cap DPR 1.5, dừng khi tab ẩn (rAF), dispose khi unmount, bỏ qua chuyển động nếu prefers-reduced-motion, im lặng nếu không có WebGL. Card kính mờ (rgba .84 + blur 3px) để thấy nền.
- Lỗi bắt được khi kiểm: CSP `default-src 'self'` chặn `data:` nên favicon canvas của animation tab sẽ không chạy → thêm `img-src 'self' data:; font-src 'self'`. Server phải restart mới nạp route font (đã restart).
- Kiểm bằng Chrome headless (CDP, giả lập di chuột, 1440×900): hiện đúng chấm tản/đậm quanh con trỏ và vầng sáng, gem 3D, đã nạp 7 face Be Vietnam Pro, không lỗi console. 6 test node + test web font/CSP. app.js 1.64MB. Chưa commit.

### 2026-10-22 15:00 — Làm rõ ô tùy chọn trên web (Asia/Ho_Chi_Minh)

- Người dùng hỏi các ô tick để làm gì. Phát hiện chữ giao diện cũ: dòng "Claude cố định Haiku 5.5 / low" sai (engine hiện là Sonnet 5; lần đổi trước sed nhầm dòng) → nay lấy tên model từ danh sách engine; ô "Kiểm lại cả rule đã đạt (… Firebase tracking)" vô nghĩa sau khi gỡ rule Firebase → bỏ khỏi UI (CLI `--recheck-all` còn); viết lại mô tả 2 ô còn lại (Kiểm đầy đủ cho dev ≈ +20% token; Rà lỗi chéo chậm ~5 phút). Build đạt, chưa commit.

### 2026-10-22 14:40 — Animation trên tab trình duyệt khi audit chạy (Asia/Ho_Chi_Minh)

- `frontend/src/tabIndicator.js`: hook `useTabIndicator` — khi audit chạy, tiêu đề tab quay spinner braille (⠋⠙⠹…) kèm tiến độ "3/7" và favicon canvas 32px có cung sáng quay (120ms; tab nền bị trình duyệt giãn ~1s vẫn quay); xong ✅ xanh, lỗi ⚠️ đỏ, chờ xác nhận tài liệu ❔ vàng; tôn trọng `prefers-reduced-motion` (tĩnh). Có test node (tabTitle). Build đạt, file tĩnh phục vụ từ đĩa nên không cần restart. Chưa xem trực quan trên trình duyệt; chưa commit.

### 2026-10-22 14:10 — Preflight tài liệu có đúng app không (Asia/Ho_Chi_Minh)

- Yêu cầu: dừng và hỏi xác nhận trên web khi package/tài khoản AdMob tài liệu lệch app, trước khi tốn AI. `apk_audit/preflight.py` (`check_documents`: package_match False, app_id_match False, tài khoản AdMob không giao nhau giữa ID active của ADS SCRIPTS và ad_config.json, bỏ qua ID demo Google; `DocumentMismatch` mã 7). Pipeline kiểm sau inventory, trước slice/rule; `confirm_mismatch`; engine none không chặn; báo cáo có `preflight` + cảnh báo `documents_may_not_match_app` khi đã xác nhận. Web: trạng thái `awaiting_confirmation` (không giữ slot active), `POST /api/jobs/<id>/confirm|cancel`; UI Alert + 2 nút, lịch sử "Chờ xác nhận tài liệu". CLI `--confirm-mismatch`.
- Kiểm trên job cũ: Silly (96ec2ada) và AI Learn (837e1e00) sẽ bị chặn (App ID + tài khoản lệch); app huyết áp (02754ccc) OK — nhận định trước "cả hai lượt đều lệch" chỉ đúng với Silly và AI Learn. 238/238 test (thêm test_preflight, pipeline, luồng web); build; server restart. Chưa commit.

### 2026-10-22 13:10 — Job 454e5fb8 (Claude Sonnet 5 low, Silly) và sửa báo oan REMOTE_FALLBACK (Asia/Ho_Chi_Minh)

- Kết quả: 8 PASS / 3 FAIL (static CONFIG_FLAGS, DEBUG_TEST_IDS + AI REMOTE_FALLBACK) / 3 UNKNOWN (DEV_TOGGLE, INTERVAL obfuscated; WELCOME unverified_claims), 308s, 60 tool calls, cache read 2.47M, cache write 0.42M, output 97K. Lệnh mỗi rule AI: INIT 2, ID 5, SPLASH 5, ONBOARDING 10, LANGUAGE 11, REMOTE 11, WELCOME 16 (TB 8.6); 5/7 rule vẫn cần 1 lượt sửa nối tiếp (conf trung bình). So Codex cùng app (96ec2ada): Codex 4 màn UNKNOWN, Claude 3 PASS + 1 UNKNOWN; bất đồng chỉ ở REMOTE (Codex PASS, Claude FAIL).
- Phát hiện: REMOTE_FALLBACK FAIL của Claude ("hardcode RELEASE_FILE_NAME, DEBUG_FILE_NAME không dùng") là báo oan trên APK release: base dùng `if (BuildConfig.DEBUG)` nhưng trình biên dịch gập DEBUG=false nên nhánh debug bị loại khỏi release APK. Cùng kiểu kết luận đã xuất hiện ở các app trước. Sửa: `code_profile.build` (debug nếu manifest có android:debuggable="true", còn lại release), AI nhận build trong code_profile + prompt claims-review-15 (release: vắng nhánh debug không phải lỗi, chỉ FAIL nếu release đọc nhầm file debug hoặc không đọc ad_config.json), câu hỏi rule REMOTE bổ sung; pack 0.11.1. Slicer default-package cũng đã nạp (restart xong). 232/232 test.

### 2026-10-22 12:40 — Vì sao Claude vẫn 10–17 lệnh (Asia/Ho_Chi_Minh)

- Quan sát job 454e5fb8 (Claude, Silly) đang chạy: mỗi rule 6–8 lệnh ở lượt đầu, thêm sửa/review lên 10–17. Lệnh là Grep/Read vào `sources/defpackage/*` (cx1, bx1, j5, ex1, o12, rn1…): lớp helper của R8 nằm ở package mặc định, được gọi bằng tên trần không có import nên slicer chưa lần tới.
- Sửa (chưa nạp vào server vì job đang chạy): slicer nhận diện lớp default package (`sources/defpackage/*`, `sources/*.java`), theo token tham chiếu trần trong hàm đã chọn, hop 2 bước, hạ hạng file registry cấu hình (nhiều tên vị trí) cho rule màn hình, điểm file helper nhỏ 12. Đo slice trên app Silly: Language nay chứa cx1, bx1 (AI từng đọc cx1/bx1/j5/ex1) nhưng chưa đủ (j5, ex1 thiếu); onboarding/splash chưa chứa o12/rn1 — ngân sách ký tự bị nhiều file ngắn tên giống nhau chiếm. 231/231 test. Cần restart khi job xong.

### 2026-10-22 12:10 — Kiểm job 96ec2ada (Silly, Codex GPT-6 Sol low, pack 0.11.0) (Asia/Ho_Chi_Minh)

- Kết quả: 6 PASS / 2 FAIL (static) / 6 UNKNOWN, 186s, input 5.29M (cache 4.68M), output 67K, 74 tool calls — so với job 0fd0c7af (cùng app, trước slice/scope): 295s, 8.64M, 104K, 115 calls ⇒ -37% thời gian, -39% token vào, -36% lệnh. Phạm vi đúng (7 rule AI core; không chạy GATES/BANNER/CROSS). Lệnh mỗi rule vẫn 6–15 (mục tiêu 2–4 chưa đạt với Codex low; Claude đo 0–5).
- 4 màn đều UNKNOWN: Splash/Onboarding do 1–2 evidence trượt làm vô hiệu claim violation; Language claim bị `applicability_not_proven/unresolved_blocker`; Welcome `review_unknown` (thiếu WelcomeActivity). INIT/REMOTE/ID đều PASS.
- Lỗi phát hiện: screen_report của rule bị hạ UNKNOWN vẫn hiện ✅/❌ và `verified=True` (tính lúc apply theo draft FAIL). Đã sửa trong `_gate_and_grade`: UNKNOWN ⇒ mọi ok/issue → unknown, verified=False.
- Cải tiến thêm: slice truyền dạng văn bản thô ngoài JSON envelope (SLICE_MARK) để model đọc mã thật thay vì chuỗi bị escape. 231/231 test; server restart. Chưa commit. Đề xuất chờ duyệt: bỏ evidence trượt nhưng giữ claim còn đủ ≥2 vai trò; dùng Claude cho 4 màn.

### 2026-10-22 11:30 — Phạm vi đọc hẹp + trích mã sẵn (slice) (Asia/Ho_Chi_Minh)

- Yêu cầu: AI chỉ đọc khởi tạo, remote/consent/fallback/ID và 4 màn đầu; đưa sẵn hàm quan trọng vào prompt để cần 2–4 lệnh thay vì 12–18.
- Đã làm: `apk_audit/slicer.py` (parse method bằng đếm ngoặc bỏ qua chuỗi/comment; seed theo vùng: Application class, file chứa literal Remote/consent/ID, Activity màn trong manifest + sibling + file chứa tên/getter vị trí của màn; chấm điểm theo literal vị trí, getter Kotlin, API ads, lifecycle; 1 bước gọi `X.m(` và `new X(`; bỏ thư viện, giữ code app/obfuscated; file ≤40 dòng lấy nguyên; ngân sách ký tự theo vùng; ghi "KHÔNG CÓ MÃ" khi manifest khai báo Activity mà JADX không xuất file — app huyết áp thiếu WelcomeActivity.java). Pipeline thêm `source_slice` vào context (bundle gợi ý giảm còn 5000), prompt claims-review-14. Rule `tier: full` cho LOAD_OBSERVE_GATES và BANNER_RELOAD (cần `--full`/ô web "Kiểm đầy đủ"); ngân sách lệnh INIT 20, ID 20, REMOTE/SPLASH/LANGUAGE/ONBOARDING 26, WELCOME 24; pack 0.11.0. MAX_RANGE_LINES 20→40 (AI hay trích 23 dòng); lượt sửa cũng kích hoạt khi `incomplete_path`.
- Đo live Claude Sonnet 5 low trên app huyết áp (từng rule): Language 12→4 lệnh (PASS), Welcome 3 lệnh (UNKNOWN do thiếu file Welcome), Onboarding 0–3 lệnh (PASS sau 1 repair resume), Remote fallback 5 lệnh/4 lượt (FAIL). Replay: prompt 7 rule core ~62KB/rule (lớn hơn trước) nhưng ít lệnh hơn nên tổng token nhỏ hơn; chưa đo toàn lượt Codex.
- Test: 227/227 + test_slicer; build; server restart. Chưa commit.

### 2026-10-22 — Rà trạng thái (Asia/Ho_Chi_Minh)

- Người dùng hỏi đã triển khai tới đâu và cần làm gì. Kiểm: remote HEAD (SSH) = 1446c4a; fetch HTTPS lỗi "Repository not found" (repo private, cần đăng nhập); web server không chạy nên đã khởi động lại (HTTP 200). Cập nhật phần Trạng thái hiện tại. Không đổi code.

### 2026-10-21 20:10 — Alias tên placement (Asia/Ho_Chi_Minh)

- Báo oan: tài liệu ghi `inter_welcome_back`, app (ad_config + ad_config_debug) dùng `inter_welcome` nên báo "Thiếu". Thêm `PLACEMENT_ALIASES`/`config_key` (placement_policy.py): inventory so sánh theo tên của app, marketing hiện một dòng "Đúng ID (app đặt tên inter_welcome)", ADS_CONFIG_FLAGS cũng ghép theo alias. Vị trí cùng họ khác chỉ số (fullscreen_1_2 vs 1_3/1_4 của app huyết áp) giờ báo "Chưa khớp tên … cần xác nhận cùng vị trí" kèm danh sách `candidates`, không còn "Thiếu". Trên job 4f31f8ec: ID có vấn đề 3 → 2 (chỉ còn hai fullscreen_*_2 cần xác nhận tên). 227/227 test; server restart. Chưa commit.

### 2026-10-21 19:40 — Cổng chặn báo oan cho rule AI và độ tin cậy (Asia/Ho_Chi_Minh)

- Yêu cầu: hạn chế bắt lỗi nhầm ở cả các rule AI/sau này nhưng vẫn chính xác, đáng tin.
- Đã làm: (1) claim có `basis` bắt buộc (defect_present | behavior_absent | not_applicable); prompt giải thích, claim violation chỉ dựa trên "không thấy" chỉ dùng khi tên không bị đổi. (2) `agent._gate_and_grade`: FAIL chỉ giữ nếu có ≥1 claim violation hỗ trợ verdict với defect_present, hoặc code_profile sạch (làm rối thấp, 0 file app lỗi); ngược lại hạ UNKNOWN reason `absence_not_conclusive` (giữ "AI nghiêng về…"); replay cũ không có basis coi là defect_present; không có profile (offline) giữ nguyên. (3) Reviewer: claim behavior_absent phải tự tìm lại bằng chuỗi/hằng số/import, nếu mã làm rối/lỗi giải mã mà chưa có chứng cứ hành vi sai thì hạ uncertain. (4) Độ tin cậy cao/trung bình/thấp cho cả rule AI (verification.confidence): cao = không phải sửa/điều tra, trung bình = có sửa bằng chứng/điều tra hoặc lỗi chỉ dựa trên vắng mặt khi mã làm rối, thấp = UNKNOWN; static dùng cao/thấp; hiển thị ở tab Dev, report.md, HTML; Marketing ghi "(nên dev xác nhận)" khi ❌ trung bình. rule_policy có absence_gate để cache đúng. claims-review-13-fail-gate.
- Kiểm: 224/224 test (thêm 3 test gate/confidence); build đạt; server restart. Chưa chạy AI thật với prompt/schema mới; chưa commit. Ý tưởng tiếp: nút "Đánh dấu báo oan" lưu phản hồi để hiệu chỉnh/loại trừ ở lượt sau.

### 2026-10-21 19:00 — Chuẩn hóa kết luận với APK bị làm rối (Asia/Ho_Chi_Minh)

- Yêu cầu: hạn chế báo oan/cảm tính vì input là APK giải mã chứ không phải mã nguồn rõ.
- Nguyên tắc: chuỗi ký tự, manifest, asset JSON không bị đổi tên → căn cứ chắc; vắng một TÊN hàm chỉ là lỗi khi mã ít làm rối và không có file giải mã lỗi. `rules/code_facts.py`: `code_profile` (tỉ lệ tên lớp ≤2 ký tự → làm rối thấp/vừa/cao; file của app có "Code restructure failed|Method dump skipped|…"; thư viện không tính), `app_roots` (package manifest + package Application class), `absence_is_conclusive`. Áp dụng: REMOTE_KEYS (thiếu chuỗi + file app giải mã lỗi → UNKNOWN decompile_gaps), INTERSTITIAL_INTERVAL và LANGUAGE_DEV_TOGGLE (vắng tên hàm: FAIL chỉ khi làm rối thấp, còn lại UNKNOWN obfuscated). Mọi rule tĩnh ghi `verification.basis/limits/confidence`; Dev view/report.md hiện "Căn cứ"; `report.code_profile` + cảnh báo trong tab Dev khi làm rối ≠ thấp hoặc có file lỗi. AI nhận `code_profile` trong context + prompt claims-review-12 (không FAIL chỉ vì mất tên hàm, lần theo chuỗi/hằng số/import).
- Kiểm: 221/221 test (thêm 2 test); trên app huyết áp: CONFIG_FLAGS/DEBUG_TEST_IDS FAIL (confirmed), REMOTE_KEYS PASS, SCREEN_NAMES/ORIENTATION PASS, DEV_TOGGLE và INTERVAL UNKNOWN (inconclusive, làm rối cao 48%, 0 file lỗi trong app). Chưa kiểm AI với prompt mới; chưa commit.

### 2026-10-21 18:00 — Đọc job f19b53b6 (Sonnet 5 low), sửa UI và báo oan rule tĩnh (Asia/Ho_Chi_Minh)

- Job f19b53b6 (com.blood.pressure…, Claude Sonnet 5 low, 6 workers): 9 PASS / 5 FAIL / 2 UNKNOWN, 323s (rules 262s), 139 tool calls, cache read 3.73M, cache write 459K, output 105K; AI rules 9/9 gần hết 1–3 lượt (resume dùng ở 7 rule). Tốt nhất từ trước tới giờ. Job f8864b4b bị gián đoạn do restart server đúng lúc người dùng bấm chạy.
- Phát hiện báo oan của rule tĩnh với app này (applicationId com.blood… nhưng code ở com.itg.template, mã bị làm rối): ADS_REMOTE_KEYS FAIL (thực tế đủ 4 key trong com/itg/template), ADS_INTERSTITIAL_INTERVAL UNKNOWN, ADS_LANGUAGE_DEV_TOGGLE FAIL (thực tế tvTitle.setOnTouchListener của lib devconfig bị đổi tên). Đã sửa: quét toàn bộ sources thay vì chỉ thư mục package manifest; dev toggle không thấy tên hàm mà có listener trên tiêu đề + thư viện devconfig → UNKNOWN reason `obfuscated`; interval ghi chú tên hàm có thể bị làm rối. Kiểm lại trên app: REMOTE_KEYS PASS, DEV_TOGGLE UNKNOWN(obfuscated), INTERVAL UNKNOWN.
- Giữ nguyên các FAIL thật: ADS_DEBUG_TEST_IDS (ad_config.json release có 9 placement dùng ID demo Google), ADS_CONFIG_FLAGS (banner_home/native_home isEnable false trong khi ADS SCRIPTS active; inter_onboarding enable_ua_check true), REMOTE_FALLBACK FAIL (AI: AdRemoteConfig.initialize bỏ qua json, luôn fromAssets release).
- UI: khung "Logic hiện tại" bị nền xanh đậm do media query dark-mode trong khi app giao diện sáng → chữ đen khó đọc; đã bỏ media query, nền sáng #f0f5ff chữ đậm. 219/219 test; server restart. Chưa commit.

### 2026-10-21 17:15 — Claude đổi sang Sonnet 5 low (Asia/Ho_Chi_Minh)

- Theo yêu cầu: Claude `claude-haiku-5-5` → `claude-sonnet-5` (low; id `claude-sonnet-5-0` không tồn tại, `claude-sonnet-5` trả OK). 218/218 test, build đạt, server restart; nhãn Haiku/Sonnet 5.5 giữ cho báo cáo cũ. Chưa đo chất lượng/token; chưa commit.

### 2026-10-21 17:00 — Claude đổi sang Haiku 5.5 low (Asia/Ho_Chi_Minh)

- Theo yêu cầu (tiết kiệm token): Claude `claude-sonnet-5-5` → `claude-haiku-5-5` (effort low). claude_engine.py, cli help, README, UI (nhãn Sonnet giữ cho báo cáo cũ), 3 test. Kiểm `claude -p --model claude-haiku-5-5` trả OK. 218/218 test, build đạt, server restart. Lưu ý: lần thử Haiku cũ (20/10, prompt/evidence cũ) cho 0 PASS/2 FAIL/9 UNKNOWN; định dạng evidence mới chưa kiểm với Haiku. Cache Claude Sonnet không dùng lại. Chưa commit thay đổi này (nhánh feat/readable-fast-cheap-audit đã push f637e3b).

### 2026-10-21 16:30 — Viết lại README, commit và push (Asia/Ho_Chi_Minh)

- README mới ngắn gọn cho MKT và Dev (dùng nhanh, đọc báo cáo, công cụ kiểm tra gì, cài đặt, dòng lệnh, chọn AI/tiết kiệm token, giới hạn). README cũ giữ nguyên nội dung tại docs/technical-reference.md. Commit toàn bộ thay đổi của nhánh feat/readable-fast-cheap-audit và push theo yêu cầu người dùng.

### 2026-10-21 16:00 — Onboarding/Welcome thiếu thông tin: do quota và hết ngân sách lệnh (Asia/Ho_Chi_Minh)

- Job cf299856 (IPTV, Codex gpt-6-sol low): 6 PASS / 2 FAIL / 8 UNKNOWN, 163s, input 2.54M (cache 2.17M), output 34K (rất thấp so với lượt 6.1: 13.3M) NHƯNG: 5 rule AI dính "usage limit" (Welcome engine_error, Onboarding repair_error, Splash review_error, Load/observe, Banner) và 3 rule tool_budget (INIT 36/35, REMOTE 41/40, ID 36/35). Nên Onboarding/Welcome không có evidence/logic/checklist trong báo cáo.
- Nguyên nhân tool_budget: prompt "≤120 dòng/lệnh" làm gpt-6-sol dùng gấp đôi số lệnh (252 so với 113). Đã đổi thành gộp nhiều đoạn vào một lệnh (sed -n "a,bp;c,dp"), 150–300 dòng/lệnh, dành lệnh cuối trả JSON. claims-review-11-batched-reads.
- Đã làm: rule có checklist luôn trả `screen_report` (placeholder: ❔ khi AI lỗi, ➖ khi bỏ qua theo tài liệu) nên 4 màn luôn đầy đủ như nhau; marketing giải thích riêng khi hết hạn mức ("chạy lại sau khi hạn mức làm mới, rule đã xong được dùng lại") hoặc lỗi gọi AI; dev view nhãn quota; cảnh báo `engine_quota_exhausted` trong report. 218/218 test; server restart. Chưa kiểm live; chưa commit.
- Chưa làm: tự dừng sớm toàn lượt khi gặp quota (hiện từng rule tự lỗi); cân nhắc tăng ngân sách lệnh cho INIT/REMOTE/ID nếu vẫn hết.

### 2026-10-21 15:20 — Codex đổi sang gpt-6-sol low (Asia/Ho_Chi_Minh)

- Theo yêu cầu: model Codex `gpt-6.1-sol` → `gpt-6-sol` (vẫn effort low). Đã kiểm `codex exec --model gpt-6-sol` trả OK. engines.py, cli help, README, UI (nhãn cũ 6.1 giữ cho báo cáo cũ), 2 test. 216/216 test, build đạt, server restart. Cache Codex cũ không dùng lại (engine identity đổi). Chưa đo chất lượng gpt-6-sol; chưa commit.

### 2026-10-21 15:00 — Bù đánh đổi evidence theo đoạn dòng bằng review có mã thật (Asia/Ho_Chi_Minh)

- Chọn phương án tối ưu nhất trong các cách bù (anchor dài hơn / hai anchor / review đọc mã thật): review FAIL nhận `source_text` = mã thật tool lấy từ line..end_line cho mọi evidence (không tốn thêm lệnh đọc), REVIEW_PROMPT yêu cầu loại claim mà dòng được dẫn không thể hiện kể cả khi anchor khớp; prompt yêu cầu anchor của violation ≥12 ký tự đặc trưng. Không thêm lượt AI hay tiêu chí cứng mới nên không tạo thêm lượt sửa. PROMPT_POLICY claims-review-10-source-review.
- 216/216 test (thêm test reviewer nhận source_text, không còn excerpt do AI viết); server restart. Chưa đo live; chưa commit.

### 2026-10-21 14:30 — Dẫn chứng theo đoạn dòng + anchor (giảm lượt sửa bằng chứng) (Asia/Ho_Chi_Minh)

- Yêu cầu: sửa triệt để vấn đề lượt "sửa bằng chứng" làm token tăng 2–4 lần.
- Nguyên nhân (dữ liệu thật): Codex low IPTV 28 evidence bị loại, 27 do viết lại đoạn code dài, dòng đầu vẫn đúng dòng được dẫn; mô phỏng với ranged evidence (≤8 dòng, anchor = dòng đầu 60 ký tự) cả 28 + 4 của Sonnet đều xác minh được.
- Đã làm: evidence schema live = {file, line, end_line, anchor} (bỏ excerpt); `_verify_range` (đoạn tồn tại, ≤20 dòng, anchor ≥4 ký tự nằm trong đoạn, so sánh bỏ khoảng trắng) và tool điền excerpt = mã thật; excerpt cũ vẫn kiểm chặt như trước (replay/benchmark/cache cũ). Prompt claims-review-9: bỏ excerpt, hướng dẫn anchor/đoạn 1–8 dòng. Cache đã lưu dùng lại được (excerpt điền sẵn).
- Kiểm: 215/215 test (thêm 3 test ranged + cache reverify); live Claude Sonnet low trên AI Learn, ADS_SPLASH_PLACEMENT: PASS, 1 lượt, 0 sửa, 4 tool, 26s, 6 evidence verified, output 3.7K token. Chưa kiểm Codex live với schema mới. Server restart. Chưa commit.
- Đánh đổi đã nêu trong README: mất bằng chứng AI "đã nhìn nguyên văn cả đoạn", còn anchor ngắn.

### 2026-10-21 13:00 — Giảm token cho lượt chạy mới (Asia/Ho_Chi_Minh)

- Người dùng hỏi chạy lại có tốn token nữa không và yêu cầu tối ưu. Trả lời: có, lượt đầu sau khi đổi checklist/prompt/pack phải chạy lại AI.
- Đã làm: (1) bỏ pack version khỏi khóa verdict cache và scoped cache — bump version khi thêm rule không còn làm mất kết quả AI của rule không đổi (rule text/params, context, policy, engine, tài liệu vẫn đổi khóa). Một lần duy nhất khóa đổi định dạng nên lượt tới vẫn chạy đủ. (2) Prompt: evidence 1–5 dòng nguyên văn (không "...", không gộp, không tóm tắt) vì 27/28 evidence trượt của Codex low là đoạn dài bị viết lại; lệnh đọc ≤~120 dòng, không cat/nl cả file, bắt đầu từ flow_map/evidence_bundle (output lớn bị mang theo mọi lượt sau). PROMPT_POLICY claims-review-8-short-reads. 212/212 test; server restart. Chưa đo token live; chưa commit.
- Đề xuất chờ duyệt: gộp ADS_LOAD_OBSERVE_GATES vào rule từng màn (trùng đọc AdsManager); rule nhẹ chạy Haiku; chỉ điều tra bổ sung khi chưa sửa bằng chứng.

### 2026-10-21 12:20 — Rule chặn xoay màn hình và observe liên tục (Asia/Ho_Chi_Minh)

- Hỏi: đã có rule kiểm observer ads liên tục và chặn xoay màn hình ở 4 màn chưa. Kết quả rà: observer đã nằm trong ADS_LOAD_OBSERVE_GATES (load→observe→render/hide, observer bị ngắt → FAIL) và rule Language (observer chồng), Onboarding (vòng đời view) nhưng chưa thành mục riêng cho từng màn; chặn xoay chưa có rule nào.
- Đã làm: rule tĩnh `ADS_SCREEN_ORIENTATION` (custom check `screen_orientation_lock`): parse resources/AndroidManifest.xml, 4 Activity đầu phải có screenOrientation thuộc {portrait, reversePortrait, sensorPortrait, userPortrait, locked}; ghi chú nếu chỉ dùng configChanges=orientation; evidence dòng manifest; hiện ở mục cấu hình của tab Marketing. Checklist Language/Onboarding/Welcome thêm ý "theo dõi liên tục kết quả tải (observe), quảng cáo về trễ vẫn hiện". Pack 0.10.0, 17 rule.
- Kết quả: IPTV và AI Learn đều PASS (4 màn portrait). 211/211 test; server restart. Chưa commit; AI cần chạy lại (checklist đổi nên cache AI cũ không dùng).

### 2026-10-21 11:50 — Logic từng màn và checklist yêu cầu trong báo cáo (Asia/Ho_Chi_Minh)

- Yêu cầu: báo cáo nêu rõ ở 4 màn Splash/Language/Onboarding/Welcome app đang có logic thế nào và đã đúng yêu cầu chưa (load, show ads).
- Đã làm: schema AI thêm `screen_report` {load, show, requirements[{index,status ok|issue|unknown|na,note}]} (bắt buộc cho strict schema, rule không checklist trả rỗng); `params.checklist` (5/5/5/4 mục) cho ADS_SPLASH/LANGUAGE/ONBOARDING/WELCOME; prompt hướng dẫn tiếng Việt dễ hiểu, chỉ ok/issue khi có bằng chứng; `agent._screen_report` ghép checklist, hạ mọi ok/issue thành unknown nếu rule bị guard hạ UNKNOWN, đánh dấu `verified`; `Finding.screen_report`; marketing `screens[].logic/requirements`; hiển thị ở tab Marketing, report.md, report.html. Pack 0.9.0, PROMPT_POLICY claims-review-7.
- Kiểm tra: 210/210 unittest; build đạt; smoke Claude Sonnet low trên examples/workspace (ADS_SPLASH_PLACEMENT): schema được chấp nhận, thiếu code thì mọi mục unknown đúng. Chưa kiểm Codex với schema mới; chưa chạy APK thật (cache AI cũ không dùng lại vì pack/prompt đổi). Server restart. Chưa commit.

### 2026-10-21 11:10 — Gỡ rule Firebase tracking (Asia/Ho_Chi_Minh)

- Theo yêu cầu: xóa `ADS_FIREBASE_EVENTS` khỏi rulepacks/default/rules/ads-flow.yaml, pack 0.8.0, 16 → 15 rule (11 AI → 9 AI... xem rules check: 16 luật tính cả rule tĩnh mới). base-reference.json và scripts/snapshot_base_reference.py giữ mục cũ (không ảnh hưởng). Cơ chế skip_after_pass giữ lại, hiện chưa rule nào dùng. 206/206 test; server restart. Chưa commit.

### 2026-10-21 10:45 — Sửa ADS_CONFIG_FLAGS đọc sai key UA (Asia/Ho_Chi_Minh)

- Lỗi: rule chỉ đọc `enableUaCheck` (camelCase) trong ad_config.json, trong khi JSON thật dùng `enable_ua_check` (adapter của base `AdRemoteConfigJsonAdapterFactory` đọc `"enable_ua_check"`). Hệ quả: native_onboarding_fullscreen_* đã `enable_ua_check: true` vẫn bị báo thiếu — báo cáo sai. Đã đọc cả hai tên key, ưu tiên `enable_ua_check`; trường trong báo cáo đổi thành `enable_ua_check`.
- Sau sửa: IPTV FAIL chỉ vì inter_home/inter_back có UA true (cả hai file); AI Learn FAIL vì inter_onboarding UA true. Các native fullscreen không còn bị báo. 206/206 test; server restart. Chưa commit.

### 2026-10-21 10:25 — Kết quả Codex Sol low trên IPTV và bỏ qua rule đã đạt (Asia/Ho_Chi_Minh)

- Job 1f4be3bd (IPTV, Codex Sol low, 6 workers, 16 rule): 5 PASS / 3 FAIL / 8 UNKNOWN, 936s (rules 905s). 7/10 rule AI UNKNOWN do `unverified_evidence` kể cả sau sửa bằng chứng. Token: input 13.29M (cache đọc 11.49M, mới 1.80M), output 256K; mỗi rule 0.5–2.5M input — cùng bậc với Codex medium hôm trước (~1.37M/rule), nên low không tiết kiệm token và chậm hơn Sonnet (242s). 
- Chẩn đoán evidence trượt (28 mục): chỉ 1/28 do sai số dòng; 27/28 đoạn trích không phải nguyên văn dù dòng đầu khớp đúng dòng được dẫn (Codex low viết lại/tóm tắt đoạn code). Không thể xác minh bằng cách tự sửa số dòng hay thay đoạn trích bằng code thật (sẽ hợp thức hóa claim bịa); giữ hợp đồng nghiêm.
- Kết luận đề xuất: không dùng Codex low làm mặc định; ưu tiên Claude Sonnet low (ít UNKNOWN hơn, nhanh hơn) hoặc Codex medium.
- Đã làm: `skip_after_pass` (passed_history.py): rule ADS_FIREBASE_EVENTS bỏ qua ở bản build sau khi app đã Đạt; `--recheck-all`/ô web; lịch sử seed từ report khi web khởi động (hiện có INIT_ORDER của com.ai.learn…, IPTV chưa có Firebase vì FAIL). 206/206 test, server đã restart sau khi job xong. Chưa commit.

### 2026-10-21 14:00 — Codex nối tiếp phiên cho lượt sửa/điều tra (Asia/Ho_Chi_Minh)

- Bối cảnh: lượt web Codex Sol low trên IPTV: 5/6 rule AI vào lượt "sửa bằng chứng" trước khi rule nào xong; Codex chưa nối phiên nên mỗi lượt sửa gửi lại toàn prompt. Người dùng yêu cầu dừng audit và áp dụng cho Codex. Audit/server đã dừng (job 84a23cfd bị gián đoạn, mới có facts/inventory).
- Đã làm: CodexEngine `supports_resume`; lượt đầu giữ session (bỏ --ephemeral, lấy `thread_id` từ sự kiện thread.started), lượt sau `codex exec resume <id>` với `sandbox_mode="read-only"` (resume không có --sandbox/--cd) và cwd=workspace; `close_session` xóa rollout trong ~/.codex/sessions khi rule xong; review FAIL vẫn phiên mới (agent.py không đổi). map_document vẫn --ephemeral.
- Kiểm live (Sol low, examples/workspace, ADS_INIT_ORDER): resume nhớ ngữ cảnh, read-only chặn ghi file, không còn rollout sót sau khi xong; lượt resume chỉ gửi 5.5–6.4KB prompt thay vì 24KB (token vào gồm cả hội thoại nhưng ~82–85% từ cache).
- Đã thử và bỏ: tự sửa số dòng evidence và tự gộp chỉ số path vào claim — trên dữ liệu Sonnet thật chỉ 0/4 evidence còn trượt được sửa dòng, và cả hai làm hỏng test hợp đồng nghiêm (evidence phải khớp ở đúng dòng được dẫn, path phải nằm trong claim). Lỗi cấu trúc claim phần lớn là hệ quả evidence không xác minh, nên cách đã có (so khớp bỏ khoảng trắng/gộp dòng/"...") mới là phần hiệu quả. Giả thuyết "phần lớn là sai số dòng" của lượt trước KHÔNG được dữ liệu ủng hộ; chưa biết nguyên nhân repair của Codex low trên IPTV vì job bị dừng trước khi có trace.
- File: apk_audit/engines.py, tests/test_codex_engine.py. 202/202 test; server restart. Chưa commit.
- Việc tiếp: chạy lại IPTV với trace bật để biết vì sao Codex low cần repair (so với medium); cho rule tĩnh chạy trước để bộ đếm tiến độ không hiện 0/16.

### 2026-10-21 12:30 — Rule ID test ở ad_config_debug (Asia/Ho_Chi_Minh)

- Theo yêu cầu: `ADS_DEBUG_TEST_IDS` (static, pack 0.7.0, 17 rule): mọi placement trong ad_config_debug.json phải dùng ID demo Google (pub-3940256099942544) đúng loại (open 9257395921; banner 6300978111/9214589741; inter 1033173712; reward 5224354917/5354046379; native 2247696110/1044960115). ID trống chỉ chấp nhận khi isEnable=false; ID thật, ID sai loại hoặc trống khi đang bật → FAIL. ad_config.json (release) dùng ID demo → FAIL. Evidence file/dòng JSON; hiện ở nhóm Cấu hình của tab Dev và mục kiểm tra cấu hình của tab Marketing.
- APK AI Learn: PASS (debug dùng ID test đúng loại, 9 placement tắt để trống, release dùng ID thật pub-7462…).
- File: apk_audit/rules/{custom,loader}.py, apk_audit/{dev_view,marketing}.py, rulepacks/default/{pack.yaml,rules/ads-flow.yaml}, tests/test_custom_rules.py, README.md. 201/201 test; server restart. Chưa commit.

### 2026-10-21 12:00 — Codex hạ xuống Sol low (Asia/Ho_Chi_Minh)

- Theo yêu cầu: Codex `gpt-6.1-sol` effort `medium` → `low` (engines.py, label, README, UI, test). Báo cáo cũ giữ nhãn medium. Verdict cache cũ của Codex medium không dùng lại cho low (engine identity đổi). 200/200 test, build đạt, server restart. Chưa đo chất lượng Sol low; chưa commit.

### 2026-10-21 11:30 — Triển khai kế hoạch đọc dễ / nhanh / ít token (Asia/Ho_Chi_Minh)

- Nhánh `feat/readable-fast-cheap-audit` (từ main, mang theo thay đổi rule UA/Dev toggle chưa commit từ sáng). Kế hoạch: docs/superpowers/plans/2026-10-21-readable-fast-cheap-audit.md.
- GĐ0: `metrics.usage_totals`, `rules[].usage` chuẩn hóa (input/cache_read/cache_write/output), `resumed_attempts`; UI hiện token; `scripts/measure_audit.py` (chưa chạy live, cần quota).
- GĐ1: tab Marketing/Dev; `dev_view.py` (gom theo màn, kết luận một dòng, Cần sửa, file:dòng, lý do UNKNOWN bằng lời thường, UNKNOWN do guard hiện "AI nghiêng về..."); nhãn chung Đạt/Cần sửa/Cần dev xem lại/Không áp dụng; `report_html.py` + endpoint `/report.html`, `/ids.csv`; nút copy ID lỗi; report.md theo cấu trúc mới; báo cáo cũ được dựng lại dev_view khi mở.
- GĐ2: rule tĩnh ADS_REMOTE_KEYS, ADS_INTERSTITIAL_INTERVAL, ADS_SCREEN_NAMES (pack 0.6.0, 16 rule); rule ID thu hẹp còn nguồn ID trong code (budget 35); rule welcome/banner → SKIPPED không gọi AI khi tài liệu không dùng; `scoped_cache.py` dùng lại verdict PASS/FAIL theo file đã đọc (kiểm trên trace thật: 7/7 liệt kê được, cần tập đường dẫn file không đổi; `--no-scoped-cache`); `flow_map.py` bản đồ luồng quảng cáo (~2KB) vào context.
- GĐ3: bundle gợi ý 12000 ký tự (rule.budget.context_chars ghi đè), bỏ output_schema trùng khỏi prompt CLI, prompt yêu cầu 6–12 evidence và reasoning ~8 dòng. Replay: prompt mỗi rule 80–85KB → 43–52KB.
- Chưa làm: GĐ3.3 (model theo độ khó, tùy chọn chờ duyệt); đo live thời gian/token/chất lượng; visual QA trình duyệt cho 2 tab; refactor JSX bị lặp (mid) trong App.jsx.
- Kiểm tra: 200/200 unittest, frontend build đạt, rules check 16 luật, server restart (HTTP 200), API trả dev_view/report.html/ids.csv trên báo cáo cũ. Chưa commit/push.

### 2026-10-21 09:20 — Rule tĩnh isEnable/UA check và Dev setting ở Language (Asia/Ho_Chi_Minh)

- Mục tiêu: người dùng mô tả cơ chế UA check của base (isEnable + enableUaCheck; Dev setting → Unlimited ads bypass thành non-organic) và yêu cầu thêm rule trước các bước tiếp theo.
- Khảo sát base e8f4337: AdUnitConfig.enableUaCheck mặc định false; ad_config*.json của base không khai báo enableUaCheck; LanguageActivity gắn `tvTitle.setOnAdminAdToggleListener` (com.itg.devconfig). Yêu cầu người dùng: chỉ 4 native_onboarding_fullscreen_* có enableUaCheck=true.
- Đã làm: `apk_audit/rules/custom.py` với `ad_config_flags` (enableUaCheck đúng pattern `native_onboarding_fullscreen_*`; isEnable theo trạng thái ADS SCRIPTS active/disabled, bỏ qua inter_onboarding/unknown; kiểm cả ad_config.json và ad_config_debug.json, evidence file/dòng JSON) và `language_dev_toggle` (tìm setOnAdminAdToggleListener trong *Language*Activity/Fragment; FAIL nếu chưa gắn, UNKNOWN nếu không thấy màn Language). Hai rule static ADS_CONFIG_FLAGS, ADS_LANGUAGE_DEV_TOGGLE (không tốn token AI); pack 0.5.0, 13 rule. evaluate_static nhận workspace. Tóm tắt Marketing thêm mục config_checks (bảng file/vị trí/trường/cần/đang) trên web và report.md.
- Kết quả APK AI Learn: ADS_CONFIG_FLAGS FAIL (4 native fullscreen Onboarding thiếu enableUaCheck=true ở cả 2 file); ADS_LANGUAGE_DEV_TOGGLE PASS (LanguageActivity.java:231).
- File: apk_audit/rules/{custom(mới),engine,loader}.py, apk_audit/{pipeline,marketing}.py, rulepacks/default/{pack.yaml,rules/ads-flow.yaml}, frontend/src/App.jsx + build, tests/test_custom_rules.py (mới), SESSION_LOG.md.
- Kiểm tra: 182/182 unittest, rules check 13 luật, build đạt. Server không chạy (máy khởi động lại) → đã start lại, HTTP 200. Chưa commit.
- Còn lại theo kế hoạch 21/10: Remote Config so tài liệu (mục 1 phần còn lại), logic Welcome back/App Open.

### 2026-10-20 18:40 — Tiết kiệm token Claude và tóm tắt cho Marketing (Asia/Ho_Chi_Minh)

- Bối cảnh: lượt Sonnet 5.5 medium (job 837e1e00) cho 5 PASS/2 FAIL/4 UNKNOWN trong 242s nhưng đốt hết phiên 5h; token chủ yếu là cache write ~1.07M do mỗi lượt sửa/review mở phiên mới, cache read ~2.35M, output ~126K.
- Tiết kiệm token: Claude Sonnet effort low; agent nối tiếp phiên rule cho repair/investigation (chỉ gửi phần góp ý, review vẫn phiên mới, resume lỗi trước khi có tool call thì fallback prompt đầy đủ, close_session xóa ~/.claude/projects/*/<id>.jsonl). Prompt: phần chung trước, header ngân sách cuối. Cross-flow tắt mặc định (`cross_flow` trong pipeline, `--cross-flow`, header X-Cross-Flow, checkbox web). Đã kiểm live `claude -p --session-id` rồi `--resume` nhớ được ngữ cảnh; chưa đo token một lượt audit mới.
- Marketing: `apk_audit/marketing.py` tạo `report.marketing` (4 màn đầu, bảng placement với ID tài liệu/app và tình trạng, nhãn màn = số ID lỗi + luồng quảng cáo theo rule, ghi chú khác tài khoản AdMob, danh sách ID có vấn đề). AI thêm trường `marketing_summary` (schema bắt buộc, lời dễ hiểu). report.md có mục Tóm tắt cho Marketing trước phần kỹ thuật. Web: thẻ "Tóm tắt cho Marketing · 4 màn đầu" ở đầu kết quả; báo cáo cũ được dựng lại phần này khi mở (từ facts.json + tài liệu đã lưu).
- Kết quả trên job 837e1e00: 15 ID có vấn đề; toàn bộ ID app thuộc pub-7462273888693209, ADS SCRIPTS là pub-2864154863223892.
- File: apk_audit/{agent,claude_engine,contracts,engine_common,execution,pipeline,cli,web,report,marketing(mới)}.py, frontend/src/{App.jsx,style.css} + build, tests/{test_audit_depth,test_claude_engine,test_execution,test_marketing(mới)}.py, README.md, SESSION_LOG.md.
- Kiểm tra: 179/179 unittest đạt, frontend build đạt, restart server; API trả marketing cho báo cáo cũ. Chưa visual QA trình duyệt; chưa đo token/thời gian lượt Sonnet low mới; chưa commit.

### 2026-10-20 17:30 — Tối ưu thời gian/token/độ chính xác (Asia/Ho_Chi_Minh)

- Mục tiêu: người dùng duyệt kế hoạch tối ưu (lọc context, workers, cross-flow gọn, review nhắm đúng, giảm UNKNOWN oan).
- Đã làm:
  - `apk_audit/context_scope.py`: lọc ADS SCRIPTS/checklist/inventory theo `rule.area` (placement theo tên, checklist theo từ khóa, bỏ trường rỗng/trùng; code_references nhóm theo file, tối đa 3 ref/placement). Prior cho cross-flow chỉ giữ verdict, reasoning 700 ký tự, 6 claim, 8 evidence (excerpt 160). `SCOPE_VERSION` vào cache policy.
  - Đo trên APK AI Learn (replay, không gọi AI): prompt đầu 911.7KB → 652.2KB tổng 11 rule (-28%); code_references 8.5KB → 1.8KB; thêm phần code_references sau đó chưa đo lại tổng.
  - `agent._excerpt_matches`: so excerpt theo dòng bỏ khoảng trắng, chấp nhận block bị gộp dòng (≤15 dòng) và "..." là đoạn bỏ (≤40 dòng), vẫn bắt đầu đúng dòng và đúng thứ tự. Trên 53 evidence bị đánh trượt ở lượt Claude trước: 37 nay hợp lệ, 16 vẫn bị chặn (code bị viết lại/gộp sai), 0 evidence hợp lệ bị đổi kết quả.
  - Review FAIL giới hạn 12 lệnh, prompt chỉ đọc lại violation/gate. AUDIT_PROMPT hướng dẫn excerpt nguyên văn, "..." cho đoạn bỏ. PROMPT_POLICY_VERSION claims-review-6-scoped.
  - Web mặc định 6 workers.
- File: apk_audit/{context_scope(mới),pipeline,agent,web,cli}.py, tests/{test_context_scope(mới),test_claims}.py, SESSION_LOG.md.
- Kiểm tra: 175/175 unittest đạt. Đang chạy Claude Haiku 10 workers so với baseline 606s/0P-2F-9U: out/claude-speed-test-v2.
- Restart server với code tối ưu (người dùng yêu cầu chạy thử).
- Nâng Claude engine: `claude-sonnet-5-5` effort `medium` (allowlist chỉ Sonnet 5.5); UI/README/test cập nhật, nhãn Haiku cũ giữ cho báo cáo cũ. Smoke `claude -p` Sonnet trả OK. 175/175 test, build đạt. Dừng lượt so sánh Haiku CLI (exit 143, không có kết quả). Restart server lần nữa.
- Chưa: Codex live (quota tới 19:10), audit Sonnet thật, commit.

### 2026-10-20 17:00 — Test tốc độ Claude 10 workers (Asia/Ho_Chi_Minh)

- Người dùng muốn test bằng Claude và tối ưu tốc độ. Đang làm: CLI audit APK c7d5612c (AI Learn, 2 CSV cũ) `--engine claude --workers 10 --cache-dir out/web/cache`, output out/claude-speed-test, log /tmp/claude-1000/claude-speed.log. So với Codex 4 workers: 1028s tổng, rules 951s.
- Quan sát Codex: mỗi rule ~1.37M input token (86% cached), review FAIL làm thêm một lượt dài.
- Kết quả Claude Haiku low 10 workers: 606s tổng (rules 589s = rule thường chậm nhất 303s + cross-flow 286s chạy sau), 314 tool calls, 0 PASS/2 FAIL (SPLASH, WELCOME_RESUME)/9 UNKNOWN. 7 UNKNOWN do unverified_evidence/claims (bản nháp AI có dẫn chứng sai), cross-flow tool_budget. SPLASH FAIL trái với Codex PASS — chưa đối chiếu. Nhanh hơn ~1.7x nhưng chất lượng kém Codex rõ rệt. Exit 1 của CLI là do có FAIL, không phải lỗi chạy.

### 2026-10-20 16:50 — Về main, cô lập Codex và báo lỗi quota (Asia/Ho_Chi_Minh)

- Người dùng đã merge PR #1; chuyển sang main f63bbeb (stash/pop SESSION_LOG).
- Codex audit chạy với `--ignore-rules`, tắt plugins/apps/hooks/multi_agent, `skills.include_instructions=false`, `include_apps_instructions=false`, `project_doc_max_bytes=0`. Đo bằng `codex debug prompt-input` trên examples/workspace: prompt nền ~51KB/77 tham chiếu SKILL.md xuống ~17KB/0 skill, không còn nạp AGENTS.md. Claude engine đã cô lập sẵn (--safe-mode/--restricted).
- Lỗi Codex exit≠0 giờ lấy thông điệp từ sự kiện JSON `error`/`turn.failed` (vd usage limit + giờ thử lại) thay vì "exit 1".
- File: apk_audit/engines.py, tests/test_codex_engine.py, SESSION_LOG.md. 169/169 unittest đạt. Restart server, HTTP 200.
- Chưa kiểm live: Codex đang hết quota tới 19:10; cần một audit thật để xác nhận cờ mới không làm hỏng phiên. Chưa commit.

### 2026-10-20 16:30 — Commit và push (Asia/Ho_Chi_Minh)

- Theo yêu cầu người dùng: commit 4c1671e trên feat/audit-optimization (61 file), push lên origin (nhánh mới). 168/168 unittest đạt trước commit. Chưa tạo PR/merge main.
- Việc tiếp theo đề xuất: hiện rõ lỗi quota Codex thay vì "exit 1"; chạy Codex audit không nạp skill cá nhân ~/.codex.

### 2026-10-20 16:20 — Phân tích kết quả audit AI Learn 4 workers (Asia/Ho_Chi_Minh)

- Job c7d5612c (com.ai.learn.and.speak.language.ailearn, Codex Sol medium, 4 workers): 1 PASS / 3 FAIL / 7 UNKNOWN, 179 tool calls, 1028s tổng (rules 951s; tổng thời gian rule cộng dồn ~3500s nên song song giảm ~3.5x).
- FAIL: INIT_ORDER, LANGUAGE_PLACEMENT, WELCOME_RESUME. PASS: SPLASH.
- UNKNOWN: BANNER_RELOAD và CROSS_FLOW `engine_error` do Codex hết usage limit (đã xác minh bằng codex exec: "You've hit your usage limit ... try again at 7:10 PM"); FIREBASE review_error (nhiều khả năng cùng nguyên nhân, chưa xác minh); ID_SOURCE unverified_evidence (bản nháp FAIL lệch 4 ID Splash release); ONBOARDING/LOAD_OBSERVE thiếu thân hàm AdExtensionKt:911 do JADX lỗi; REMOTE_FALLBACK custom parser.
- Phát hiện: lỗi Codex chỉ báo "exit 1" vì thông báo nằm trong JSON stdout; Codex nạp skill cá nhân ~/.codex và đọc AGENTS.md/SESSION_LOG.md, tốn lệnh. Chưa sửa.

### 2026-10-20 15:55 — Xóa cache và lịch sử, restart (Asia/Ho_Chi_Minh)

- Theo yêu cầu: không có job đang chạy; dừng server, xóa out/web (lịch sử, báo cáo, uploads, documents, cache), ~/.cache/apk-audit và file tạm /tmp/apk-audit-*; restart server, /api/jobs rỗng.

### 2026-10-20 15:45 — Hiển thị agent đang chạy trên UI (Asia/Ho_Chi_Minh)

- Mục tiêu: UI hiện trực quan từng agent/rule đang chạy và lệnh nó đang thực thi.
- Đã làm: `engine_common.ACTIVITY` (contextvar) + `report_activity()`; Codex/Claude engine báo lệnh và số tool call khi bắt đầu mỗi tool; agent báo giai đoạn (initial/repair/investigation/review), lượt và allowance; pipeline gắn sink theo rule. Web lưu phase/tool_calls/allowance/command/recent_commands (6 gần nhất)/started_at trong `current_rules`. Frontend thêm khối "Agent đang chạy": thẻ mỗi rule với chấm nhấp nháy, thời gian chạy, tag giai đoạn, thanh lệnh đã dùng/ngân sách, lệnh hiện tại dạng terminal và lịch sử lệnh.
- File: apk_audit/{engine_common,engines,claude_engine,agent,pipeline,web}.py, frontend/src/{App.jsx,style.css}, web_assets build, tests/test_web.py, SESSION_LOG.md.
- Kiểm tra: 168/168 unittest đạt (test web mở rộng cho activity); build đạt; pipeline thật trên examples/workspace với engine giả, 4 workers: 22 sự kiện activity cho 11 rule. Chưa visual QA trình duyệt.
- 15:50: Theo yêu cầu, dừng server và 4 tiến trình claude của job 30ca2841 (ngắt job), restart server với UI agent mới; HTTP 200.

### 2026-10-20 15:35 — Chạy nhiều rule song song (Asia/Ho_Chi_Minh)

- Mục tiêu: Người dùng muốn audit nhanh hơn bằng nhiều phiên AI chạy đồng thời.
- Đã làm: `execution.MAX_WORKERS=10`, `valid_workers()` dùng chung cho execution/pipeline/web/cli; `--workers 1-10`; `serve` mặc định 4. Cross-flow vẫn chạy sau cùng; ngân sách 400 lượt vẫn được giữ chỗ theo rule.
- File: apk_audit/{execution,pipeline,web,cli}.py, tests/test_execution.py, README.md, SESSION_LOG.md.
- Kiểm tra: 168/168 unittest đạt (thêm test 6 rule chạy đồng thời bằng Barrier). Chưa đo thời gian audit thật với 4 workers; chưa kiểm rate limit/quota CLI khi chạy song song.
- Sự cố: Restart server lúc 15:24 làm gián đoạn job Claude 257c1216 người dùng vừa bắt đầu (0/11). Server mới đang chạy; job có nút Tiếp tục.

### 2026-10-20 15:30 — Xóa lịch sử kiểm tra web (Asia/Ho_Chi_Minh)

- Theo yêu cầu: dừng server, xóa toàn bộ out/web (job, báo cáo, uploads, documents), restart server nền; /api/jobs trả rỗng. Giữ các thư mục out/* validation/pilot CLI khác.

### 2026-10-20 15:25 — Dừng audit, xóa sạch cache, restart server (Asia/Ho_Chi_Minh)

- Theo yêu cầu: dừng server cũ (PID 448253/448297) và codex exec của job 00e42ef1 (đang ở rule 1/11); xóa out/web/cache, ~/.cache/apk-audit, /tmp/apk-audit-codex-*. Giữ báo cáo/jobs/uploads/documents.
- Restart `uv run apk-audit serve` nền (log /tmp/claude-1000/apk-audit-serve.log), cổng 8765 trả engines OK; bản build có chọn sheet. Job cũ hiển thị bị gián đoạn; cần chạy lượt mới.
- Ghi chú: mục "Xóa cache tool" trước đó xóa nhầm lúc job vừa được Tiếp tục; lần này dừng job trước rồi mới xóa.

### 2026-10-20 15:50 — Xóa cache tool (Asia/Ho_Chi_Minh)

- Theo yêu cầu người dùng, xóa out/web/cache (2.2G: workspaces, source-index, verdicts), out/audit-optimization-benchmark/cache và ~/.cache/apk-audit (570M). Không có job đang chạy lúc xóa (server 8765 vẫn chạy). Giữ báo cáo, uploads, documents, jobs. Lượt sau phải giải mã và gọi AI lại từ đầu; resume job cũ không còn dùng lại verdict cache.

### 2026-10-20 15:10 — Sửa đóng gói/đường dẫn rule pack (Asia/Ho_Chi_Minh)

- Mục tiêu: Người dùng yêu cầu hoàn thiện các chức năng còn dở; bắt đầu với ưu tiên số 1 (pack phụ thuộc cwd).
- Trạng thái: Hoàn tất mục đóng gói/path/fail-fast. Các mục còn lại (chọn sheet, lọc context theo rule, tiến độ live/hủy audit) chưa làm.
- Đã làm: `load_pack()` không còn trả pack empty im lặng; tìm pack trong gói (`apk_audit/rulepacks/default`) rồi tới gốc repo, không thấy thì AuditError mã 5. Wheel force-include `rulepacks/default`.
- File thay đổi: apk_audit/rules/loader.py, pyproject.toml, SESSION_LOG.md.
- Kiểm tra: `rules check` từ /tmp đạt 11 luật; wheel chứa 6 file pack; cài wheel vào venv sạch, chạy từ / đạt 11 luật; 165/165 unittest đạt.
- Bước tiếp theo: Lọc Documents/inventory theo rule; live stage + hủy audit tới CLI.

### 2026-10-20 15:40 — Chọn sheet XLSX cho workbook nhiều app (Asia/Ho_Chi_Minh)

- Mục tiêu: Người dùng chọn làm tiếp chức năng chọn sheet.
- Trạng thái: Hoàn tất; chưa restart server chính, chưa visual QA trình duyệt.
- Đã làm: `documents.list_sheets()` trả sheet khớp header (không có thì mọi sheet visible); `load_document(..., sheet=)` lọc đúng sheet visible, lỗi nhiều sheet liệt kê tên. Pipeline `ads_sheet`/`checklist_sheet`; CLI `--ads-sheet`/`--checklist-sheet`. Web: `/api/documents` trả `sheets`; reserve nhận header `X-Ads-Scripts-Sheet`/`X-Checklist-Sheet` (URL-encoded), bắt buộc chọn khi >1 sheet, lưu `document_sheets` trong job (resume dùng lại). Frontend upload tài liệu ngay khi chọn, hiện Select sheet, khóa nút bắt đầu khi đang đọc/thiếu sheet, tải lại token nếu lượt trước đã dùng.
- File thay đổi: apk_audit/{documents,pipeline,cli,web}.py, frontend/src/App.jsx + web_assets build, tests/{test_documents,test_web,test_job_persistence}.py, README.md, SESSION_LOG.md.
- Kiểm tra: 167/167 unittest đạt; frontend build đạt. Workbook Smart Zone thật: ADS 3 sheet app, working 4 (gồm Index); chọn từng sheet đọc đúng 24/17/24 placement và 66 dòng working, không gọi AI. Smoke server tạm cổng 8799: upload ADS trả đúng 3 sheet. Chưa chạy audit APK đầy đủ với lựa chọn sheet.
- Giới hạn: Working file vẫn liệt kê sheet Index (header khớp Content/Detail); người dùng tự chọn đúng sheet app. Không tự đoán ghép cặp sheet.

### 2026-10-20 14:47 — Sửa CSV lệch header và bổ sung AI nhận dạng tài liệu (Asia/Ho_Chi_Minh)

- Mục tiêu: Sửa CSV SmartZone bị từ chối, sau đó nhận steering người dùng muốn đọc linh hoạt và thêm AI lọc thông tin khi cần.
- Trạng thái: Hoàn tất triển khai/kiểm chứng slice nhận dạng cấu trúc; chưa restart server hoặc phát hành.
- Nguyên nhân thực: CSV ADS MoneyTracker có dòng giới thiệu ở dòng1, header dòng2; parser cũ chỉ đọc dòng đầu. Working AI Learn đọc được66dòng nhưng là app khác ADS17placement. Không sửa workbook/CSV gốc hoặc tự ghép hợp đồng khác app.
- Đã làm: Regression RED/GREEN cho header lệch/blank/multiline/boundary40/wrongslot. Tiếp đó alias cột và tự nhận delimiter; callback mapping tùy chọn cho CSV/XLSX, schema và kiểm tọa độ từ preview. Tách structured invocation dùng lại lifecycle/timeout/usage của Codex/Claude, giữ model/effort pin; Claude mapping tools rỗng, Codex tắt shell/websearch, mọi tool call mapping bị từ chối. Không coi observer là hard gateway cho mọi tool bên trong Codex. Pipeline gọi fallback tự động chỉ khi cần, không gọi khi static/none/budget0. UI báo tài liệu được đọc trực tiếp hay AI hỗ trợ và dòng tiêu đề/số dữ liệu; metrics không lưu raw preview. Không tạo/correct ID hoặc thay trạng thái bôi màu bằng suy đoán AI.
- File thay đổi lượt này: apk_audit/{documents,document_structure,engines,claude_engine,pipeline}.py; tests/{test_documents,test_document_mapping}.py; frontend/src/App.jsx và web_assets/app.js build; README.md, docs/superpowers/plans/2026-10-20-flexible-documents.md, SESSION_LOG.md. Giữ toàn bộ diff tối ưu cũ; không commit/push.
- Kiểm tra: Ban đầu CSV header regression đỏ rồi19/19 xanh, full155/155. Slice AI/alias/delimiter có test đỏ trước sửa; bắt và sửa regression mất cột mô tả Việt/Anh khi có cả hai. Cuối165/165đạt7.438s; buildđạt3.01s, diffcheckđạt. Kiểm hai CSV thật và XLSX mẫu với mapper cấm gọi: đọc trực tiếp đúng66/17/26dòng và XLSX3disabled.
- AI smoke: CSV tự tạo không chứa APK/ID đối tác, dùng empty pack có chủ đích. Codex thật Sol6.1medium ánh xạ header dòng2 trong8.856s/0tools,1placement, usage20507input/77output; out/document-ai-live-smoke/report.json. Không đánh giá APK/11rule trong smoke này. Hai provider fake CLI kiểm schema riêng, model pin, usage, no audit instruction; Claude thật chưa xác minh.
- Giới hạn: Mapping chỉ xác nhận tọa độ/cấu trúc, chưa là proof semantic của mọi tên cột; không hiểu thì báo lỗi, không bỏ tài liệu âm thầm. Preview bounded, header ngoài40dòng chưa hỗ trợ. Nhiều app sheet vẫn cần chọn/tách sheet, không có dropdown; không suy công thức/conditional formatting. Mapping chưa có cache riêng giữa các job. File thật người dùng hiện không cần AI fallback.
- Việc còn lại: Restart server để áp dụng backend mới, người dùng dùng đúng cặp tài liệu cùng app. Chưa commit/push, fullAPKaccuracy, liveClaudeauth hay visual browser QA; các tối ưu packaging/context trước vẫn chưa thực hiện.
- Bước tiếp theo: Dùng web với file mới sau restart; bộ chọn sheet và xác nhận ánh xạ thủ công là mở rộng riêng khi cần.

### 2026-10-20 14:29 — Giải thích lỗi XLSX nhiều sheet Smart Zone (Asia/Ho_Chi_Minh)

- Mục tiêu: Người dùng hỏi nguyên nhân lỗi khi tải ADS SCRIPTS và working file Smart Zone Infotech.
- Trạng thái: Hoàn tất chẩn đoán/giải thích; chưa triển khai chọn sheet.
- Đã làm: Đọc hướng dẫn/nhật ký, Git, loader XLSX và test; dùng load_document tái hiện với cả hai đường dẫn Downloads. Kiểm metadata, header và số placement bằng openpyxl chỉ đọc, không in ID/token hoặc nội dung checklist.
- Kết quả: ADS có ba sheet ứng dụng visible cùng mẫu, lần lượt AI Learn 24, Money Tracker 17, Silly 24 placements. Working có ba sheet ứng dụng tương ứng và Index bị coi là ứng viên do có Content/Detail. _xlsx_rows từ chối mọi trường hợp hơn một ứng viên nên dừng ở bước tài liệu; không liên quan giải mã APK/AI.
- Quyết định: Giải thích đúng giới hạn lựa chọn sheet, không gộp dữ liệu nhiều app hoặc tự chọn sheet đầu tiên. Cách hiện tại là dùng bản sao chỉ giữ sheet ứng dụng cần kiểm ở mỗi file; hướng sản phẩm là dropdown cho từng tài liệu và giữ trạng thái tô màu/gạch ngang.
- File thay đổi lượt này: SESSION_LOG.md. Không sửa workbook gốc, code chức năng, commit/push/restart.
- Kiểm tra: Hai lỗi thực được tái hiện, workbook đọc được và header/count đã kiểm; không chạy lại unit suite/build/AI vì lượt này chỉ chẩn đoán nguyên nhân.
- Việc còn lại: Chưa có bộ chọn sheet trên web/CLI, chưa biết ứng dụng người dùng muốn audit trong workbook nhiều app; không cần thông tin này để giải thích lỗi.
- Bước tiếp theo: Nếu triển khai hỗ trợ workbook nhiều sheet, truyền lựa chọn sheet rõ ràng xuyên suốt upload, parser, job persistence/resume và cache identity; kiểm đúng cặp sheet trước audit.

### 2026-10-20 14:18 — Rà soát code và ưu tiên tối ưu trước triển khai (Asia/Ho_Chi_Minh)

- Mục tiêu: Đánh giá code hiện tại, mức sẵn sàng triển khai và những phần có thể tối ưu theo câu hỏi người dùng.
- Trạng thái: Hoàn tất rà soát; chưa thực hiện các sửa đổi đề xuất.
- Đã làm: Đọc hướng dẫn/nhật ký, kiểm Git, pipeline/context, loader/packaging, metrics pilot, scheduler và tiến độ web. Xác nhận 2 workers đã có, chưa có hủy audit truyền tới CLI hoặc callback live cho các lượt repair/investigation/review.
- Phát hiện: Chạy rules check từ repo đạt 11 rule 0.4.0; chạy cùng executable từ /tmp trả empty 0 rule và exit 0. Wheel config chỉ bao gồm apk_audit nên cần đóng gói bộ rule/reference và bỏ phụ thuộc cwd. Pilot 3 rule dành ~98.3% thời gian cho AI, context 87–89KB/rule; đây là số đo snapshot trước chỉnh prompt cuối, không chứng minh tốc độ hay accuracy bản mới.
- Đề xuất theo thứ tự: Đóng gói/path/fail-fast; lọc Documents/inventory theo rule và tái dùng dẫn chứng; phân loại blocker để tránh điều tra code khi thiếu hợp đồng; benchmark 1/2 workers đã có; thêm live stage/hủy audit. Gate phát hành: full 11 rule có đầu vào thật, ca APK có kết luận chuẩn và kiểm cài/chạy ngoài repo trên máy mới.
- File thay đổi lượt này: SESSION_LOG.md; giữ toàn bộ diff chức năng có sẵn trên feat/audit-optimization.
- Kiểm tra: Chạy mới 151/151 unittest đạt trong 7.258s, log /tmp/apk-audit-readiness-tests.log; rules check tại repo và git diff --check đạt. Lỗi 0 rule ngoài cwd được tái hiện. Không chạy audit AI trả phí, build frontend mới, kiểm trực quan hoặc thử wheel cài đặt trong lượt này.
- Việc còn lại: Các tối ưu đề xuất chưa làm; chưa đo accuracy tổng quát, chưa chạy full 11 rule sau thay đổi cuối, chưa xác minh Claude live auth. Code tối ưu hiện có chưa commit/push; backend chưa restart để nạp toàn bộ thay đổi mới.
- Bước tiếp theo: Bàn giao ưu tiên triển khai; local beta có thể chạy từ repo với --rules tuyệt đối. Không tự commit/push/restart hoặc triển khai batch mới từ câu hỏi đánh giá.

### 2026-10-20 11:53 — Bổ sung code base và AI điều tra sâu (Asia/Ho_Chi_Minh)

- Mục tiêu: Người dùng yêu cầu giải quyết UNKNOWN bằng thêm dữ liệu base và AI can thiệp sâu; sau đó cung cấp XLSX để kiểm mẫu, xác nhận không cần khớp ứng dụng.
- Trạng thái: Hoàn tất triển khai/kiểm đại diện; chưa chạy lại full11rule với hợp đồng thật mới hoặc đo accuracy tổng quát.
- Chẩn đoán: Report31f931... có50evidence nhưng claim trỏ53–63, path không nằm trong claimrefs; UNKNOWN có excerpt sai không được repair, có thểreusecache; native Language dừng26/25tools. Đọc sourcebase thật commit e8f4337, phát hiện khác biệt docs cũ về Languagepreload/Splashreload.
- Đã làm: Thêm snapshotbase và scriptrefresh kiểm commit/dirtysource; loader/RulePack/pipeline chuyển profile riêng, hashreference vào cache, metricsnguồn. Sửa repair/UNKNOWNinvestigation/budgetreserve/retainedreadoutputs, thêm currentattemptlimit tách khỏi tổngrule. RevalidateUNKNOWN/cache; giữ strictguard/review. Sửa scope/rulebudget và banner logic. UI/README/validationdoc cập nhật. Không gửi Sheet/webhook hoặc đổi account/model.
- File thay đổi lượt này: apk_audit/{agent,engine_common,engines,claude_engine,contracts,pipeline}.py; apk_audit/rules/loader.py; scripts/snapshot_base_reference.py; rulepacks/default/{base-reference.json,pack.yaml,context.md,rules/ads-flow.yaml}; frontend/src/{App.jsx,findingExplanation.js} và web_assetsbuild; tests/{test_audit_depth,test_execution,test_codex_engine,test_claude_engine}.py; README.md, docs/audit-depth-validation.md, SESSION_LOG.md. Giữ các diff cũ/XLSX parser.
- Kiểm tra: RED→GREEN cho badrefs53/63, UNKNOWNexcerpt, điều tra callback, runtimefailclosed, budgetrecovery, cachedUNKNOWNforgedvalid, codex/claude giữreadresults, refcache và attemptlimit. Full151/151đạt, build/JS/rulescheck/diffcheckđạt. Pilot3ruleSolmedium1PASS/1FAIL/1UNKNOWN,18phút2giây/54tools/0cache; docsghi rõ không là speedbenchmark hoặc fullAPKaccuracy. Languageofflinefault đượcreviewvàđọcsource lại, chưa đo runtime.
- XLSX thực: Sheet PA-INN-1-RemoteTV,26rows/23active/3disabled;2strike/1highlight,IDs active không trống. Ban đầu thấy AppID khácAPK nên hỏi, người dùng xác nhận đây là mẫuformat: kiểm mẫu hoàn tất, không dùng để tínhIDverdictIPTV. Không ghi rawID/token vào nhật ký.
- Quyết định/giới hạn: Không épUNKNOWNthànhPASS. IDCSV còn thiếu quan hệ cũ/mới; tinh chỉnh scope tránh đòi remote live và callbackrender không liên quan. Các chỉnhpromptcuối chưa có paidrerun, được kiểm bằng hồi quy; pilotartifact giữ nguyên snapshot và metadata. Rule/model/scope/cache khác lượt cũ nên không suy tốc độ/precision/recall. BoundedAI có thể mất thời gian/quota; không tự tăng model hoặc bỏ trần400.
- Việc còn lại: Restart backend khi dùng web, auditfull11rule với docs thật khi có yêu cầu; runtime/Firebase và sourceSDK thiếu vẫn có thểUNKNOWN. Chưa commit/push.
- Bước tiếp theo: Bàn giao báo cáopilot và cơ chế mới; không chạy thêm AI trả phí ngoài phạm vi kiểm chứng đã xong.

### 2026-10-20 11:21 — Rule tùy chọn, XLSX và giải thích UNKNOWN (Asia/Ho_Chi_Minh)

- Mục tiêu: Theo sửa yêu cầu của người dùng, bỏ inter cuối Onboarding; phần lớn open_resume không dùng khi thiếu ID/tô màu/gạch ngang. Người dùng xác nhận chuyển tài liệu sang XLSX và hỏi ý nghĩa lỗi chưa rõ.
- Trạng thái: Hoàn tất code/tests/build; chưa audit lại APK đối tác, chưa restart/push.
- Đã làm: Thêm normalization trạng thái active/disabled/unknown độc lập isEnable của APK, integration_policy dùng chung inventory và prompt. Điều chỉnh6rule liên quan cùng context, nâng pack0.3.0/promptpolicy. Thêm openpyxl để đọc XLSX, sheet/header/dòng/style; chấp nhận backend/frontend và lưu job qua restart. Giữ CSV/JSON, thêm cột trạng thái và warnings mất định dạng. UI phân biệt nguyên nhân UNKNOWN và sửa mô tả verification chưa đạt; không sửa verdict lịch sử.
- File sửa mới lượt này: apk_audit/placement_policy.py, documents.py, inventory.py, pipeline.py, agent.py, web.py; rulepacks/default/{pack.yaml,context.md,rules/ads-flow.yaml}; frontend/src/{App.jsx,findingExplanation.js,findingExplanation.test.js} và web_assets build; pyproject.toml/uv.lock; tests/{test_documents,test_inventory,test_job_persistence}.py; README.md, docs/base-ads-contract.md, SESSION_LOG.md. Mọi diff cũ được giữ.
- Kiểm tra: Test đỏ trước sửa cho trạng thái CSV/JSON, inventory optional/disabled, uploadXLSX và style/formula. Cuối140/140tests đạt, log/tmp/apk-audit-xlsx-tests-full.log; frontendbuild đạt, log/tmp/apk-audit-xlsx-build.log; JS check/rulescheck/diffcheck đạt. Smoke offline với2XLSX đi hết pipeline engine none, open_resume highlight disabled, inter không báo thiếu. Sandbox test kẹt MCP đã dừng; chạy đầy đủ ngoài sandbox đạt. Build có cảnh báo AntD use-client/chunk như trước. Không coi engine-none smoke là bằng chứng AI kết luận đúng.
- Quyết định/giới hạn: Màu nền ô ID khác trắng/không màu đánh dấu không dùng theo quy ước người dùng; không suy từ màu header/mô tả. Conditional formatting/công thức không được thực thi: cần tài liệu tĩnh để kết luận. XLSX nhiều sheet phù hợp cần file chỉ giữ một sheet; không tự chọn nhầm. Sheets dùng exportXLSX, chưa kết nốiURL. UNKNOWN ở báo cáo cũ không tương đương bug APK; không tự nâng UNKNOWN thành PASS.
- Việc còn lại: Restart backend và audit mới bằng XLSX thực để xác minh chất lượng verdict; các lỗi liên kết claim/evidence hoặc budget của lượt cũ chưa được sửa thuật toán trong lượt này. Chưa commit/push.
- Bước tiếp theo: Người dùng tải.xlsx của ADS SCRIPTS/working file vào web sau khi nạp backend mới.

### 2026-10-20 11:07 — Đọc lượt audit IPTV mới nhất (Asia/Ho_Chi_Minh)

- Mục tiêu: Xem kết quả audit người dùng vừa chạy.
- Trạng thái: Hoàn tất đọc và nhận xét sơ bộ; không triển khai sửa tool hoặc audit lại.
- Đã làm: So metadata jobs và thời gian report; đọc đủ11finding, verification và metrics. Đối chiếu inter_onboarding load/show stub và getter trong workspace với ADS SCRIPTS; đọc config/banner callsite và reference base để ghi giới hạn kết luận reload. Không tải dữ liệu hoặc gửi Sheet.
- Kết quả: Job31f9316735b24c9da4ec41e959e176c2 hoàn tất11:03:32ngày20/10;1PASS/2FAIL/8UNKNOWN,408.44s,67tools,6cache. Engine vẫn Luna;5UNKNOWN có invalid claim/evidence indices/path,Language toolbudget26/25,2UNKNOWN thiếu callsite/coverage. Hai FAIL qua reviewaccepted của tool, không đồng nghĩa chứng minh ngữ nghĩa/runtime.
- File thay đổi lượt này: SESSION_LOG.md.
- Kiểm tra: Đọc report.json/metrics/metadata và các đoạn nguồn liên quan; không chạy tests/build/CLI AI. Không xác minh adfill, UI runtime hoặc Firebase nhận event.
- Việc còn lại: Sửa chất lượng liên kết bằng chứng, xác nhận phạm vi reload Splash và chạy model mới ở lượt sau khi có yêu cầu; giữ mọi thay đổi có sẵn.
- Bước tiếp theo: Trả người dùng tóm tắt, phân biệt lỗi APK có bằng chứng và giới hạn công cụ.

### 2026-10-20 11:00 — Pin Claude Haiku và Codex Sol medium (Asia/Ho_Chi_Minh)

- Mục tiêu: Không dùng Claude default có thể đắt; Codex chuyển đúng6.1Sol/medium.
- Trạng thái: Hoàn tất code/tests/build; chưa live audit bằng hai model mới.
- Đã làm: Kiểm CLI help + localmodelmetadata, tra nguồn chính thức model/effort; chọn claude-haiku-5-5/low, khóa modelallowlist/fallback settings trong invocation; Codex chỉ địnhgpt-6.1-sol và config effortmedium. Chuẩn hóa lỗi Codex bỏ nhãnLuna; detection trả model/effort, doctor lấy engineidentity thực. Cache thêm reasoning_effort; tên report engine phân biệt cả model/effort. Web hiện đúng model mới và giữ tên báo cáo Luna/default cũ; docs cập nhậtdefaults, giữ benchmark cũ có ghi chú lịch sử.
- File thay đổi lượt này: apk_audit/{engines,claude_engine,cache_identity,config,cli}.py; frontend/src/App.jsx và apk_audit/web_assets/app.js; tests/{test_codex_engine,test_claude_engine,test_execution}.py; README.md, docs/audit-optimization.md, docs/audit-optimization-validation.md, SESSION_LOG.md. Giữ mọi diff tối ưu/UI hiện có.
- Kiểm tra: Fake CLI tests trước sửa thất bại đúng do model/effort không được truyền; sau sửa đạt. Cache identity test đổi effort và Claude pin giảm cache miss đạt. Full129/129 test (7.367s), frontend build exit0, diffcheck đạt. Không gửiAPK/docs hay gọi model trả phí trong lượt này.
- Quyết định: Pin Haiku5.5 thay alias haiku/default để không phụ thuộc config người dùng; nếu account không hỗ trợ thì lỗi/UNKNOWN, không nâng model tự động. Không chỉnh config cá nhân hoặc tự đăng nhập. Không xác minh quyền model thực tế bằng request AI. Cần restart server chạy từ code mới.
- Việc còn lại: Người dùng restart và kiểm audit thực; không tự push/commit.
- Bước tiếp theo: Chạy .venv/bin/apk-audit serve --port8765 sau Ctrl+C server cũ.

### 2026-10-19 10:39 — Tách card từng rule trong báo cáo (Asia/Ho_Chi_Minh)

- Mục tiêu: Khắc phục các mục Init/Remote Config và rule khác nhìn dính nhau.
- Trạng thái: Hoàn tất.
- Đã làm: Card riêng cho từng rule, header số thứ tự + tiêu đề + trạng thái; nền/viền/khoảng cách24px; tách body và verification; evidence và collapse thành khối rõ, mobile header/status xuống hàng. Giữ đủ reasoning/claims/evidence trong cùng rule.
- File thay đổi phiên này: frontend/src/App.jsx, frontend/src/style.css, apk_audit/web_assets/app.js, apk_audit/web_assets/app.css, SESSION_LOG.md. Giữ nguyên mọi thay đổi đang có trên nhánh.
- Kiểm tra: Frontend build thành công; React SSR thực tế render2 Finding mẫu Init/Remote Config thành2card và2h4; HTTP assets mới đạt; diff check đạt. Không browser visual QA, không thêm backend test hoặc auditAI cho thay đổi layout.
- Việc còn lại: Người dùng đánh giá trực quan; chưa commit/push.
- Bước tiếp theo: Tải lại web để xem card mới, không cần restart server.

### 2026-10-19 10:08 — Triển khai tối ưu audit và claim verification (Asia/Ho_Chi_Minh)

- Mục tiêu: Thực hiện kế hoạch tối ưu local và kết luận chính xác hơn, người dùng yêu cầu dùng Superpowers.
- Trạng thái: Hoàn tất triển khai, chưa commit/push. Không ghi đè thay đổi SESSION_LOG có sẵn.
- Quy trình: Đọc using-superpowers/writing-plans/executing-plans/TDD, ghi spec/plan/ledger; feature branch; chia3phần độc lập cho agents (index,claims,persistence), root tích hợp scheduler/cache/metrics/benchmark; independent final review và một vòng sửa lỗi có regression. Không tạo worktree/commit khi chưa có yêu cầu cho các thao tác đó.
- File thay đổi: apk_audit/source_index.py, cache_identity.py, execution.py, claim_verifier.py, benchmark.py, quality_cases.json; sửa agent/engine_common/contracts/engines/claude_engine/pipeline/verdict_cache/cli/web/tools/inventory/facts; frontend App.jsx và app.js build; các tests source_index/claims/execution/shared_workspace/benchmark/job_persistence/web/adapters; README, .gitignore, docs và nhật ký. Ledger .superpowers/audit-optimization/progress.md được ignore, giữ tại máy để tiếp nối.
- Đã làm: Chuẩn bị bundle theo rule/placement, chỉ mục compact và cắt vocabulary có metadata; reuse danh sách file đã kiểm trong preprocessing. Claims link evidence, applicability/path/conditions/limitations, review FAIL và candidate có violation hỗ trợ nhưng claim phụ lỗi; strict final guard, UNKNOWN ghi rõ draft chưa chấp nhận. Cache version/model/CLI/policy và checksum, recheck actual excerpts+review trace; checkpoint đủ fingerprint. Scheduler reserve ngân sách, mặc định1worker,tối đa2, crossflow cuối. Web lưu JSON atomic/history/resume chủ động/path validation, giữ report qua refresh. Metrics và benchmark cold/warm/quality.
- Kiểm tra: Baseline51/51; cuối127/127 đạt, frontend build đạt (cảnh báo AntD/chunk/font như trước), quality15/15, diff check đạt, HTTP web đạt. Test mới có cache corruption/forged review trace, CLI version đổi giữa job, worker overlap/budget/order, checkpoint fingerprint, restart/path tamper và cache index bounded/truncated. Reviewer3Important đã sửa; không có Critical hoặc minor deferred được báo.
- Bằng chứng runtime công cụ: Codex thật mẫu static known-fault đi đủ claim+review (FAIL đúng hợp đồng,4tools/38.05s); warmcache0tools. Pilot APK thật Splash đọc59kfile, tách phase facts36.51/index62.49/AI167.47, cuốiUNKNOWN; phát hiện index398MB và bất cập draft. Sửa index xuống16MB, đo v2cold53.63/warm1.85, process peak250100KiB (không phải mỗi phase); preprocessing chia sẻ file list engine none20.24s. Replay candidate/repair thật có reviewerUNKNOWN trong budget25/12/6,total20tools sau chỉnhguard. Không gọi lại full11rule.
- Quyết định: Giữ tất cả source cho AI tìm rộng, lexical index không chứng minh absence/call graph. Tắt verdict reuse Claude khi identity chưa biết; không tự đổi provider/model. Quan sát tooloverrun và báo đúng, không giả hard pre-execution cap. Giữ cache v1/report đầu vào cũ, không rm. Checksum chỉ corruption, không security authenticity. Tài liệu validation ghi rõ phân biệt fixture/replay/live/pilot và policy khác thời điểm.
- Vận hành: Nạp server cuối cổng8765 khi không activejob. Browser automation setup lỗi node:process; dùng HTTP/API+build/test, không tuyên bố visual QA. Chưa commit/push hoặc merge main.
- Việc còn lại ngoài phạm vi lát cắt: Bộ APK groundtruth/accuracy, benchmark freshAI worker1/2, runtimeads/Firebase/smali và Claude live auth. Không hứa tăng tốc tổng theo96%giảm index.
- Bước tiếp theo: Người dùng thử web, rà verdict thật và quyết định commit/push khi sẵn sàng.

### 2026-10-19 09:34 — Phương án tối ưu tốc độ và chất lượng audit (Asia/Ho_Chi_Minh)

- Mục tiêu: Trả lời phương án triển khai để audit nhanh hơn và kết luận đáng tin hơn.
- Trạng thái: Hoàn tất đề xuất, chưa thực thi mã.
- Đã làm: Rà pipeline, tools, facts, unpack, inventory, adapter, agent verifier và verdict cache; đối chiếu pilot IPTV 518.7 giây/76 tool calls. Chỉ ra bộ code reference chưa đi vào context, nhiều lượt scan, phiên AI riêng cho từng rule và thiếu kiểm chứng ngữ nghĩa.
- File thay đổi: SESSION_LOG.md.
- Kiểm tra: Đọc code và report; không chạy lại test/AI, không dùng số pilot có cache khác verdict làm benchmark tương đương.
- Quyết định đề xuất: Ưu tiên baseline + fixture chuẩn, chỉ mục/gói dẫn chứng, claim verification rồi cache/checkpoint và song song hai worker có kiểm soát; thêm smali/DEX theo ca cần giải nghĩa mã lỗi, không dựng bộ symbolic execution toàn APK. Tách nhận định deterministic khỏi AI và chưa chứng minh; giữ hợp đồng ADS SCRIPTS/base được version hóa.
- Việc còn lại: Phương án chưa triển khai; cần benchmark cùng đầu vào và đo thời gian, quota/tokens nếu CLI trả, tài nguyên, repair, precision/recall và UNKNOWN do thiếu dữ liệu so với lỗi hệ thống.
- Bước tiếp theo: Người dùng chọn triển khai lát cắt đầu; chưa commit/push.

### 2026-10-19 09:30 — Kiểm tra lại tiến độ (Asia/Ho_Chi_Minh)

- Mục tiêu: Báo cáo phần đã có, đã kiểm chứng và còn thiếu.
- Trạng thái: Hoàn tất kiểm tra, không sửa mã chức năng.
- Đã làm: Đọc AGENTS/nhật ký, Git và pipeline/API/UI; kiểm bộ luật và công cụ; đối chiếu report pilot thật. Commit code mới nhất 7d439cf, commit nhật ký dce8e0e trên main; không pull/push hoặc chạy audit đối tác mới.
- File thay đổi: SESSION_LOG.md.
- Kiểm tra: Chạy mới 51/51 unittest đạt; rulepack infinity-ads-base-logic 0.2.0 có 11 rule hợp lệ; doctor nhận Java/JADX/Codex/Claude; frontend assets có sẵn. Không kiểm trực quan web, không build lại, không xác nhận auth Claude hiện tại.
- Việc còn lại: Runtime/Firebase live, độ chính xác verdict, Claude live thành công, lưu job qua restart và các mở rộng đã ghi ở trạng thái hiện tại.
- Bước tiếp theo: Ưu tiên kiểm chứng AI và tính bền vững của job trước khi bổ sung chức năng ngoài ads.

### 2026-10-16 17:21 — Push Claude CLI, CSV và UI kết quả (Asia/Ho_Chi_Minh)

- Mục tiêu: Commit/push code theo yêu cầu người dùng.
- Trạng thái: Hoàn tất push code 7d439cf lên origin/main.
- Đã làm: Kiểm remote main cùng HEAD cũ 42a5376; commit toàn bộ sửa CSV, Claude adapter/bộ chọn AI và UI dễ đọc; push SSH thành công, không force push. APK/CSV đối tác và out/ không đưa vào commit.
- File thay đổi: 21 file code/test/assets/docs ở commit 7d439cf; nhật ký xuất bản trong commit tiếp theo.
- Kiểm tra: Chạy mới 51/51 unittest đạt, npm run build exit 0, git diff --cached --check đạt; git push xác nhận main từ 42a5376 lên 7d439cf.
- Việc còn lại: Các giới hạn đã ghi nhận về Claude OAuth/verdict thật, browser automation và nạp prompt sau restart vẫn còn; không thay đổi backend đang chạy trong lượt push.
- Bước tiếp theo: Pull main trên máy khác hoặc tải lại UI local.

### 2026-10-16 17:00 — Làm rõ phần đọc kết quả (Asia/Ho_Chi_Minh)

- Mục tiêu: Khắc phục chữ nhỏ và đoạn reasoning quá dài theo phản hồi người dùng.
- Trạng thái: Hoàn tất UI; prompt mới chờ restart backend để được nạp.
- Đã làm: Tăng typography kết quả; thêm findingText.js nhận các mục reasoning, chia đoạn cũ thành từng câu mà không làm vỡ package/key; nêu câu caveat có sẵn làm ý chính, mở đầy đủ nội dung bằng Collapse; tên code trong backtick hiển thị monospace. Thêm hướng dẫn AI viết tiếng Việt với bốn mục, kết luận trước và giữ điều kiện/giới hạn; không sửa status hoặc dữ liệu report cũ.
- File thay đổi: frontend/src/{App.jsx,style.css,findingText.js}, apk_audit/agent.py, apk_audit/web_assets/{app.js,app.css}, SESSION_LOG.md. Giữ các thay đổi trước.
- Kiểm tra: Frontend build exit 0, 51/51 unittest đạt ngoài sandbox; kiểm Node xác nhận câu cũ ghép lại nguyên nội dung và giữ com.demo.App/config.open_resume, nhận mục mới; HTTP JS/CSS trả bản mới; git diff --check đạt. Lượt test trong sandbox bị dừng ở MCP nên dùng lượt ngoài sandbox làm bằng chứng. Chưa chạy browser automation.
- Vận hành: Giữ server hiện tại và job hoàn tất 565175d1f3f24d65a1be15b63749bfec để tránh reset kết quả trong bộ nhớ; frontend assets cập nhật ngay khi tải lại. Prompt mới được nạp ở lần backend restart tiếp theo; verdict cache cũ giữ nguyên và vẫn đọc được.
- Việc còn lại: Người dùng xem UI; chưa commit/push. Xác thực Claude vẫn chờ đăng nhập lại.
- Bước tiếp theo: Xem trên localhost, chỉ xuất bản mã khi được yêu cầu.

### 2026-10-16 16:51 — Claude CLI và bộ chọn AI trên web (Asia/Ho_Chi_Minh)

- Mục tiêu: Tự phát hiện Codex/Claude trên máy và cho người dùng chọn AI trước khi audit.
- Trạng thái: Hoàn tất triển khai, kiểm thử mô phỏng và xử lý lỗi thực; xác minh verdict Claude thật còn phụ thuộc đăng nhập lại.
- Đã làm: Tách JSON schema/prompt dùng chung; thêm Claude adapter stream-json, chỉ Read/Glob/Grep, safe-mode/restricted, tắt MCP/customization và lưu phiên, giới hạn tool calls/timeout; đưa lỗi xác thực từ stdout vào UNKNOWN. Thêm API detection và header X-Audit-Engine, kiểm engine trước upload/tiêu thụ tài liệu, lưu engine theo job, không fallback provider. UI Ant Design Select và Phát hiện lại, khóa khi đang chạy/thiếu CLI, hiển thị engine của báo cáo và thông tin gửi dữ liệu qua AI. Cập nhật doctor/help/README/kế hoạch.
- File thay đổi: apk_audit/{claude_engine,engine_common,engines,web,config,cli}.py, frontend/src/{App.jsx,style.css}, apk_audit/web_assets/{app.js,app.css}, tests/{test_claude_engine,test_web}.py, README.md, docs/2026-10-16-claude-cli-plan.md, SESSION_LOG.md. Giữ các thay đổi CSV/documents/pipeline/test của phiên trước.
- Kiểm tra: 51/51 unittest đạt; npm run build đạt (cảnh báo bundle AntD/use client/font runtime); git diff --check đạt. HTTP /api/engines nhận cả hai CLI, default codex; trang/assets/Poppins trả 200 và bundle có selector/header/detection. Claude thực gọi trên examples/workspace với một rule, không gửi docs đối tác, trả UNKNOWN do OAuth session expired and could not be refreshed; báo cáo out/claude-cli-smoke/report.json ghi rõ nguyên nhân. Không tự đăng nhập hay lưu thông tin xác thực.
- Vận hành: Kiểm tra job IPTV cũ 96d62344feac491badd2ae0118018ffa đã done trước khi restart server; báo cáo cũ vẫn nằm trong out/web/. Server mới chạy cổng 8765; danh sách job cũ trong bộ nhớ bị reset theo thiết kế hiện có.
- Việc còn lại: Người dùng đăng nhập lại Claude để xác minh verdict thành công trên model thật; chưa kiểm thử giao diện bằng trình duyệt tự động hoặc chạy Claude đủ 11 rule trên APK thật. Cache Claude theo engine default, khi đổi model cần refresh/xóa verdict cache như README. Chưa commit/push.
- Bước tiếp theo: claude auth login, tải lại trang, chọn engine và audit.

### 2026-10-16 16:14 — Sửa CSV IPTV và bước lỗi web (Asia/Ho_Chi_Minh)

- Mục tiêu: Sửa lỗi CSV không đúng mẫu mà người dùng gặp khi audit iptv1_Inative.apk.
- Trạng thái: Hoàn tất sửa, chưa commit/push.
- Nguyên nhân: ADS SCRIPTS có header Tên/Mô tả TV/Mô tả TA/Note/Layout, working file dùng Content/Detail/PIC. Parser trước yêu cầu Name và Phase 2/Task/Task Detail ở vị trí cố định. Web gán stage unpack trước khi đọc tài liệu nên lỗi CSV hiện ở Giải mã.
- Đã làm: Chuẩn hóa header dấu/khoảng trắng/hoa thường; ánh xạ cột theo tên, nhận Name/Tên và Task/Content, Task Detail/Detail; giữ nguyên placement/ID và dữ liệu trong ô; bổ sung thông báo đúng loại tài liệu; thêm stage documents trong pipeline/API/frontend và xử lý stage cả khi lỗi; bỏ số 10 hardcode; cập nhật README; build assets, mở lại server.
- File thay đổi: README.md, SESSION_LOG.md, apk_audit/{documents,pipeline,web}.py, frontend/src/App.jsx, apk_audit/web_assets/app.js, tests/{test_documents,test_integration,test_web}.py.
- Kiểm tra và kết quả: 40/40 unittest đạt; test hồi quy cho hai header mới, đổi thứ tự cột, lỗi CSV dừng ở documents trước khi gọi JADX; npm run build và git diff --check đạt. CLI engine none với đúng ba file upload hoàn tất ~71 giây, 63 placement/23 hàng working, Package và AdMob App ID khớp; report tại out/iptv-csv-fix-smoke/. Web HTTP 200 tại cổng 8765. Không lưu nội dung token trong nhật ký.
- Việc còn lại: Người dùng chọn lại file trên web để chạy AI; chưa audit AI hoặc runtime IPTV trong phiên sửa lỗi. Các giới hạn chung về suy luận AI và job chưa lưu bền vẫn còn.
- Bước tiếp theo: Chạy lại lượt audit trên web; chỉ commit/push bản sửa theo yêu cầu người dùng.

### 2026-10-16 15:29 — Chuẩn bị push cải tiến audit (Asia/Ho_Chi_Minh)

- Mục tiêu: Đưa toàn bộ cải tiến CSV, inventory, bằng chứng, rule và tiến độ web lên GitHub.
- Trạng thái: Hoàn tất; GitHub main nhận commit 6146440.
- Đã làm: Kiểm tra Git main và remote; fetch HTTPS thiếu đăng nhập, fetch trực tiếp SSH thành công; HEAD và main trên remote cùng commit trước khi commit mới.
- File thay đổi: Mã và tài liệu trong lượt triển khai trước, kèm SESSION_LOG.md. APK/CSV đối tác, cache và báo cáo out/ bị Git ignore.
- Kiểm tra: Chạy mới 35/35 unittest đạt; npm run build đạt; git diff --check đạt.
- Kết quả xuất bản: Commit 6146440 (feat: deepen ads audits and show rule progress), push origin main thành công từ 7163042 lên 6146440. Nhật ký xác nhận được commit riêng sau mã.
- Bước tiếp theo: Pull main trên máy khác để nhận mã mới; các phần runtime và job bền vững vẫn theo kế hoạch.

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
