# Tối ưu audit và đọc kết quả

## Cơ chế mới

1. Đọc tài liệu, giải mã/reuse workspace, trích facts/inventory như trước.
2. Lập SourceIndex theo digest workspace và phiên bản policy. Lượt sau dùng index còn hợp lệ. Mỗi rule nhận gói file/dòng có giới hạn khoảng 20.000 ký tự, vị trí chuỗi placement, manifest/Application và config liên quan. Đây là gợi ý lexical, AI vẫn tìm ngoài gói; không phải call graph hoặc bằng chứng thiếu hành vi. Các bước hash/facts vẫn đọc workspace để kiểm tính toàn vẹn, chưa thay bằng tin mtime.
3. Native AI trả từng claim: nhận định, applicability, phạm vi static/runtime, điều kiện, đường đi, chỉ số dẫn chứng. Checker kiểm cấu trúc và excerpt; không tự chứng minh ngữ nghĩa. Blocker trong scope ở unresolved; giới hạn ngoài scope ở limitations. FAIL được AI rà thêm bằng prompt phản biện trong cùng ngân sách; review có thể hạ UNKNOWN.
4. Cache/checkpoint phụ thuộc dữ liệu đầu vào, rule/context, prompt/schema/verifier, bundle policy và engine identity. Cache có checksum phát hiện hỏng dữ liệu, recheck excerpt và đối chiếu reviewed result với finding; checksum không chống người có quyền sửa cả record và checksum. Không sử dụng cache từ policy cũ. Model và effort đều nằm trong identity; Claude Haiku5.5 / low đã được chỉ định rõ nên reuse verdict/checkpoint được khi CLI version xác định. Khi identity chưa biết thì chỉ reuse index. Codex GPT-6.1 Sol / medium giữ mặc định từ 20/10; Claude cố định Haiku5.5 / low.
5. Workers=1 mặc định; workers=2 chỉ cho rule độc lập. Scheduler reserve ngân sách trước dispatch; rule giao thoa chạy cuối với finding/claim/evidence hoàn tất. Native CLI báo tool khi bắt đầu nên đây là giới hạn quan sát rồi dừng, không phải gateway chặn trước mọi tool; overrun được giữ số thật, UNKNOWN và warning, không giấu bằng cap. Có thể tăng thời gian/quota do review; cần benchmark trước khi coi nhanh hơn.
6. Job lưu JSON nguyên tử trong out/web/jobs. Restart đánh dấu lượt đang dở bị gián đoạn; không tự gọi AI. Bấm Tiếp tục để kiểm lại fingerprint và dùng checkpoint/cache hợp lệ; không tiếp tục giữa chừng một request model. Lịch sử và báo cáo đọc lại được sau restart. Lượt upload chưa đủ byte không resume. Dữ liệu job cũ trước phiên bản persistence không tự khôi phục vào lịch sử.

## Chạy

```bash
.venv/bin/apk-audit serve --workers 1
# Thử nghiệm tối đa hai rule độc lập:
.venv/bin/apk-audit audit /path/to/app.apk --workers 2 --out out/app --trace
# Tiếp tục đúng out và đầu vào; không bỏ qua bước kiểm fingerprint:
.venv/bin/apk-audit audit /path/to/app.apk --out out/app --resume --trace
```

Web có Lịch sử, Xem kết quả và Tiếp tục. Muốn web chạy hai rule đồng thời, khởi động backend bằng `serve --workers 2`; không tự đổi provider/model.

## Đo đạc và đánh giá

`metrics.json` và `report.json.metrics` có thời gian mỗi phase/rule, cache/index hit, repair/review attempts, tool calls, prompt bytes và usage do CLI thực sự trả. Prompt bytes không phải token; không ước lượng token/chi phí khi không có dữ liệu. Thời gian rule chồng lấp khi chạy song song. Report còn lưu fingerprint để từ chối so tốc độ giữa đầu vào hoặc policy khác nhau.

```bash
# Fixture tổng hợp offline: kiểm claim guard và review replay, không đánh giá model:
.venv/bin/apk-audit benchmark --quality --out out/quality
# Tạo cache namespace mới, đo cold/warm trên cùng đầu vào:
.venv/bin/apk-audit benchmark examples/workspace --engine none --out out/bench --repeats 2
# Gọi AI thật, dùng quota CLI hiện có:
.venv/bin/apk-audit benchmark /path/to/app.apk --engine codex --workers 1 --out out/bench-ai --repeats 2 --ads-scripts /path/to/ads.csv --checklist /path/to/working.csv
```

So sánh workers 1/2 cần cùng APK/docs/model/policy, cache cold riêng và nhiều lượt để nhìn biến động; benchmark cold/warm không chứng minh tăng tốc fresh AI. `quality_preserved` trong comparator chỉ nghĩa verdict không đổi trên cùng fingerprint; chất lượng thật cần bộ ground truth được rà thủ công. Precision/recall trong quality.json ghi cả mẫu số và chỉ thuộc fixture tổng hợp, không được công bố thành độ chính xác APK thực tế.

## Giới hạn còn lại

- Chưa tự tạo DEX/smali hoặc xác minh mọi callback/nhánh bằng symbolic execution. SDK/JNI/reflection/JADX lỗi có thể cần UNKNOWN.
- Không xác minh request/show ads hoặc Firebase runtime.
- Review AI và claim structure không phải oracle; vẫn cần benchmark trên tập APK có lỗi đã biết.
- Chưa chứng minh mức tăng tốc AI trên nhiều APK/máy/tài khoản. Lượt live smoke mẫu tổng hợp chỉ kiểm chứng đường tích hợp mới.
