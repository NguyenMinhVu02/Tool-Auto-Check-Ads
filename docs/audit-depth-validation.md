# Kiểm chứng AI đọc sâu ngày 20/10/2026

## Phạm vi

Giảm UNKNOWN có thể xử lý từ code/tài liệu, giữ nguyên guard cuối cho thiếu bằng chứng thật. Không đo runtime ad fill/show hoặc Firebase delivery. Không dùng code base làm bằng chứng rằng APK có cùng hành vi.

## Nguyên nhân đã xác định

Đọc `out/web/31f9316735b24c9da4ec41e959e176c2/report.json` của `iptv1_Inative.apk`:

| Bằng chứng | Nhận xét | Đường sửa |
| --- | --- | --- |
| Splash có 50 evidence nhưng claim trỏ 53–63; một số path không nằm trong refs của claim | Chỉ số không hợp lệ; chưa có lượt sửa claim links | Feedback có catalog, lỗi verifier và source windows; AI trả lại kết quả đầy đủ |
| Remote/ID/Welcome có excerpt không khớp dù verdict UNKNOWN | Repair cũ chỉ chạy cho nháp PASS/FAIL | Kiểm và repair mọi native verdict; guard cuối giữ nguyên |
| 6/11 finding lấy cache, trong đó có UNKNOWN với verification không hợp lệ | Cache cũ chỉ revalidate chặt PASS/FAIL | Revalidate UNKNOWN; không cache lỗi cấu trúc/source |
| Language dừng ở 26 lượt với ngân sách 25 | Không có phần dự trữ và không giữ kết quả đọc cho lần tiếp | Phân bổ khoảng 60% ban đầu ở native rule có ngân sách ≥20; giữ read output có giới hạn, một lượt điều tra bổ sung |
| Context có mô tả base nhưng không có code riêng theo rule | AI phải tự hiểu lại helper/callback và dễ đòi runtime ngoài phạm vi | 11 profile có source commit, file hash, đoạn code và static goal/required paths/caveats |

Các số trên mô tả lượt cũ, không phải baseline cùng model/cache/rule để đo tốc độ.

## Hợp đồng mới

- Model mặc định giữ GPT-6.1 Sol / medium, Claude Haiku / low; không tự đổi model hoặc effort.
- Rule pack 0.4.0 có các ngân sách riêng 35–45 lượt; trần toàn audit vẫn 400. Budget là số tool CLI quan sát được, không phải hard pre-execution gateway.
- Một lượt điều tra bổ sung tập trung vào blocker/claim chưa chắc. Sai liên kết vẫn phải được AI sửa, không tự dịch số hoặc bỏ blocker. Kết luận FAIL phải được reviewer kiểm lại trong ngân sách còn lại.
- Điều chỉnh của người dùng vẫn ưu tiên hơn code mẫu: inter cuối Onboarding tùy chọn; Open Resume theo ADS SCRIPTS active/disabled/unknown.
- Base được kiểm là `e8f4337afbc987c7c9df45a69317fb538ed6e1c6`. Mã base thực tế preload Language sau chọn config, còn reload banner theo timer thuộc BaseActivityWithBanner. Không áp thời điểm sai từ hướng dẫn cũ hoặc ép Splash reload chỉ vì có interval.
- Snapshot portable ở `rulepacks/default/base-reference.json`; pipeline gửi riêng profile của rule, hash profile đi vào cache identity. Script `scripts/snapshot_base_reference.py` kiểm commit/diff trước khi cập nhật snapshot.

## Kiểm thử

151 unittest đạt sau khi hoàn tất các thay đổi; có ca chỉ số 53/63 sai được sửa, UNKNOWN sai excerpt, điều tra callback còn thiếu, runtime không được nâng PASS, phục hồi budget theo phần dự trữ, cache UNKNOWN giả valid bị từ chối, read output được giữ khi CLI bị ngắt, sửa reference làm mất cache của rule và giới hạn từng lượt được tách khỏi tổng rule trong prompt. Đây là kiểm hợp đồng/mô phỏng, không phải số đo precision/recall trên bộ APK.

Frontend build đạt, JS explanation check đạt. Metrics/UI bổ sung số lượt repair/investigation/review và nguồn base; chưa kiểm browser trực quan.

## Lượt kiểm chứng thực tế đã hoàn tất

Chọn ba rule từng UNKNOWN: Remote Config, phân phối ID, Language. Dùng lại APK và hai tài liệu CSV của job cũ, không suy màu/gạch ngang đã mất; rule Open Resume không được coi bắt buộc khi tài liệu chưa rõ trạng thái. Snapshot rule pack ba rule lưu dưới `out/audit-depth-validation/rules/`; trace/checkpoint/report ở `out/audit-depth-validation/report/`. Không thay báo cáo hoặc lịch sử web cũ.

