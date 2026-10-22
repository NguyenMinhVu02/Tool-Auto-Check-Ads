# apk-audit — tài liệu kỹ thuật chi tiết

> Bản đầy đủ dành cho dev (cơ chế, giới hạn, cấu hình). Hướng dẫn dùng nhanh nằm ở [README](../README.md).

Khung CLI audit APK theo thiết kế v2. Bộ luật mặc định hiện chứa chuẩn **logic ads/init** rút từ `Example-AdLogic-Partner` tại commit `e8f4337` (xem [hợp đồng tham chiếu](docs/base-ads-contract.md)). Mặc định Codex CLI dùng `gpt-6.1-sol` (reasoning `medium`) đọc workspace đã giải mã và đánh giá 11 luật logic, gồm một lượt rà lỗi giao thoa giữa các luồng ads; cần cài và đăng nhập Codex CLI. Có thể chọn Claude CLI bằng `--engine claude` hoặc bộ chọn AI trên web. `--engine none` tắt AI và trả `UNKNOWN`. ID ads của base không dùng làm ID kỳ vọng cho app đối tác.

## Chạy ngay

```bash
cd /home/infinity01/Tools/apk-audit
uv sync --extra mcp
uv run apk-audit --help
uv run apk-audit doctor
codex login status
uv run apk-audit examples/workspace --out out/demo
```

Kết quả: `out/demo/facts.json`, `xref_index.json`, `inventory.json`, `report.md`, `report.json`.
Workspace mẫu chỉ chứa dữ liệu minh họa, không phải APK/app thật.

## Tối ưu audit và kiểm chứng nhận định

Đã thêm chỉ mục mã/gói dẫn chứng theo rule, claim guard + review FAIL, metrics, checkpoint, lịch sử job bền và tùy chọn `--workers 2`. Xem [cơ chế, lệnh và giới hạn](docs/audit-optimization.md). `benchmark --quality` chạy bộ ca tổng hợp offline; `benchmark <target>` đo cold/warm, engine mặc định `none` để không tự gọi AI.

## Tóm tắt cho Marketing

Đầu báo cáo (web và `report.md`) có mục **Tóm tắt cho Marketing** cho 4 màn đầu: Splash, chọn ngôn ngữ, Onboarding, Welcome back/App Open. Mỗi màn có bảng vị trí quảng cáo với ID trong ADS SCRIPTS, ID trong app (`ad_config.json`) và tình trạng (Đúng ID / Sai ID / Thiếu / Không dùng), cộng kết luận luồng quảng cáo bằng lời dễ hiểu (`marketing_summary` do AI viết, không tên class/hàm). Phần đối chiếu ID là tất định, không phụ thuộc AI. Tool cũng báo khi toàn bộ ID trong app thuộc tài khoản AdMob khác ADS SCRIPTS.

## Báo cáo cho Marketing và Dev

Trang kết quả có hai tab. **Marketing**: danh sách ID ads lỗi, bảng ID tài liệu/ID app theo từng màn, nút copy danh sách, tải CSV (`/api/jobs/<id>/ids.csv`) và báo cáo HTML một file (`/api/jobs/<id>/report.html`). **Dev**: rule gom theo màn với kết luận một dòng, mục "Cần sửa", vị trí `file:dòng`, lý do UNKNOWN bằng lời thường; bằng chứng đầy đủ gập lại. Nhãn chung: Đạt / Cần sửa / Cần dev xem lại / Không áp dụng. `report.md` theo cùng cấu trúc. Metrics hiện token từng rule (đọc cache/ghi cache/đầu ra).

Mỗi màn trong tab Marketing còn có **Logic hiện tại** (app tải quảng cáo khi nào, hiển thị khi nào, lỗi/offline/hết thời gian thì làm gì) và **Đã đúng yêu cầu chưa?** (✅ đúng, ❌ chưa đúng, ❔ chưa đủ căn cứ, ➖ không áp dụng) theo checklist khai báo trong `params.checklist` của rule Splash/Language/Onboarding/Welcome. Phần này do AI viết bằng lời thường (`screen_report`); khi kết luận rule bị tool hạ xuống "Cần dev xem lại" vì dẫn chứng không đủ, mọi mục đều hiện ❔ và logic ghi "chưa xác minh đủ".

