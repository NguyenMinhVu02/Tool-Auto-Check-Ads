export const pages = [
  { key: 'audit', label: 'Kiểm tra' },
  { key: 'history', label: 'Lịch sử' },
  { key: 'results', label: 'Kết quả' },
  { key: 'setup', label: 'Thiết lập máy' },
];

export function pageFromHash(hash) {
  const key = String(hash || '').replace(/^#\/?/, '');
  return pages.some((page) => page.key === key) ? key : 'audit';
}
