# Tối ưu audit và kiểm chứng nhận định

## Mục tiêu đã được yêu cầu
Triển khai phương án ngày 19/10: audit local ít đọc mã lặp hơn, kết luận có bằng chứng theo từng nhận định, có số đo đối chiếu được, tiếp tục sau gián đoạn và chạy song song có giới hạn. Codex Luna mặc định; Claude tùy chọn. CLI là tiến trình local nhưng inference qua nhà cung cấp hiện có.

## Phạm vi và hợp đồng
- Python >=3.11, standard library, giữ CLI/API/report cũ đọc được. Không tự commit/push; làm trên feat/audit-optimization, giữ thay đổi SESSION_LOG hiện có.
- Đo duration theo phase và rule, cache/repair/review/budget; không bịa token/CPU khi không thu được. Có benchmark cùng đầu vào và bộ ca tổng hợp có verdict chuẩn; không coi fixture là đánh giá accuracy APK thực tế.
- SourceIndex quét mã một lần khi chưa có index theo workspace digest; cache index bên ngoài workspace. Tạo bundle có file/dòng/excerpt giới hạn kích thước, gợi ý theo rule và inventory.code_references, Application/manifest. Ranking lexical là heuristic, không gọi là call graph chứng minh đường đi. AI vẫn đọc toàn workspace; thiếu hit/truncated không chứng minh thiếu hành vi.
- Live adapters trả claims liên kết evidence; claim PASS/FAIL phải applicable, scope static, không có unresolved blocker, có bằng chứng hợp lệ và các mắt xích đường đi. Runtime/thiếu mã giữ UNKNOWN. Review bổ sung có mục tiêu cho FAIL, trong cùng budget; kết luận có thể thay đổi, review không phải oracle. Replay/legacy adapter được đọc tương thích và đánh dấu chưa xác minh claim.
- Cache verdict phải phụ thuộc prompt/schema/verifier/index policy, engine/model cấu hình và phiên bản CLI nếu có; không dùng lại cache vô điều kiện khi Claude model mặc định không xác định. Không chuyển provider/model. Chỉ reuse verdict đã qua validation đúng phiên bản; lỗi hệ thống không cache.
- Scheduler workers 1 mặc định, 2 tùy chọn, budget tổng được reserve trước dispatch và hoàn lại phần chưa dùng. Rule giao thoa chạy sau tất cả và nhận finding/claim đã kiểm; thứ tự report cố định. Không tự chạy song song trên tài khoản thật trước benchmark.
- Job lưu JSON nguyên tử; khởi động lại đánh dấu job dang dở interrupted, không tự sinh request AI; resume do người dùng bấm, dùng cache/checkpoint hoàn thành đã hợp lệ. Lưu và đọc lịch sử/report từ disk, archive/doc paths phải nằm dưới output_root. Single active job như cũ.
- Không tuyên bố đã xác minh semantic bằng regex/shape validator; chưa có symbolic execution hay tự sinh smali. Những vùng JADX lỗi và SDK/reflection không giải nghĩa được phải thể hiện giới hạn. Tự sinh DEX/smali là extension khi có ca cần thiết và tool tương ứng, không thêm dependency reverse chưa kiểm.

## Tiêu chí nghiệm thu
Baseline hiện 51 tests. Thêm test red/green cho bundle bounded/path safety/cache; claims thiếu bằng chứng/gate/runtime/reviewer bác bỏ; cache invalidation; workers/budget/dependency/order; persistent restart/resume/path tamper; metrics và benchmark ground truth. Full suite, frontend build, offline benchmark và workspace smoke. Pilot AI thật chỉ khi login/network sẵn, báo riêng nếu chưa kiểm; không hứa mức tăng tốc trước benchmark tương đương.