## Rule tĩnh (không tốn token AI)

`ADS_CONFIG_FLAGS` (isEnable theo ADS SCRIPTS, enableUaCheck chỉ true cho 4 native full screen Onboarding), `ADS_LANGUAGE_DEV_TOGGLE`, `ADS_DEBUG_TEST_IDS` (`ad_config_debug.json` phải dùng ID test của Google đúng loại, vị trí tắt được để trống, `ad_config.json` không được dùng ID test), `ADS_REMOTE_KEYS` (key Remote Config bắt buộc có trong mã app), `ADS_INTERSTITIAL_INTERVAL` (35 giây), `ADS_SCREEN_NAMES` (tên 4 Activity đầu), `ADS_SCREEN_ORIENTATION` (4 màn đầu phải khóa hướng `android:screenOrientation` portrait/sensorPortrait/userPortrait/reversePortrait/locked trong manifest). Rule `welcome`/`banner` được đánh dấu **Không áp dụng** và không gọi AI khi ADS SCRIPTS xác định không dùng placement tương ứng. Rule ID chỉ còn kiểm nguồn ID trong code; so sánh ID với tài liệu do kiểm kê tất định đảm nhiệm.

## Bỏ qua rule đã đạt ở bản trước

Rule khai báo `params: {skip_after_pass: true}` (hiện chưa có rule nào dùng; rule Firebase tracking đã bị gỡ khỏi bộ luật 0.8.0 theo yêu cầu) sẽ được đánh dấu **Không áp dụng**, không gọi AI, khi cùng app (cùng package) đã **Đạt** ở một bản build khác trước đó. Lịch sử lưu ở `<cache>/passed/<package>.json`, tự dựng lại từ các `report.json` đã có khi khởi động web. Một kết quả Cần sửa/Cần dev xem lại về sau xóa dấu "đã đạt". Chọn **Kiểm lại cả rule đã đạt ở bản trước** trên web hoặc `--recheck-all` ở CLI để chạy lại. Đây là đánh đổi có chủ đích: code Firebase đổi ở bản sau sẽ không bị kiểm lại.

## Dùng lại kết quả theo file liên quan

Ngoài cache theo toàn APK, verdict PASS/FAIL còn được lập chỉ mục theo các file/thư mục mà AI đã đọc hoặc tìm (`apk_audit/scoped_cache.py`). Bản build mới dùng lại verdict nếu: cùng rule/pack/engine/policy và tài liệu/kiểm kê đã lọc; **tập đường dẫn file đã giải mã không đổi**; mọi file/thư mục AI đã chạm có nội dung giống hệt; bằng chứng vẫn khớp nguồn mới. Tìm kiếm toàn workspace, lệnh bị cắt hoặc đường dẫn không xác định thì không dùng lại. **Giới hạn:** sửa một file AI không đọc (nhưng có thể ảnh hưởng kết luận) không bị phát hiện; dùng `--no-scoped-cache` khi cần audit lại hoàn toàn. UNKNOWN và rule rà lỗi chéo không dùng cơ chế này.

## Dẫn chứng theo đoạn dòng (giảm lượt sửa bằng chứng)

AI không còn phải chép lại đoạn code. Mỗi dẫn chứng là `file`, `line`, `end_line` (1–40 dòng, prompt yêu cầu 1–8) và `anchor`, một cụm ngắn nguyên văn nằm trong đoạn đó. Tool kiểm tra file/đoạn tồn tại và anchor (bỏ khoảng trắng) có trong đoạn, rồi **tự lấy mã nguồn thật** làm excerpt trong báo cáo, nên chữ AI viết lại/tóm tắt không đến được người đọc. Vì sao: 27/28 dẫn chứng bị loại của Codex low là do viết lại đoạn code dài trong khi dòng được dẫn vẫn đúng; mô phỏng trên 32 dẫn chứng bị loại thật (Codex low + Sonnet) cho thấy cả 32 sẽ được xác minh ở dạng này. Đánh đổi: không còn bằng chứng rằng AI đã "nhìn thấy" nguyên văn cả đoạn, chỉ anchor ngắn; kết luận vẫn cần claims, kiểm cấu trúc và review FAIL. Để bù phần đánh đổi: lượt review kết quả Cần sửa nhận **mã nguồn thật** của từng đoạn dòng được dẫn (`source_text`) và được yêu cầu loại claim mà các dòng đó không thể hiện, kể cả khi anchor khớp; anchor của claim violation phải là cụm đặc trưng từ 12 ký tự. Excerpt dạng cũ vẫn được kiểm chặt như trước (replay, benchmark, cache cũ).

