# APK Audit

Công cụ kiểm tra tự động cách một app Android tích hợp quảng cáo Infinity: **ID quảng cáo có đúng không, 4 màn đầu (Splash, Language, Onboarding, Welcome) tải và hiển thị quảng cáo có đúng yêu cầu không**. Chạy trên máy cá nhân, kết quả là báo cáo dễ đọc cho cả Marketing và Dev.

## Dùng nhanh (cho Marketing)

1. Nhờ dev chạy `uv run apk-audit serve`, rồi mở **http://127.0.0.1:8765**.
2. Kéo file **APK / XAPK / APKM** vào ô tải lên.
3. *(Khuyến nghị)* Chọn **ADS SCRIPTS** và **working file** của đúng app đó (XLSX hoặc CSV). Phải chọn đủ cả hai. Workbook nhiều app thì chọn đúng sheet ở ô hiện ra bên dưới.
4. Chọn AI (**Claude CLI** hoặc **Codex CLI**) rồi bấm **Bắt đầu kiểm tra**. Mỗi lượt thường mất vài phút.

## Đọc báo cáo

| Biểu tượng | Ý nghĩa |
|---|---|
| ✅ Đạt | Đúng yêu cầu, có bằng chứng trong code |
| ❌ Cần sửa | Sai yêu cầu, báo dev kèm vị trí code |
| ❔ Cần dev xem lại | Chưa đủ căn cứ để kết luận. **Không có nghĩa app lỗi** |
| ➖ Không áp dụng | Tài liệu xác định không dùng phần này |

- **Tab Marketing:** danh sách **ID ads sai/thiếu** theo từng màn (ID trong tài liệu so với ID trong app); với mỗi màn có *logic hiện tại* (tải khi nào, hiện khi nào, lỗi thì làm gì) và *danh sách yêu cầu đã đúng chưa*. Có nút **Copy danh sách ID lỗi**, **Tải CSV**, **Báo cáo HTML** (một file, gửi được cho người khác).
- **Tab Dev:** kết luận từng rule theo màn, mục *Cần sửa*, vị trí `file:dòng`, bằng chứng và thông số chạy (thời gian, token).

> Báo cáo dựa trên **đọc code tĩnh**, chưa chạy app thật. Kết quả ❌ nên được dev xác nhận lại trước khi sửa.

## Công cụ kiểm tra gì

| Nhóm | Nội dung | Cách kiểm |
|---|---|---|
| **4 màn đầu** | Splash, Language, Onboarding, Welcome: tải, hiển thị, preload, xử lý lỗi/offline/hết thời gian, observer | AI đọc code |
| **ID ads** | ID tài liệu so với `ad_config.json`; bản debug phải dùng ID test của Google, bản release không được dùng | Tất định |
| **Cấu hình** | `isEnable` theo tài liệu; `enable_ua_check` chỉ bật cho native full screen Onboarding; key Remote Config; khoảng cách inter 35 giây | Tất định |
| **Màn hình** | Tên 4 Activity, chặn xoay màn hình, Dev setting ở màn Language | Tất định |
| **Luồng chung** | Khởi tạo SDK, Remote Config và fallback, nguồn ID trong code, load/observe, banner reload | AI đọc code |
| **Lỗi chéo** *(tùy chọn)* | Lỗi chỉ xảy ra khi các luồng tác động lẫn nhau. Chậm hơn, tốn token, mặc định tắt | AI đọc code |

Tên vị trí trong tài liệu và trong app đôi khi khác nhau: tool nhận các **tên tương đương đã biết** (hiện `inter_welcome_back` ↔ `inter_welcome`) và ghi rõ "app đặt tên …"; vị trí cùng nhóm nhưng khác chỉ số (ví dụ `fullscreen_1_2` so với `fullscreen_1_3`) được báo là **"chưa khớp tên, cần xác nhận"** thay vì "thiếu". Thêm cặp tương đương mới ở `PLACEMENT_ALIASES` trong `apk_audit/placement_policy.py`.

