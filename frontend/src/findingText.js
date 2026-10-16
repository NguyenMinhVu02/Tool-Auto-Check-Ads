// Keep the original analysis available; formatting never changes the verdict.
export function findingText(reasoning = '') {
  const text = String(reasoning).trim();
  const lines = text.split(/\n+/).map((line) => line.trim()).filter(Boolean);
  const structured = lines.some((line) => /^(?:#{1,3}\s*)?(?:\*\*)?(Kết luận|Cần sửa|Đã đúng|Chưa xác minh)\s*:/i.test(line));
  if (structured) return { structured: true, lines, summary: '' };
  const sentences = text.split(/(?<=[.!?])\s+(?=[A-ZÀ-ỸĐ])/u).map((line) => line.trim()).filter(Boolean);
  // Highlight an explicitly stated caveat instead of guessing a new conclusion.
  const summary = sentences.find((line) => /^(Tuy nhiên|Vấn đề|Lỗi|Cần sửa)\b/i.test(line)) || sentences[0] || 'Chưa có mô tả.';
  return { structured: false, lines: sentences, summary };
}