## Tiết kiệm token

- Claude dùng Sonnet 5.5 effort `low`; lượt sửa bằng chứng/điều tra **nối tiếp phiên của rule** (`--session-id`/`--resume`) nên không gửi lại toàn bộ prompt; review FAIL vẫn mở phiên mới để đánh giá độc lập. Resume lỗi thì tự chạy lại bằng prompt đầy đủ. Transcript phiên bị xóa khi rule xong.
- Phần prompt chung đặt trước, số ngân sách từng lượt đặt cuối để giữ tiền tố chung cho prompt cache.
- Mỗi rule chỉ nhận placement/checklist/tham chiếu code liên quan (`context_scope.py`), bản đồ luồng quảng cáo dựng sẵn (`flow_map.py`), gợi ý code tối đa 12000 ký tự; schema không lặp trong prompt của CLI. Đo bằng replay: prompt mỗi rule giảm khoảng 40% so với trước (≈83KB → 43–52KB).
- Rule rà lỗi chéo `ADS_CROSS_FLOW_BUGS` **tắt mặc định**; bật bằng ô chọn trên web hoặc `--cross-flow`.

## Web localhost

```bash
uv run apk-audit serve
```

Mở `http://127.0.0.1:8765`, chọn hoặc kéo APK/XAPK/APKM vào vùng tải lên, rồi bấm **Bắt đầu kiểm tra**. Chọn file không tự chạy. Hai ô ADS SCRIPTS và working file là tùy chọn: chỉ khi chọn **đủ cả hai**, web mới đưa chúng vào pipeline; thiếu một file thì bỏ qua cả cặp. Mỗi tài liệu nhận XLSX, JSON object, CSV hai cột `key,value`, hoặc bảng ADS SCRIPTS/working file của Infinity, tối đa 5 MiB. ADS SCRIPTS nhận các cột `Ads type`, `Name` hoặc `Tên`, `ID`; đọc theo tên cột nên có thể đổi thứ tự. Working file nhận cả `Task/Task Detail` và `Content/Detail`. Header được chuẩn hóa dấu/khoảng trắng/hoa thường; tên placement và giá trị trong ô được giữ nguyên. Web đọc tài liệu trước khi giải mã và hiển thị riêng bước lỗi tài liệu. Web dùng font Poppins lưu sẵn trong gói để chạy offline; giấy phép ở `apk_audit/web_assets/fonts/OFL.txt`.

Trang lưu file đã tải, báo cáo và cache dưới `out/web/`, sau đó hiển thị kiểm kê ID, tổng quan và từng luật. Khi chạy, web hiển thị bước hiện tại và trong bước đối chiếu hiển thị số rule đã xong, rule đang chạy và kết quả gần nhất. Kết quả của rule không đổi được dùng lại từ cache ở lượt sau; sửa một rule không xóa cache các rule khác. Lượt đầu vẫn có thể mất nhiều phút vì AI đọc JADX tuần tự. Trình duyệt hỏi xác nhận nếu đóng tab, Back hoặc Reload trong lúc lượt kiểm tra đang chạy. Nếu vẫn Reload, trang lấy lại trạng thái lượt kiểm tra từ server. Job mới được lưu nguyên tử trên disk; sau restart có lịch sử và nút Tiếp tục cho lượt gián đoạn. Resume chỉ dùng kết quả đã hoàn tất khi fingerprint/cache/checkpoint còn hợp lệ, không tự chạy AI sau restart. Server chỉ lắng nghe trên `127.0.0.1`, xử lý một file tại một thời điểm (web mặc định chạy 4 rule đồng thời, chỉnh bằng `apk-audit serve --workers 1-10`; CLI `audit` mặc định 1); dùng `Ctrl+C` để dừng. Có thể đổi cổng/thư mục bằng `--port` và `--out`, hoặc trỏ bộ luật bằng `--rules`.

### Placement tùy chọn và ADS SCRIPTS có định dạng

