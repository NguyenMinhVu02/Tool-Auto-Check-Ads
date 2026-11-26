#!/bin/bash
# Cài APK Audit lần đầu trên macOS: bấm đúp file này (lần đầu: chuột phải > Open).
cd "$(dirname "$0")/.." || exit 1
bash installer/cai-dat-linux.sh
status=$?
if [ $status -ne 0 ]; then
  echo "Cài đặt gặp lỗi (mã $status). Chụp màn hình cửa sổ này gửi dev."
  read -r -p "Nhấn Enter để đóng..."
fi
