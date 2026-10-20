export function unknownExplanation(item) {
  if (item.status !== 'UNKNOWN') return null;
  const reason = item.reason || '';
  const errors = item.verification?.errors || [];
  if (reason.includes('budget') || item.exhausted_budget) {
    return { category: 'budget', title: 'Đã hết lượt đọc code cho mục này',
      description: 'AI dừng trước khi đủ bằng chứng vì hết ngân sách công cụ. Chưa xác nhận lỗi APK; cần lượt kiểm tra tập trung vào phần còn thiếu.' };
  }
  if (['engine_error', 'repair_error', 'review_error', 'engine_disabled'].includes(reason)) {
    return { category: 'engine', title: 'Phân tích AI chưa hoàn tất',
      description: 'AI bị tắt hoặc CLI gặp lỗi. Đây là tình trạng của công cụ; xem chi tiết lỗi để kiểm tra tài khoản, model hoặc cấu hình chạy.' };
  }
  if (reason.startsWith('unverified_') || reason.startsWith('invalid_') || reason === 'wrong_rule_id'
      || reason === 'repair_invalid_result' || reason === 'investigation_invalid_result' || errors.length > 0 || item.evidence?.some((entry) => entry.verified === false)) {
    return { category: 'verification', title: 'Nhận định của AI chưa vượt qua kiểm chứng',
      description: 'Đoạn trích hoặc liên kết giữa nhận định và bằng chứng chưa hợp lệ. Tool chưa chấp nhận kết luận PASS/FAIL; đây chưa phải lỗi APK được xác nhận.' };
  }
  return { category: 'coverage', title: 'Chưa đủ bằng chứng để kết luận',
    description: 'Chưa nối đủ đường đi mã, điều kiện áp dụng hoặc callback cần thiết. Xem phần “Chưa xác minh” để biết còn thiếu gì; UNKNOWN không đồng nghĩa APK có lỗi.' };
}
