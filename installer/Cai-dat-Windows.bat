@echo off
chcp 65001 >nul
title Cai dat APK Audit
cd /d "%~dp0.."
echo === Cai dat APK Audit ===
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul
if errorlevel 1 (
  echo [1/3] Dang cai uv ^(trinh chay Python^)...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
  if errorlevel 1 goto fail
  set "PATH=%USERPROFILE%\.local\bin;%PATH%"
) else (
  echo [1/3] Da co uv
)
echo [2/3] Dang tai thu vien cua tool...
uv sync
if errorlevel 1 goto fail
echo [3/3] Dang tao bieu tuong "APK Audit" tren man hinh chinh...
uv run apk-audit shortcut
if errorlevel 1 goto fail
echo Xong! Dang mo trang web. Lan sau chi can bam bieu tuong APK Audit.
call installer\start-windows.bat
goto end
:fail
echo Cai dat gap loi. Chup man hinh cua so nay gui dev.
pause
:end