- **Inter cuối Onboarding không bắt buộc**, kể cả tài liệu cũ còn `inter_onboarding`. Thiếu/tắt/stub của slot này không phải lý do FAIL; nếu app thực sự dùng thì vẫn kiểm gate và điều hướng.
- **Open Resume chỉ bắt buộc khi tài liệu xác định đang dùng và có ID.** Thiếu dòng `open_resume`, ID trống hoặc đánh dấu không dùng cho phép tắt App Open. Không lấy cờ `isEnable` trong APK làm trạng thái yêu cầu của tài liệu.
- Web và CLI hỗ trợ **XLSX** cho cả hai tài liệu, tối đa 5 MiB/file trên web. Trong Google Sheets chọn **Tệp → Tải xuống → Microsoft Excel (.xlsx)**. Tool đọc màu nền trực tiếp của **ô ID** (không tính trắng/không màu) và gạch ngang ở **ô tên hoặc ID** thành trạng thái không dùng. Theo quy ước này, mọi màu nền khác trắng trên ô ID đều đánh dấu không dùng; không suy từ màu header/cột mô tả.
- XLSX chọn sheet có header phù hợp trong 40 dòng đầu, giữ số dòng và tên sheet. Workbook nhiều app (nhiều sheet cùng mẫu): web hiện dropdown chọn sheet cho từng tài liệu ngay sau khi chọn file và khóa nút bắt đầu tới khi chọn đủ; CLI dùng `--ads-sheet`/`--checklist-sheet`. Sheet đã chọn được lưu trong job để resume. Giới hạn 20000 dòng/256 cột và 100 MiB sau giải nén. Không thực thi công thức; ID công thức hoặc vùng conditional formatting chưa xác định được trạng thái sẽ ghi `unknown`.
- CSV tự tìm header phù hợp trong 40 dòng đầu, bỏ qua dòng tiêu đề/giới thiệu phía trên và giữ số dòng nguồn (kể cả ô nhiều dòng). ADS SCRIPTS và working file phải thuộc cùng ứng dụng và tải đúng ô tương ứng.
- Parser nhận dấu phẩy/chấm phẩy/tab/pipe và tên cột tương đương như `Loại quảng cáo`, `Vị trí`, `Ad Unit ID`, `Nội dung`, `Chi tiết`. Nếu vẫn chưa hiểu cấu trúc, pipeline tự dùng **Codex/Claude đang chọn** để ánh xạ cột: một lần/tài liệu, tối đa 90 giây, preview giới hạn 40 dòng/64 cột/30000 ký tự (mỗi ô tối đa 120 ký tự). Không gọi AI ở bước tài liệu khi parser đã hiểu mẫu, `--static-only`, `--engine none` hoặc `--max-tool-calls 0`.
- AI chỉ đề xuất chỉ số dòng/cột; loader kiểm tọa độ và cột bắt buộc rồi lấy giá trị từ file gốc, giữ ID và định dạng XLSX. Không tạo ID hoặc tự sửa dữ liệu. Nhiều sheet ứng dụng vẫn cần chọn/tách đúng sheet; chưa có dropdown. Khi AI không chắc, lỗi đăng nhập/quá thời gian hoặc ánh xạ không hợp lệ, bước tài liệu báo lỗi và chưa giải mã APK. Mapping là hỗ trợ nhận dạng, không phải chứng minh AI luôn hiểu đúng ý nghĩa tài liệu. Báo cáo web có mục **Tài liệu đã đọc**; `metrics.documents` ghi phương pháp, số dòng và AI usage nếu CLI cung cấp. Chi phí/latency của lượt ánh xạ là riêng với các lượt đánh giá rule.
- CSV mất màu/gạch ngang: thêm `Status`/`Trạng thái` hoặc `Enabled` (`Enabled`/`TRUE` là dùng; `Disabled`/`FALSE`/`Không dùng` là tắt). Cũng hỗ trợ cột `Strikethrough`/`Gạch ngang`, `Highlighted`/`Bôi màu` dạng TRUE/FALSE. `open_resume` có ID nhưng CSV thiếu trạng thái sẽ không bị ép phải bật và cần bổ sung tài liệu.
- JSON dạng `placements` hỗ trợ `enabled`, `status`, `strikethrough`, `highlighted`. Placement disabled/unknown không bị báo thiếu local hoặc ID lệch; inventory vẫn liệt kê riêng để đối chiếu. Rule pack mới là **0.4.0**; thay đổi context/policy làm mất hiệu lực verdict cache cũ mà không xóa lịch sử báo cáo.

