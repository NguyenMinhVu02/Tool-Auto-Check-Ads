# Đọc tài liệu linh hoạt, có AI hỗ trợ khi cần

## Mục tiêu và giới hạn

Người dùng muốn tải CSV/XLSX thông thường mà không phải sửa tay từng mẫu. Parser nhận dạng trước; chỉ gọi engine đã chọn khi chưa hiểu cấu trúc. Không dùng AI để tạo ID, đổi dữ liệu hoặc chọn tùy tiện giữa nhiều ứng dụng. Giữ trạng thái định dạng XLSX, số dòng và kiểm tra trùng placement. Không tự commit/push hoặc gọi audit APK mới.

## Thiết kế

- CSV tự tìm header trong 40 dòng đầu, nhận dấu phẩy/chấm phẩy/tab/pipe và alias cột phổ biến. XLSX dùng cùng chuẩn hóa header.
- Callback mapper tùy chọn cho cấu trúc chưa nhận dạng. Preview giới hạn, một lần/file, timeout 90 giây. AI trả sheet/header/column indices theo schema, tuyệt đối không trả giá trị trích xuất.
- Loader kiểm sheet/header/cột trong preview và file gốc, bắt buộc đủ cột cần thiết, không trùng chỉ số/field. Dữ liệu đầu ra luôn lấy từ ô gốc. Nhiều sheet có mẫu app hợp lệ vẫn yêu cầu chọn/tách sheet; không gộp app.
- Codex/Claude dùng model/effort đã pin; tác vụ ánh xạ riêng không có audit verdict schema hoặc đọc workspace APK. Không có native adapter hoặc static-only thì giữ parser deterministic.
- Pipeline lưu metadata cách đọc/AI usage để biết AI có can thiệp; lỗi ánh xạ rõ nghĩa, không bỏ qua tài liệu âm thầm.

## Thứ tự thực hiện và kiểm chứng

1. Hoàn tất regression CSV header lệch dòng (đã RED/GREEN và kiểm file thật).
2. Viết test trước cho delimiter/alias, AI mapping thành công và từ chối output sai/không đủ căn cứ; giữ XLSX strike/fill.
3. Mở adapter structured mapping dùng lại lifecycle/timeout/usage; kiểm fake CLI cho cả provider.
4. Nối fallback vào pipeline và metadata báo cáo; regression không gọi AI khi parser chuẩn đã đọc được.
5. Chạy suite đầy đủ, kiểm lại CSV/XLSX thật không gọi AI cho cấu trúc chuẩn. Ghi rõ không thay thế kiểm accuracy hoặc Claude auth thực.

## Còn ngoài phạm vi

Dropdown chọn sheet, OCR/PDF/Google Sheets URL, suy công thức/conditional formatting, tự ghép hợp đồng khác app. Không cam kết đọc mọi workbook hoặc chữa thiếu dữ liệu bằng suy đoán.

## Kết quả ngày 2026-10-20

Đã triển khai các bước trên, 165/165 unittest đạt và frontend build đạt. Hai CSV thật đọc trực tiếp được66/17dòng, XLSX mẫu26placement vẫn giữ3disabled. Codex thật Sol6.1medium ánh xạ CSV giả lập thành công8.856s/0tools, report tại out/document-ai-live-smoke/report.json (empty pack có chủ đích, không là auditAPK). Claude kiểm fake CLI, chưa live auth. Chưa restart backend/commit/push hoặc kiểm trực quan trình duyệt. Tọa độ kiểm được không đồng nghĩa đảm bảo AI hiểu đúng ngữ nghĩa mọi header.
