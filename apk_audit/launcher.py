"""Desktop shortcut creation and the "open, or start then open" web launcher."""

import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.request
import webbrowser
from pathlib import Path

from .setup_tools import os_name
from .updater import RESTART_EXIT_CODE

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHORTCUT_NAME = "APK Audit"
ICON_DIR = PROJECT_ROOT / "installer"


def server_running(port):
    """True when an apk-audit server already answers on this port."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/setup/status", timeout=8) as response:
            return "items" in json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return False


def open_browser_later(url, delay=1.0):
    timer = threading.Timer(delay, lambda: webbrowser.open(url))
    timer.daemon = True
    timer.start()


def desktop_dir():
    if os_name() == "linux":
        try:
            done = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True, timeout=5)
            if done.returncode == 0 and done.stdout.strip():
                return Path(done.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            pass
    if os_name() == "windows":
        try:
            done = subprocess.run(["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
                                  capture_output=True, text=True, timeout=15)
            if done.returncode == 0 and done.stdout.strip():
                return Path(done.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            pass
    return Path.home() / "Desktop"


def posix_starter(uv):
    """Start script: reruns the server when it exits with RESTART_EXIT_CODE after an update."""
    project = str(PROJECT_ROOT)
    return ("#!/bin/bash\n"
            f'cd "{project}" || exit 1\n'
            'echo "APK Audit đang chạy. Đóng cửa sổ này để tắt tool."\n'
            "OPEN=--open\n"
            "while true; do\n"
            f'  "{uv}" run --project "{project}" apk-audit serve $OPEN\n'
            "  code=$?\n"
            f"  [ $code -eq {RESTART_EXIT_CODE} ] || break\n"
            '  echo "Đang khởi động lại sau khi cập nhật..."\n'
            "  OPEN=\n"
            "done\n"
            '[ $code -eq 0 ] || read -r -p "Có lỗi (mã $code). Nhấn Enter để đóng..."\n')


def _write_executable(path, content):
    path.write_text(content, encoding="utf-8", newline="\n")
    path.chmod(0o755)


def create_shortcut(desktop=None, uv=None):
    """Create the desktop shortcut for this OS and return the created paths."""
    uv = uv or shutil.which("uv") or sys.executable
    desktop = Path(desktop) if desktop else desktop_dir()
    desktop.mkdir(parents=True, exist_ok=True)
    system = os_name()
    project = str(PROJECT_ROOT)
    created = []
    if system == "windows":
        starter = PROJECT_ROOT / "installer" / "start-windows.bat"
        starter.write_text(
            "@echo off\r\nchcp 65001 >nul\r\ntitle APK Audit\r\n"
            f'cd /d "{project}"\r\n'
            "echo APK Audit dang chay. Dong cua so nay de tat tool.\r\n"
            "set OPEN=--open\r\n"
            ":loop\r\n"
            f'"{uv}" run --project "{project}" apk-audit serve %OPEN%\r\n'
            f"if %errorlevel%=={RESTART_EXIT_CODE} (set OPEN=& echo Dang khoi dong lai sau khi cap nhat...& goto loop)\r\n"
            "if errorlevel 1 pause\r\n", encoding="utf-8")
        link = desktop / f"{SHORTCUT_NAME}.lnk"
        script = (
            "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:APK_LINK);"
            "$s.TargetPath=$env:APK_TARGET;$s.WorkingDirectory=$env:APK_DIR;"
            "$s.IconLocation=$env:APK_ICON;$s.Save()")
        env = {**os.environ, "APK_LINK": str(link), "APK_TARGET": str(starter), "APK_DIR": project,
               "APK_ICON": str(ICON_DIR / "logo.ico")}
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                       check=True, env=env, timeout=60)
        created.append(link)
    elif system == "mac":
        # A tiny .app bundle carries the logo; it opens Terminal on the real launcher so the
        # user still sees the "close this window to stop" console.
        starter = PROJECT_ROOT / "installer" / "start-macos.command"
        _write_executable(starter, posix_starter(uv))
        link = desktop / f"{SHORTCUT_NAME}.app"
        if link.exists():
            shutil.rmtree(link)
        (link / "Contents" / "MacOS").mkdir(parents=True)
        (link / "Contents" / "Resources").mkdir()
        shutil.copyfile(ICON_DIR / "logo.icns", link / "Contents" / "Resources" / "logo.icns")
        (link / "Contents" / "Info.plist").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0"><dict>'
            '<key>CFBundleName</key><string>APK Audit</string>'
            '<key>CFBundleIdentifier</key><string>local.apk-audit.launcher</string>'
            '<key>CFBundleExecutable</key><string>launcher</string>'
            '<key>CFBundleIconFile</key><string>logo</string>'
            '<key>CFBundlePackageType</key><string>APPL</string>'
            '</dict></plist>\n', encoding="utf-8")
        _write_executable(link / "Contents" / "MacOS" / "launcher",
                          f'#!/bin/bash\nopen -a Terminal "{starter}"\n')
        created.append(link)
    else:
        starter = PROJECT_ROOT / "installer" / "start-linux.sh"
        _write_executable(starter, posix_starter(uv))
        entry = ("[Desktop Entry]\nType=Application\nName=APK Audit\nComment=Kiểm tra tích hợp ads trong APK\n"
                 f"Exec=bash \"{starter}\"\n"
                 f"Icon={ICON_DIR / 'logo.png'}\nTerminal=true\nCategories=Development;\n")
        link = desktop / "apk-audit.desktop"
        _write_executable(link, entry)
        created.append(link)
        menu = Path.home() / ".local" / "share" / "applications" / "apk-audit.desktop"
        menu.parent.mkdir(parents=True, exist_ok=True)
        _write_executable(menu, entry)
        created.append(menu)
        if shutil.which("gio"):
            subprocess.run(["gio", "set", str(link), "metadata::trusted", "true"], capture_output=True, timeout=10)
    return created