**UNKNOWN / Chưa đủ căn cứ** không có nghĩa APK có lỗi: giao diện phân biệt hết ngân sách đọc code, lỗi kiểm chứng đoạn trích/liên kết nhận định, lỗi CLI và thiếu đường gọi/điều kiện để kết luận. Sửa tài liệu/rule không tự sửa kết quả lịch sử; cần lượt audit mới sau khi khởi động lại backend.

### AI đọc sâu và xử lý kết quả chưa đủ căn cứ

1. Mỗi rule nhận **đoạn code base riêng**, mục tiêu kiểm tĩnh, các đường cần lần và các điểm khác biệt đã biết. Snapshot nằm trong `rulepacks/default/base-reference.json`, có commit và hash source, chạy được trên máy khác mà không cần checkout base. Code mẫu chỉ giải thích logic; bằng chứng PASS/FAIL phải đến từ APK.
2. AI đọc workspace với **GPT-6 Sol / low** hoặc Claude Sonnet 5.5 / low. Với native CLI và ngân sách rule từ 20 trở lên, lượt đầu dùng khoảng 60%, dành phần còn lại cho sửa bằng chứng, điều tra hoặc review. Các rule mặc định có tổng ngân sách riêng 35–45 lượt; trần toàn audit vẫn là 400 lượt quan sát được.
3. Sai excerpt hoặc số liên kết claim/path được gửi lại AI cùng bảng chỉ số evidence và source quanh dòng lỗi. Tool không tự đổi số, xóa blocker hoặc coi excerpt khớp là chứng minh ngữ nghĩa.
4. UNKNOWN có blocker/nhận định chưa chắc được **một lượt điều tra bổ sung có mục tiêu** nếu còn ngân sách: mở helper/lambda/callback/getter còn thiếu, theo phạm vi rule tĩnh. Nếu lượt đầu bị ngắt vì hết phần ngân sách riêng, lần tiếp theo nhận các kết quả đọc gần nhất đã giữ lại, tối đa khoảng 18 KB; không nhận kết luận từ lượt bị ngắt.
5. Sau điều tra, kết quả mới vẫn qua guard evidence/claims; FAIL phải có review. Thiếu SDK/dữ liệu thực sự quyết định kết luận hoặc chưa đo hành vi runtime thì vẫn UNKNOWN. UNKNOWN có bằng chứng/claim không hợp lệ không được cache lại hoặc phục hồi từ checkpoint.

Metrics trên web/JSON ghi số lượt sửa bằng chứng, điều tra bổ sung, review và nguồn base. Đọc kỹ hơn có thể tốn thêm thời gian/quota; không tự đổi model, tăng effort hoặc bỏ trần ngân sách. Chỉ số tool dùng cơ chế quan sát CLI, có thể biết một lượt vượt ngưỡng sau khi nó đã bắt đầu; phần vượt được ghi rõ và không dùng verdict từ lần gọi bị ngắt.

Để tạo lại snapshot từ đúng commit đã review:

```bash
.venv/bin/python scripts/snapshot_base_reference.py /path/to/Example-AdLogic-Partner
```

Script dừng nếu base đổi commit hoặc source liên quan có diff; cần review lại ranges/caveats trước khi nâng commit. Theo base hiện tại, vòng reload banner thuộc `BaseActivityWithBanner`; Splash load một lần không đủ làm FAIL nếu chưa chứng minh có yêu cầu reload riêng.