Lệnh tái hiện từ root dự án:

```bash
.venv/bin/apk-audit audit out/web/uploads/31f9316735b24c9da4ec41e959e176c2.apk \
  --rules out/audit-depth-validation/rules --out out/audit-depth-validation/report \
  --cache-dir out/web/cache --engine codex --trace --refresh --max-tool-calls 130 \
  --ads-scripts out/web/documents/275518e61c0a42fd87ddfa019b7ee894.csv \
  --checklist out/web/documents/8b643de0df844474a06f6c6932488a29.csv
```

Kết quả engine `codex:gpt-6.1-sol:medium`: **1 PASS, 1 FAIL, 1 UNKNOWN**, 54 tool calls, **1082.3s (~18 phút 2 giây)**, không lấy verdict cache. Cả ba mục từng UNKNOWN trong lượt cũ. Chưa chạy lại full 11 rule; khác model/cache/rule nên không dùng lượt cũ để suy tốc độ hoặc precision/recall.

| Rule | Kết quả | Bằng chứng/phạm vi |
| --- | --- | --- |
| Remote Config | PASS · 8 tools · 137.2s | 20 excerpt khớp, bốn claim hợp lệ: logic tĩnh chọn config/fallback/timer/thứ tự load. Firebase live và ad fill chưa kiểm |
| Phân phối ID | UNKNOWN · 26 tools · 606.9s | Hai lượt AI; sáu compliance và hai uncertain hợp lệ. Hợp đồng CSV còn dòng cũ/mới chưa rõ trạng thái |
| Language | FAIL · 20 tools · 319.6s | Có review độc lập accepted, 19 excerpt khớp, năm claim hợp lệ. Nhánh render ad non-null bật container/populate nhưng thiếu kiểm tra và ẩn offline |

Đã đọc lại source `LanguageActivity.java:276–298` và `ERainAd.java:974–986`: nhánh null ẩn container; nhánh non-null đặt VISIBLE và populate mà không có kiểm tra mạng/nhánh ẩn offline. Gate mạng lúc request không xử lý trường hợp mất mạng sau preload trước render. Đây là vi phạm cấu trúc fallback theo base trong code, không phải bằng chứng đã nhìn thấy quảng cáo hiển thị offline. Source của bản APK lưu trong `facts.json.workspace.root`; không sửa APK/app source.

### ID và điều chỉnh sau khi đọc trace thật

ID vẫn UNKNOWN sau hai lượt (295.3s/18 tool và 311.4s/8 tool); cả tám claim có cấu trúc và dẫn chứng hợp lệ, gồm sáu compliance và hai uncertain. AI đã lần alias Favorite/History tới ID/tag biến thể 2005, tránh kết luận ID sai chỉ từ key legacy trong inventory. Coverage còn bị chặn bởi các dòng cũ/mới trong CSV không rõ thay thế hay độc lập.

Trace cũng cho thấy AI đòi remote snapshot live và toàn bộ callback/render/navigation ở rule nguồn ID. Sau mốc này, rule/profile/prompt mặc định được giới hạn rõ về source/getter/alias → config.id → SDK load; key/schema quan sát trong source có thể kết luận tĩnh, remote deployed chỉ là limitation nếu không được cung cấp. Snapshot ba rule của lượt đang chạy giữ nguyên để bảo toàn bằng chứng. Các con số live ở đây không được gán thành số đo phiên bản có điều chỉnh phạm vi sau đó.

### XLSX người dùng bổ sung

Người dùng xác nhận `[PUB INFINITY x INNOVATIVE INSIDE] ADS SCRIPTS.xlsx` là **mẫu định dạng**, không cần cùng ứng dụng. Đã đọc sheet `PA-INN-1-Remote TV`: 26 placement, 23 active, ba disabled (`inter_onboarding`, `open_resume`, `inter_welcome_back`); hai dòng theo gạch ngang, một dòng theo màu nền ô ID. Không có ID trống ở 23 dòng active, không có trạng thái unknown/cảnh báo parser. Đọc được App ID và số dòng/sheet.

Mẫu được kiểm định dạng và trạng thái thành công, không dùng các ID mẫu để kết luận ID của IPTV. Không yêu cầu thêm APK/working file để hoàn tất kiểm tra mẫu. Biên bản không ghi giá trị ID ở `out/audit-depth-validation/xlsx-input-check.json`.
