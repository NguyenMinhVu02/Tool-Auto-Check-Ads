export function updateView(status) {
  return { available: Boolean(status?.available && !status?.git_checkout) };
}