Giao diện dùng React và các component Ant Design; font Poppins được phục vụ từ gói local. Mã frontend nằm trong `frontend/`, bản build phục vụ offline nằm trong `apk_audit/web_assets/`. Sau khi sửa frontend, chạy `cd frontend && npm ci && npm run build`; người dùng web không cần cài Node.js. Web tự phát hiện Codex/Claude CLI trên PATH của máy chạy server. Ô **AI dùng để audit** cho chọn engine, nút **Phát hiện lại** quét lại CLI; nếu có cả hai thì chọn Codex trước, chỉ có Claude thì chọn Claude. Nếu vừa sửa PATH, khởi động lại server từ terminal nhận PATH mới. Thiếu CLI thì nút bắt đầu bị khóa. Phát hiện binary không xác nhận đăng nhập hay quota. Codex dùng `gpt-6.1-sol` (reasoning `medium`), Claude cố định `claude-sonnet-5-5` với effort `low`; truyền rõ model/effort, chỉ cho phép model này và tắt fallback để không tự tăng chi phí. Engine được cố định theo từng job, không tự chuyển provider khi lỗi. Cả hai chạy phiên chỉ đọc cho từng luật, có giới hạn thời gian và số lần gọi công cụ; mọi evidence được dẫn phải khớp file/dòng trước khi nhận `PASS` hoặc `FAIL`. Nội dung mã và tài liệu cần thiết được gửi tới nhà cung cấp AI đã chọn qua CLI; lượt audit có thể dùng quota/tính phí theo tài khoản. Native AI phải cung cấp claims/điều kiện và dẫn chứng; FAIL có thêm lượt review trong cùng ngân sách. Checker không tự chứng minh ngữ nghĩa hoặc runtime. Nếu thiếu bằng chứng hoặc CLI lỗi, luật trả `UNKNOWN`. File cần `jadx` và Java như CLI. Trang chỉ nhận file có đuôi `.apk`, `.xapk`, `.apkm`; nội dung archive vẫn được kiểm tra trước khi giải mã.

### Dùng Claude CLI

Cài Claude Code CLI trên máy chạy backend rồi đăng nhập từ terminal:

```bash
claude --version
claude auth login
claude auth status
uv run apk-audit doctor
uv run apk-audit audit /path/to/app.apk --engine claude --out out/claude-app
```

Trên web: tải lại trang, bấm **Phát hiện lại**, chọn **Claude CLI**, chọn APK/tài liệu và bấm **Bắt đầu kiểm tra**. Tool luôn truyền `--model claude-sonnet-5-5 --effort low`, không dùng model mặc định trong cấu hình cá nhân. Khi OAuth hết hạn, đăng nhập lại rồi chạy lượt mới. Không nhập tài khoản hay API key vào web. Việc cài extension Claude/Antigravity trong IDE không tự tạo CLI `claude` trên PATH.

Đọc APK có sẵn (cần Java và jadx trên PATH, hoặc biến `JADX_PATH`):

```bash
uv run apk-audit /path/to/app.apk --out out/app
uv run apk-audit /path/to/app.xapk --out out/app
uv run apk-audit facts /path/to/app.apk
```

Tool gọi jadx trên bản gốc chỉ để đọc. XAPK/APKM được kiểm tra đường dẫn ZIP rồi đưa tất cả APK con cho jadx. Không cài/chạy app. Workspace bung lưu theo SHA256 trong cache; `--no-cache` tạo lượt bung mới. Mặc định cache lấy từ `platformdirs`; `--cache-dir` cho phép đổi vị trí.

Có thể truyền thẳng thư mục jadx đã bung. `--out` phải nằm ngoài thư mục đầu vào để không sửa dữ liệu đang phân tích.

## Chuẩn ads/init hiện có và cách bổ sung

Chỉnh ba nơi trong `rulepacks/default/`:

1. `context.md`: kiến trúc và luồng tham chiếu từ base; bổ sung khi base đổi logic.
2. `extract.yaml`: regex chuỗi cần tìm và tiền tố package cần thống kê.
3. `rules/*.yaml`: 10 câu hỏi logic hoặc các luật static bổ sung.

Từ thư mục dự án, tool tự nạp `rulepacks/default/`. Khi chạy ở nơi khác, truyền đường dẫn tuyệt đối bằng `--rules`. Nếu không tìm thấy bộ mặc định, dùng bộ rỗng có cảnh báo; đường dẫn `--rules` sai sẽ báo lỗi. Muốn đối chiếu ID thật cần tài liệu ADS SCRIPTS riêng của app qua `--ads-scripts`; muốn đối chiếu package/tokens cần working checklist qua `--checklist`. Tài liệu hỗ trợ JSON object hoặc CSV `key,value`; Codex đánh giá logic và dẫn bằng chứng từ workspace.

```bash
uv run apk-audit rules check --rules rulepacks/default
uv run apk-audit rules list --rules rulepacks/default
uv run apk-audit examples/workspace --rules rulepacks/default --out out/demo
```

