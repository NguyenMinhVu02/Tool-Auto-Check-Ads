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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHORTCUT_NAME = "APK Audit"


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


def launch_command(uv):
    """Shell line that starts (or reopens) the web UI from the project folder."""
    return [uv, "run", "--project", str(PROJECT_ROOT), "apk-audit", "serve", "--open"]


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
            f'"{uv}" run --project "{project}" apk-audit serve --open\r\n'
            "if errorlevel 1 pause\r\n", encoding="utf-8")
        link = desktop / f"{SHORTCUT_NAME}.lnk"
        script = (
            "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:APK_LINK);"
            "$s.TargetPath=$env:APK_TARGET;$s.WorkingDirectory=$env:APK_DIR;"
            "$s.IconLocation='%SystemRoot%\\System32\\shell32.dll,22';$s.Save()")
        env = {**os.environ, "APK_LINK": str(link), "APK_TARGET": str(starter), "APK_DIR": project}
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                       check=True, env=env, timeout=60)
        created.append(link)
    elif system == "mac":
        link = desktop / f"{SHORTCUT_NAME}.command"
        _write_executable(link, "#!/bin/bash\n"
                          f'cd "{project}" || exit 1\n'
                          'echo "APK Audit đang chạy. Đóng cửa sổ này để tắt tool."\n'
                          f'"{uv}" run --project "{project}" apk-audit serve --open\n')
        created.append(link)
    else:
        line = " ".join("'" + part.replace("'", "'\\''") + "'" for part in launch_command(uv))
        entry = ("[Desktop Entry]\nType=Application\nName=APK Audit\nComment=Kiểm tra tích hợp ads trong APK\n"
                 f"Exec=bash -c \"cd '{project}' && echo 'APK Audit đang chạy. Đóng cửa sổ này để tắt tool.' && {line}\"\n"
                 "Icon=security-high\nTerminal=true\nCategories=Development;\n")
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
