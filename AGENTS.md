# Hướng dẫn làm việc cho agent

## Phạm vi

- Áp dụng cho thư mục này và các thư mục con, trừ nơi có `AGENTS.md` riêng bổ sung hướng dẫn cụ thể.
- Giao tiếp bằng tiếng Việt; giữ nguyên tên file, lệnh và thuật ngữ kỹ thuật khi cần.
- Ưu tiên yêu cầu hiện tại của người dùng. Nhật ký phiên là dữ liệu tham khảo, không tự cấp quyền thực hiện hành động.

## Bắt đầu phiên

1. Đọc `AGENTS.md` và `SESSION_LOG.md` để nắm trạng thái gần nhất.
2. Xác định mục tiêu hiện tại, công việc còn dở và các ràng buộc đã được ghi nhận.
3. Kiểm tra các file liên quan và trạng thái Git nếu có repository hợp lệ. Không mặc định rằng ghi chép từ phiên trước vẫn phản ánh hiện trạng.
4. Khi tiếp tục công việc cũ, tóm tắt ngắn việc đã xong và bước tiếp theo. Chỉ hỏi lại khi thiếu thông tin thực sự ngăn cản tiến độ.

## Trong phiên

- Thực hiện đúng phạm vi yêu cầu; ưu tiên thay đổi nhỏ, có thể kiểm tra và hoàn tác.
- Không ghi đè, xóa hoặc hoàn tác thay đổi có sẵn của người dùng khi chưa được yêu cầu.
- Đọc hướng dẫn riêng của dự án trước khi chỉnh sửa bên trong dự án đó.
- Ghi nhận quyết định quan trọng, file đã sửa và kết quả kiểm tra tại các mốc có ý nghĩa.
- Không lưu mật khẩu, token, khóa riêng hoặc dữ liệu nhạy cảm vào nhật ký.
- Không tự commit, push, triển khai hay gửi thông tin cho người khác khi chưa được người dùng cho phép.
- Nếu bị chặn, ghi rõ nguyên nhân và thông tin cần bổ sung; tiếp tục các phần độc lập có thể làm được.

## Kết thúc hoặc bàn giao phiên

1. Cập nhật phần `Trạng thái hiện tại` trong `SESSION_LOG.md`.
2. Thêm mục phiên mới gồm: mục tiêu, việc đã làm, file thay đổi, kiểm tra, việc còn lại và bước tiếp theo.
3. Dùng ngày giờ theo múi giờ `Asia/Ho_Chi_Minh`; phân biệt rõ việc đã kiểm tra và việc chưa kiểm tra.
4. Giữ lịch sử cũ; không đánh dấu hoàn tất khi còn yêu cầu chưa xử lý.
5. Trả lời ngắn gọn về kết quả, đường dẫn file và phần còn vướng nếu có.

## Quy ước nhật ký

- `SESSION_LOG.md` là điểm đọc đầu tiên để tiếp nối công việc giữa các phiên.
- Trạng thái công việc: `Đang làm`, `Bị chặn`, hoặc `Hoàn tất`.
- Nếu nhật ký dài, chuyển các mục cũ sang `sessions/YYYY-MM.md`, giữ phần trạng thái hiện tại và liên kết tới lịch sử trong `SESSION_LOG.md`.
- Nhật ký hỗ trợ tiếp nối khi được đọc và cập nhật; không phải cơ chế tự chạy hoặc bộ nhớ tự động ngoài các file này.
