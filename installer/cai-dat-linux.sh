#!/usr/bin/env bash
# Cài APK Audit lần đầu: cài uv, tải thư viện, tạo biểu tượng trên màn hình chính rồi mở web.
set -e
cd "$(dirname "$0")/.."
echo "=== Cài đặt APK Audit ==="
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  echo "[1/3] Đang cài uv (trình chạy Python)..."
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  else
    wget -qO- https://astral.sh/uv/install.sh | sh
  fi
  export PATH="$HOME/.local/bin:$PATH"
else
  echo "[1/3] Đã có uv"
fi
echo "[2/3] Đang tải thư viện của tool..."
uv sync
echo "[3/3] Đang tạo biểu tượng \"APK Audit\" trên màn hình chính..."
uv run apk-audit shortcut
echo "Xong! Đang mở trang web. Lần sau chỉ cần bấm biểu tượng APK Audit."
if [ -f installer/start-macos.command ]; then
  exec bash installer/start-macos.command
fi
exec bash installer/start-linux.sh
