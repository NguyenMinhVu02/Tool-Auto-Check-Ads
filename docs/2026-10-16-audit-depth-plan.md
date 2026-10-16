# Kế hoạch cải thiện audit sau pilot Cast TV

## Mục tiêu

Người dùng đưa APK/XAPK/APKM và hai CSV thật lên web, bấm chạy một lần, xem được tiến độ từng rule và nhận báo cáo có kiểm kê placement, kết luận logic ads dựa trên đường đi mã JADX, cùng các giới hạn chưa chứng minh được.

## Quyết định thiết kế

1. **Tài liệu:** tách parser tài liệu khỏi pipeline. Nhận JSON object, CSV `key,value`, ADS SCRIPTS dạng bảng và working file dạng bảng. Giữ dữ liệu gốc dưới dạng hàng có số dòng; chuẩn hóa ADS SCRIPTS thành `placements`, working thành `checklist_rows`. Bỏ hàng trang trí/rỗng, không đoán ID nếu ô trống, báo lỗi rõ với header sai.
2. **Kiểm kê trước AI:** tạo một inventory từ CSV và assets đã giải mã: key thiếu/thừa, ID khớp/lệch, package/App ID nếu có nguồn. Ghi vào report `observations`, đưa tóm tắt inventory cho từng rule. Phần kiểm kê là deterministic; không tự kết luận đường load/show.
3. **Đọc mã sâu:** giữ Codex Luna cho các rule logic. Prompt yêu cầu lần từ nguồn config qua call site, callback, observer, render/show và nhánh fail/disabled; thêm rule cuối rà bug giao thoa sau khi nhận kết quả các rule trước. Nếu evidence sai file/dòng, cho Codex một lượt sửa với đầy đủ tài liệu/context; chỉ nhận PASS/FAIL khi *mọi* evidence cuối cùng đều hợp lệ. Cache của rule cuối phụ thuộc kết quả các rule trước. Tăng mô tả rule để tiêu chí FAIL bao phủ đúng lỗi release/debug và thiếu reload theo config.
4. **Tiến độ web:** callback hiện thêm rule index, tổng rule, ID, title, trạng thái hoàn thành và cache hit. Giao diện hiển thị `n/11`, tên rule và kết quả vừa xong, không đưa ETA thiếu cơ sở. Job vẫn chạy một lượt tại một thời điểm. Cache đặt trong `out/web/cache`, khóa theo từng rule cùng tài liệu/context; rule rà giao thoa còn phụ thuộc các finding trước. Lượt đầu vẫn cần Codex đọc mã.
5. **Kiểm chứng:** test parser trên mẫu CSV thật bằng fixture ẩn ID, test inventory, evidence, callback/API/web; build frontend; chạy pilot với chính hai CSV gốc bằng cache hoặc rule hẹp để xác nhận đầu cuối. Không gửi dữ liệu ra ngoài, không commit/push khi chưa được yêu cầu.

## Phạm vi sau lát cắt này

Phân tích mã tĩnh không chứng minh request/show ads và Firebase runtime. Chưa xây bộ phát hiện mọi bug Java trong toàn bộ APK, chưa chạy nhiều Codex song song hoặc lưu job qua restart server. Các phần đó cần thiết kế và benchmark riêng sau khi đầu vào/report đáng tin và tiến độ dễ theo dõi.

## Công việc

- [x] Parser bốn loại tài liệu cùng test.
- [x] Inventory deterministic và report observations.
- [x] Siết evidence/prompt/rule criteria.
- [x] Progress callback/API/frontend và test.
- [x] README, build, test và pilot với hai CSV thật.

## Kết quả kiểm chứng

35/35 unittest đạt; frontend build và rule pack check đạt. Hai CSV gốc được nhận trực tiếp: 24 placement kỳ vọng, local release có 23, 23 ID chung khớp; Package và AdMob App ID khớp tài liệu. Đã chạy các lượt đủ 11 rule và kiểm chứng riêng các rule bị hiệu chỉnh. Bản rà soát có ghi nguồn từng kết luận ở `out/cast-tv-final-review/validation.md`; không coi các FAIL AI thô đã bị bác bỏ là lỗi xác nhận.
