# Kiểm chứng bản tối ưu — 2026-10-19

## Kết quả có thể tái kiểm

- Baseline:51 tests đạt. Bản cuối:127/127 unittest đạt ngoài sandbox; frontend production build exit0; git diff --check đạt.
- Quality suite:15/15 ca tổng hợp đạt kỳ vọng, gồm claim runtime, applicability thiếu, unresolved SDK, evidence lỗi, review bác bỏ/timeout/budget và claim phụ. Đây là kiểm guard/replay, không phải precision của AI trên APK thật.
- Independent review tìm3 Important (cache shape, tin review flag, index cache thiếu truncated); đã thêm regression RED/GREEN và sửa. Cache/checkpoint có checksum, shape guard, recheck evidence và reviewed payload.
- Web HTTP engines/history/assets đạt. Đã restart backend khi history không có job active. Browser automation chưa thực hiện được: runtime bootstrap chặn import node:process; không tuyên bố kiểm trực quan UI.

## Mẫu lỗi tĩnh có verdict đã biết

Mẫu callback nhận loadedSlot nhưng gọi showInterstitial(languageSlot), hợp đồng chỉ xét argument forwarding tĩnh:

| Lượt | Kết quả | Công cụ | Thời gian |
|---|---|---:|---:|
| Codex Luna thật +review | FAIL, claim valid, review accepted |4|38.05s|
| Warm cùng fingerprint thời điểm đó |FAIL từ cache|0|0.012s|

Artifact:out/audit-optimization-live-smoke-v2/report.json và out/audit-optimization-live-warm/report.json. Prompt/guard có thay đổi thêm sau đó từ pilot; không dùng warm cache của policy cũ cho bản mới. Không suy thời gian hoặc độ chính xác APK lớn từ mẫu này.

## Pilot IPTV và tối ưu index

Corpus59,457 file có thể index,57,760 lớp Java,5,563,845 dòng,284,077,177 byte text.

| Phần đo | Kết quả |
|---|---:|
| Index v1 cache |398,177,580B|
| Index v1 cold phase trong pilot |62.49s|
| Index v2 cache |16,086,507B|
| Index v2 cold riêng |53.63s|
| Index v2 warm riêng |1.85s|
| Bundle Splash v2 |0.19s|
| Peak RSS tiến trình đo v2 (giữ cold+warm cùng lúc) |250,100KiB|
| Pipeline local sau chia sẻ file list, engine none/index warm |20.24s|

Cache giảm khoảng96%, không đồng nghĩa toàn bộ audit AI nhanh hơn96%. v1/v2 được đo cùng corpus nhưng khác policy index và không phải cặp chạy model fresh tương đương. Số liệu tại out/audit-optimization-index-v2-bench/measurement.json và out/audit-optimization-iptv-local-final/report.json. Giữ cache v1 cũ để không xóa dữ liệu; policy mới không reuse nó.

Pilot AI thật rule Splash trước chỉnh guard cuối mất267.49s: facts36.51s,index62.49s,AI167.47s,19tools. Kết quả cuối UNKNOWN/unverified_evidence; draft FAIL chưa được công nhận. Pilot cho thấy ancillary claim có thể chặn review và reasoning nháp gây hiểu nhầm. Đã sửa bằng supported-violation targeted review và nhãn UNKNOWN/draft chưa xác minh, kiểm qua replay dữ liệu thật. Chưa chạy lại đủ11rule với bản cuối và chưa đo fresh AI 1worker/2workers trên nhiều APK.

## Giới hạn giữ nguyên

Checksum không chống người có quyền sửa cả record/checksum/trace. CLI tool budget là reservation+observed stop; tool có thể đã bắt đầu trước khi bị dừng, report giữ observed overrun. Claude model default chưa xác định thì không reuse verdict/checkpoint. Không có runtime proof, tự sinh smali hay semantic oracle. Chưa kiểm Claude live thành công trong phiên này.

## Thay đổi model ngày 2026-10-20

Các số liệu live phía trên thuộc cấu hình Luna ở thời điểm19/10. Code hiện chuyển Codex sang GPT-6.1 Sol / medium và Claude sang Haiku5.5 / low theo yêu cầu mới; không dùng benchmark Luna để suy giá/tốc độ/chất lượng của model mới. Khóa cache và nhãn report được tách theo model/effort.