Mỗi file luật là một **danh sách YAML**. Ví dụ tổng quát bên dưới chỉ minh họa cú pháp, không phải chuẩn quảng cáo:

```yaml
- id: EXAMPLE_CONFIG
  title: Đối chiếu giá trị cấu hình
  mode: static
  area: configuration
  check: manifest_meta
  params:
    key: example.config
    equals: expected-value
  on_missing: unknown
  hint: Xem resources/AndroidManifest.xml
```

Bảy phép kiểm tra tổng quát:

| check | params bắt buộc | So sánh |
|---|---|---|
| `manifest_meta` | `key` | `equals`, `equals_doc` hoặc `regex` |
| `manifest_has` | `collection`, `name` | Tên component có mặt |
| `string_present` | `key` | Candidate có mặt; lọc thêm `equals`/`regex` |
| `string_absent` | `key` | Candidate không có mặt; lọc thêm `equals`/`regex` |
| `asset_json_path` | `file`, `path` | Đường dẫn có giá trị, kể cả `false` |
| `asset_json_match` | `file`, `path` | `equals`, `equals_doc` hoặc `regex` |
| `sdk_version` | `key`, `min` | So phiên bản số; extractor SDK chưa nối nên mặc định UNKNOWN |

`key` của string là tên trong `extract.yaml:string_patterns`.
`file` của JSON là tên tương đối bên trong assets, ví dụ `config.json`.
JSONPath hỗ trợ `$.a.b`, `items[0].id`, `["key.with.dots"]`; chưa hỗ trợ wildcard/filter.
Toàn bộ JSON assets được đọc; `asset_json` được giữ trong cấu trúc extract để mở rộng chọn lọc sau.
Chuỗi hiện lấy từ text đã decode, chưa phải DEX string pool. Các trường SDK/ID chuyên biệt giữ trống; không suy đoán nghiệp vụ.

Luật agent khai báo `question`, `verdict.pass_when`, `verdict.fail_when`, `verdict.unknown_when`, `start_hints`, `budget.max_tool_calls`. Viết các tiêu chí dạng chuỗi (đặt dấu nháy nếu là `yes/no`). Dùng `--engine none` sẽ trả UNKNOWN với lý do engine_disabled.

Tài liệu đầu vào hỗ trợ JSON object, CSV **key,value** hoặc đúng hai mẫu bảng Infinity qua `--ads-scripts` / `--checklist`; đối chiếu bằng `equals_doc: ads_scripts.some_key`. Với ADS SCRIPTS dạng bảng, tool tạo `placements`, đối chiếu số key và ID trong `ad_config.json`, so AdMob App ID với manifest, so Package với working file, rồi lưu vị trí chuỗi placement và nguồn config trong Java giải mã vào `inventory.json`. Vị trí chuỗi không chứng minh ad đã load/show. Cột Status của working file chỉ là dữ liệu tiến độ trong tài liệu, không phải verdict audit. Chưa đọc URL Google Sheets. Thiếu key/tài liệu trả SKIPPED.

## MCP chỉ đọc

```bash
uv run apk-audit mcp --workspace /absolute/path/to/jadx-workspace
```

Chín tool: `get_facts`, `list_classes`, `search_classes`, `get_class`, `get_smali`, `get_methods`, `xrefs_to`, `grep`, `read_lines`.
`get_facts` giới hạn phản hồi 64 KiB; cần truyền `path` hẹp hơn khi vượt giới hạn.
`xrefs_to` dùng `method` hoặc `class_name`, dựa trên chỉ mục lệnh invoke smali. Thiếu smali trả `available: false`; không coi là không có lời gọi. `get_methods` chỉ nhận dạng khai báo Java theo mẫu, không phải parser hoàn chỉnh.

Cấu hình MCP cho client dùng JSON:

```json
{
  "mcpServers": {
    "apk_audit": {
      "command": "/absolute/path/to/apk-audit/.venv/bin/python",
      "args": ["-m", "apk_audit", "mcp", "--workspace", "/absolute/path/to/workspace"]
    }
  }
}
```