Rule kiểm tra **tất định** chạy tức thì, không tốn token AI. Danh sách đầy đủ: `uv run apk-audit rules list`.

## Cài đặt (cho Dev)

Yêu cầu: Python ≥ 3.11 với [uv](https://docs.astral.sh/uv/), `jadx` và Java, và **một** trong hai CLI đã đăng nhập: `claude` hoặc `codex`. Node.js chỉ cần khi sửa giao diện.

```bash
uv sync --extra mcp
uv run apk-audit doctor        # kiểm tra jadx, Java, CLI AI
uv run apk-audit serve         # mở web tại http://127.0.0.1:8765
```

`serve` mặc định chạy **6 rule song song**; đổi bằng `--workers 1-10`. Kết quả lưu ở `out/web/`.

## Dòng lệnh

```bash
uv run apk-audit audit app.apk --engine claude --out out/app \
  --ads-scripts ADS.xlsx --checklist working.xlsx \
  --ads-sheet "PA-XXX-1-Tên app" --checklist-sheet "PA-XXX-1-Tên app"
```

| Tùy chọn | Tác dụng |
|---|---|
| `--engine claude\|codex\|none` | Chọn AI; `none` chỉ chạy rule tất định |
| `--workers N` | Số rule chạy đồng thời (1–10) |
| `--cross-flow` | Chạy thêm rule rà lỗi chéo |
| `--recheck-all` | Kiểm lại cả rule đã đạt ở bản trước |
| `--no-scoped-cache` | Không dùng lại kết quả giữa các bản build |
| `--only RULE_ID` | Chỉ chạy một rule hoặc một nhóm |

Mã thoát `1` nghĩa là báo cáo có rule **Cần sửa**.

## Phạm vi mặc định và trích mã sẵn

Mặc định AI **chỉ đọc phần liên quan**: khởi tạo SDK, Remote Config / consent / fallback local, nguồn ID và **4 màn đầu** (Splash, Language, Onboarding, Welcome). Rule Load/observe và Banner chỉ chạy khi chọn **Kiểm đầy đủ cho dev** (web) hoặc `--full` (CLI). Trước khi gọi AI, tool **trích sẵn các hàm quan trọng** của từng phạm vi (`apk_audit/slicer.py`): chọn theo thứ tự bền với làm rối (class trong manifest, chuỗi/tên vị trí quảng cáo, getter, vòng đời `onCreate/onResume`), theo một bước gọi/khởi tạo lớp trong app, bỏ qua thư viện bên thứ ba, ghi rõ `KHÔNG CÓ MÃ` khi JADX không xuất được file của một màn. Mỗi khối có đường dẫn và **số dòng thật** nên AI dùng thẳng làm dẫn chứng và chỉ cần vài lệnh đọc thêm; đo thử trên app huyết áp: số lệnh đọc mỗi rule giảm từ 9–12 xuống 0–5.

## Chọn AI và tiết kiệm token

- **Claude Sonnet 5 (low)** và **Codex GPT-6 Sol (low)** đều cố định model, không tự đổi khi lỗi. Mỗi lượt dùng hạn mức của gói đăng ký, không tính tiền theo token.
- Rule **Đạt/Cần sửa** đã có kết quả được **dùng lại** khi chạy lại cùng APK, tài liệu và engine; bản build mới cũng dùng lại nếu file code liên quan không đổi.
- Hết hạn mức giữa chừng thì rule dở dang ra ❔ kèm lý do; chạy lại sau khi hạn mức làm mới.
- Muốn xem nhanh ID và cấu hình mà không tốn token: dùng `--engine none`.

## Độ tin cậy với APK bị làm rối

Công cụ đọc mã **giải mã từ APK** (JADX), không phải mã nguồn gốc: tên lớp/hàm có thể bị đổi (R8/ProGuard) và một số hàm không giải mã được. Vì vậy:

- **Chuỗi ký tự, manifest và file cấu hình trong assets không bị đổi tên** nên là căn cứ chắc chắn: thiếu hoặc sai ở đây mới báo ❌.
- **Không thấy một tên hàm** chỉ báo ❌ khi mã *không* bị làm rối và không có file giải mã lỗi; ngược lại ra ❔ kèm lý do, không bị coi là lỗi.
- Mỗi rule tĩnh ghi **Căn cứ** (manifest / file cấu hình / chuỗi trong mã / lời gọi hàm) và **giới hạn** (mức làm rối, số file giải mã lỗi); tab Dev cảnh báo khi mã bị làm rối vừa/cao. AI cũng nhận thông tin này và được yêu cầu không kết luận lỗi chỉ vì mất một tên hàm.
- **Cổng chặn báo oan cho rule AI:** mỗi nhận định lỗi phải ghi `basis`: *defect_present* (đoạn code được dẫn thể hiện hành vi sai) hoặc *behavior_absent* (đã tìm nhưng không thấy). Kết quả ❌ chỉ chỉ dựa trên "không thấy" sẽ tự hạ thành ❔ khi mã bị làm rối hoặc có file giải mã lỗi; lỗi có đoạn code sai rõ ràng vẫn là ❌ và vẫn phải qua review độc lập. Reviewer được yêu cầu tự tìm lại hành vi bằng chuỗi/hằng số/import.
- **Độ tin cậy** (cao / trung bình / thấp) hiện bên cạnh từng rule: *cao* khi đạt ngay lượt đầu và đủ căn cứ, *trung bình* khi phải sửa bằng chứng/điều tra thêm hoặc lỗi chỉ dựa trên việc không thấy, *thấp* với ❔. Màn Marketing ghi "nên dev xác nhận" khi ❌ chỉ ở mức trung bình.

## Kiểm tra tài liệu có đúng app trước khi gọi AI

Sau khi đọc APK và tài liệu, **trước khi tốn quota AI**, tool kiểm tra ba dấu hiệu tài liệu thuộc app khác: package của working file lệch package APK, AdMob App ID lệch, hoặc **tài khoản AdMob** của ID trong app và trong ADS SCRIPTS không trùng nhau (ID test của Google không tính). Nếu lệch, web dừng ở trạng thái *Chờ xác nhận tài liệu* và hỏi **Tiếp tục kiểm tra** hay **Hủy để chọn lại tài liệu**; CLI dừng với mã `7` và chấp nhận `--confirm-mismatch`. Chạy `--engine none` không bị chặn. Lượt đã xác nhận ghi cảnh báo `documents_may_not_match_app` trong báo cáo.

## Giới hạn cần biết

- Kết luận dựa trên mã đã giải mã bằng JADX. Hàm bị JADX bỏ thân hoặc code bị làm rối có thể cho kết quả ❔.
- Không đo được hành vi lúc chạy (có fill hay hiển thị thật không).
- ADS SCRIPTS và working file phải **cùng một app**. CSV không giữ màu/gạch ngang nên không biết placement nào "không dùng"; dùng XLSX để chính xác nhất.
- Nội dung code và tài liệu cần thiết được gửi tới nhà cung cấp AI đã chọn qua CLI.

## Tài liệu kỹ thuật

[Tham chiếu chi tiết](docs/technical-reference.md) · [Chuẩn ads/init của base](docs/base-ads-contract.md) · [Tối ưu và kiểm chứng](docs/audit-optimization.md) · [Kế hoạch triển khai](docs/superpowers/plans/)

## Phát triển

```bash
uv run python -m unittest discover -s tests     # kiểm thử
cd frontend && npm ci && npm run build          # build giao diện vào apk_audit/web_assets
```

Nhật ký làm việc và trạng thái hiện tại nằm ở [`SESSION_LOG.md`](SESSION_LOG.md).