Windows dùng `.venv/Scripts/python.exe`. Server không chỉnh cấu hình toàn cục của client. Cách đăng ký tool và chạy stdio theo [tài liệu FastMCP](https://gofastmcp.com/deployment/running-server).

## Chỗ nối tích hợp

- `fetch.py:DownloadProvider`: adapter tải APK. Hiện link Play được parse package, rồi báo rõ chưa nối provider. Không scrape giả hoặc vượt CAPTCHA.
- `engines.py:Engine`: nhận prompt, bộ tools, ngân sách; trả `AgentResult`. `CodexEngine` gọi Codex CLI với `gpt-6.1-sol` (reasoning `medium`), phiên chỉ đọc và đầu ra JSON có schema; `none` và `replay` dùng cho kiểm thử/offline. `ClaudeEngine` gọi Claude CLI với JSON schema, chỉ cấp Read/Glob/Grep, tắt customization và MCP, không lưu phiên hội thoại. Cần bản Claude CLI hỗ trợ `--safe-mode`, `--restricted`, `--json-schema`, `--no-session-persistence`; nếu CLI cũ không nhận cờ, cập nhật CLI trước.
- `agent.py`: dựng prompt, thử lại JSON hỏng một lần, kiểm tra ID/status/ngân sách, mở file xác minh evidence. PASS/FAIL thiếu bằng chứng hợp lệ trở thành UNKNOWN.
- `verdict_cache.py`: khóa gồm APK/workspace, pack context/extract, từng luật, engine, tài liệu và phiên bản tool; rule rà giao thoa thêm kết quả các rule trước. Cache lưu prompt và trace. Hai adapter đếm lời gọi công cụ từ event JSONL và dừng khi quá ngân sách. Cache/checkpoint tách theo model và reasoning effort; model/CLI version chưa xác định thì không reuse verdict. Claude Haiku đã được chỉ định rõ nên có thể reuse khi CLI version được xác định. Cache có fingerprint prompt/schema/verifier/engine identity và revalidate khi đọc.
- `unpack.py`: nhận dữ liệu jadx, lưu mã thoát và log. Chưa nối baksmali; có thể cung cấp workspace đã có thư mục `smali/`.
- `apk_audit.run(...)`: API chung cho CLI và các cửa vào tương lai.

Chưa triển khai: tải tự động apkcombo/apkpure, lấy version từ Play, nhóm phiên AI theo area, phát hiện mọi bug Java ngoài luồng ads, `ask` và skill `/audit-play`. Đã chạy pilot tĩnh với Cast TV nhưng chưa kiểm chứng runtime request/show ad và Firebase. Mã thoát 0 chỉ nghĩa không có FAIL, không bảo đảm mọi luật PASS.

## Kiểm thử

```bash
uv run --extra mcp python -m unittest discover -s tests -v
```

Kiểm thử trên workspace giả lập, static checks, cache, evidence, path traversal, CLI, web và MCP. Bộ test mở rộng có fixture claim/review tổng hợp, scheduler/cache/index và persistence; xem nhật ký phiên để biết số test chạy gần nhất và smoke AI thật. MCP stdio và web được kiểm tra ngoài sandbox vì sandbox chặn socket localhost. Đã có pilot APK đối tác trên Linux; chưa xác nhận Windows/macOS hoặc accuracy trên tập APK chuẩn.

Thư viện được khóa trong `uv.lock`. Thiết kế gốc: `docs/2026-09-10-apk-audit-design.md`; phạm vi bản khung: `docs/implementation-plan.md`.

### Cấu hình model từ 2026-10-20

- Codex: `gpt-6-sol`, `model_reasoning_effort="low"`.
- Claude: `claude-sonnet-5-5`, effort `low`, model allowlist chỉ chứa Sonnet 5.5 và fallback rỗng. Nếu model không khả dụng thì báo lỗi/UNKNOWN, không tự chuyển lên Sonnet/Opus.
- Model/effort được đưa vào tên engine, report và khóa cache. Cache Luna/model mặc định cũ không được dùng lẫn. Sau khi cập nhật code cần restart server để nạp cấu hình mới.
- Chọn model rẻ hơn làm thay đổi đơn giá, không đảm bảo ít token hơn hoặc giá của gói CLI cụ thể. Giá API và giới hạn xem [Haiku5.5](https://platform.claude.com/docs/en/models/haiku-5-5/overview), cấu hình effort xem [Codex config](https://developers.openai.com/codex/config-reference/).
