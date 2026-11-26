"""Check and install the external tools the audit needs, without admin rights.

Tools are installed as portable copies under ``tools_root()`` (Java, JADX, Node)
or through the vendor's own per-user installer (Claude CLI). ``activate()`` puts
those locations on PATH for the current process so every existing
``shutil.which`` / ``subprocess`` call finds them.
"""

import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path
from uuid import uuid4

from platformdirs import user_data_path

USER_AGENT = "apk-audit-setup"
JAVA_MAJOR = 17


def tools_root():
    override = os.environ.get("APK_AUDIT_TOOLS_DIR")
    return Path(override).expanduser() if override else user_data_path("apk-audit", appauthor=False) / "tools"


def os_name():
    return {"win32": "windows", "darwin": "mac"}.get(sys.platform, "linux")


def arch_name():
    machine = platform.machine().lower()
    return "aarch64" if machine in {"arm64", "aarch64"} else "x64"


def _find_bin_dir(root, executable):
    """Return the directory holding ``bin/<executable>`` inside an extracted archive."""
    names = [executable + ".exe", executable + ".bat", executable + ".cmd", executable]
    if not root.is_dir():
        return None
    for candidate in sorted(root.rglob("bin")):
        if candidate.is_dir() and any((candidate / name).is_file() for name in names):
            return candidate
    return None


def _node_bin_dir():
    root = tools_root() / "node"
    if not root.is_dir():
        return None
    for child in sorted(root.iterdir()):
        if (child / "node.exe").is_file():
            return child
        if (child / "bin" / "node").is_file():
            return child / "bin"
    return None


def _npm_prefix():
    return tools_root() / "npm"


def _npm_bin_dir():
    prefix = _npm_prefix()
    return prefix if os_name() == "windows" else prefix / "bin"


def tool_paths():
    """Directories to prepend to PATH, most specific first."""
    root = tools_root()
    dirs = [_find_bin_dir(root / "jdk", "java"), _find_bin_dir(root / "jadx", "jadx"), _node_bin_dir(),
            _npm_bin_dir(), Path.home() / ".local" / "bin"]
    return [d for d in dirs if d and d.is_dir()]


def activate():
    """Prepend portable tool directories to PATH (idempotent)."""
    current = os.environ.get("PATH", "").split(os.pathsep)
    added = [str(d) for d in tool_paths() if str(d) not in current]
    if added:
        os.environ["PATH"] = os.pathsep.join(added + current)
    java_bin = _find_bin_dir(tools_root() / "jdk", "java")
    if java_bin:
        os.environ["JAVA_HOME"] = str(java_bin.parent)
    return added


def _run(command, timeout=20):
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL, errors="replace")
        return done.returncode, (done.stdout or "") + (done.stderr or "")
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)


def _which(name):
    return shutil.which(name)


def _java_version():
    path = _which("java")
    if not path:
        return None, None
    _, output = _run([path, "-version"])
    return path, parse_java_major(output)


def parse_java_major(output):
    match = re.search(r'version "(\d+)(?:\.(\d+))?', output or "")
    if not match:
        return None
    major = int(match.group(1))
    return int(match.group(2) or 0) if major == 1 else major


def _first_line(output):
    for line in output.splitlines():
        if line.strip():
            return line.strip()[:120]
    return ""


def _login_state(engine):
    """True / False / None (cannot tell) for whether the AI CLI is logged in."""
    if not _which(engine):
        return False
    if engine == "codex":
        code, _ = _run([_which("codex"), "login", "status"])
        return None if code is None else code == 0
    code, output = _run([_which("claude"), "auth", "status"])
    if code is None:
        return None
    lowered = output.lower()
    if code == 0 and ("not logged" in lowered or "not authenticated" in lowered):
        return False
    if code == 0:
        return True
    return None if "unknown" in lowered or "usage" in lowered else False


def check():
    from .config import find_jadx
    activate()
    java_path, java_major = _java_version()
    jadx = find_jadx()
    _, jadx_out = _run([jadx, "--version"]) if jadx else (None, "")
    node = _which("node")
    items = [
        {"id": "java", "label": "Java 17+", "required": True, "purpose": "JADX cần Java để chạy",
         "installed": bool(java_path and (java_major or 0) >= JAVA_MAJOR), "path": java_path,
         "version": str(java_major) if java_major else None,
         "note": f"Đang có Java {java_major}, cần 17 trở lên" if java_path and java_major and java_major < JAVA_MAJOR else None},
        {"id": "jadx", "label": "JADX", "required": True, "purpose": "Giải mã APK",
         "installed": bool(jadx), "path": jadx, "version": _first_line(jadx_out) if jadx else None},
        {"id": "node", "label": "Node.js", "required": False, "purpose": "Cần để cài Codex CLI",
         "installed": bool(node), "path": node, "version": _first_line(_run([node, "--version"])[1]) if node else None},
    ]
    for engine, label in (("claude", "Claude CLI"), ("codex", "Codex CLI")):
        path = _which(engine)
        items.append({"id": engine, "label": label, "required": False, "ai": True,
                      "purpose": "AI đọc mã để audit (cần ít nhất một AI)",
                      "installed": bool(path), "path": path,
                      "version": _first_line(_run([path, "--version"])[1]) if path else None,
                      "logged_in": _login_state(engine) if path else False})
    ai_ready = any(item.get("ai") and item["installed"] for item in items)
    missing = [item["id"] for item in items if item["required"] and not item["installed"]]
    return {"os": os_name(), "arch": arch_name(), "tools_dir": str(tools_root()), "items": items,
            "ready": not missing and ai_ready, "missing_required": missing, "ai_ready": ai_ready}


# ---------------------------------------------------------------- downloads

def _http_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _http_text(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def _download(url, destination, log, sha256=None):
    log(f"Đang tải {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    digest = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as stream:
        total = int(response.headers.get("Content-Length") or 0)
        done, last = 0, 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            stream.write(chunk)
            digest.update(chunk)
            done += len(chunk)
            if total and done * 100 // total >= last + 10:
                last = done * 100 // total
                log(f"  {last}% ({done // (1024 * 1024)} MB)")
    if sha256 and digest.hexdigest().lower() != sha256.lower():
        raise RuntimeError("File tải về không khớp mã kiểm tra SHA256, đã hủy cài đặt")
    if sha256:
        log("Đã kiểm tra SHA256 khớp")


def _safe_target(root, name):
    target = (root / name).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise RuntimeError(f"File nén chứa đường dẫn không an toàn: {name}")
    return target


def _extract(archive, destination, log):
    log("Đang giải nén...")
    destination.mkdir(parents=True, exist_ok=True)
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                _safe_target(destination, member.filename)
            bundle.extractall(destination)
    else:
        with tarfile.open(archive) as bundle:
            for member in bundle.getmembers():
                _safe_target(destination, member.name)
            if hasattr(tarfile, "data_filter"):
                bundle.extractall(destination, filter="tar")
            else:
                bundle.extractall(destination)
    if os_name() != "windows":
        for path in destination.rglob("*"):
            if path.is_file() and path.parent.name == "bin":
                path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _install_archive(name, url, archive_name, log, sha256=None):
    root = tools_root()
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        archive = Path(tmp) / archive_name
        _download(url, archive, log, sha256)
        staging = Path(tmp) / "out"
        _extract(archive, staging, log)
        target = root / name
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(staging), str(target))
    log(f"Đã cài vào {root / name}")


def install_java(log):
    os_part = {"windows": "windows", "mac": "mac", "linux": "linux"}[os_name()]
    url = (f"https://api.adoptium.net/v3/assets/latest/{JAVA_MAJOR}/hotspot?os={os_part}"
           f"&architecture={arch_name()}&image_type=jdk&vendor=eclipse")
    assets = _http_json(url)
    if not assets:
        raise RuntimeError("Không tìm thấy bản Java phù hợp với máy này trên Adoptium")
    package = assets[0]["binary"]["package"]
    _install_archive("jdk", package["link"], package["name"], log, package.get("checksum"))


def install_jadx(log):
    release = _http_json("https://api.github.com/repos/skylot/jadx/releases/latest")
    asset = next((a for a in release.get("assets", [])
                  if a["name"].startswith("jadx-") and a["name"].endswith(".zip") and "gui" not in a["name"]), None)
    if not asset:
        raise RuntimeError("Không tìm thấy file JADX trong bản phát hành mới nhất")
    digest = (asset.get("digest") or "").removeprefix("sha256:") or None
    _install_archive("jadx", asset["browser_download_url"], asset["name"], log, digest)


def install_node(log):
    base = "https://nodejs.org/dist/latest-v22.x/"
    platform_part = {"windows": "win", "mac": "darwin", "linux": "linux"}[os_name()]
    arch_part = "arm64" if arch_name() == "aarch64" else "x64"
    suffix = ".zip" if os_name() == "windows" else ".tar.gz"
    wanted = f"-{platform_part}-{arch_part}{suffix}"
    for line in _http_text(base + "SHASUMS256.txt").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].startswith("node-v") and parts[1].endswith(wanted):
            _install_archive("node", base + parts[1], parts[1], log, parts[0])
            return
    raise RuntimeError("Không tìm thấy bản Node.js phù hợp với máy này")


def _stream(command, log, env=None):
    log("$ " + " ".join(command))
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                               text=True, errors="replace", env=env)
    for line in process.stdout:
        if line.strip():
            log(line.rstrip()[:300])
    if process.wait() != 0:
        raise RuntimeError(f"Lệnh cài đặt kết thúc với mã lỗi {process.returncode}")


def install_claude(log):
    if os_name() == "windows":
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                   "irm https://claude.ai/install.ps1 | iex"]
    else:
        command = ["bash", "-c", "curl -fsSL https://claude.ai/install.sh | bash"]
    _stream(command, log)


def install_codex(log):
    activate()
    if not _which("npm"):
        log("Chưa có Node.js, cài Node.js trước...")
        install_node(log)
        activate()
    npm = _which("npm")
    if not npm:
        raise RuntimeError("Không tìm thấy npm sau khi cài Node.js")
    _npm_prefix().mkdir(parents=True, exist_ok=True)
    _stream([npm, "install", "-g", "--prefix", str(_npm_prefix()), "@openai/codex"], log)


INSTALLERS = {"java": install_java, "jadx": install_jadx, "node": install_node,
              "claude": install_claude, "codex": install_codex}
LOGIN_COMMANDS = {"claude": ["claude"], "codex": ["codex", "login"]}


def open_terminal(command):
    """Open a visible terminal window running ``command`` so the user can log in."""
    executable = _which(command[0])
    if not executable:
        raise RuntimeError(f"Chưa cài {command[0]}")
    full = [executable, *command[1:]]
    system = os_name()
    if system == "windows":
        subprocess.Popen(["cmd", "/c", "start", "", "cmd", "/k", subprocess.list2cmdline(full)])
        return
    quoted = " ".join("'" + part.replace("'", "'\\''") + "'" for part in full)
    if system == "mac":
        script = quoted.replace("\\", "\\\\").replace('"', '\\"')
        subprocess.Popen(["osascript", "-e", f'tell application "Terminal" to do script "{script}"',
                          "-e", 'tell application "Terminal" to activate'])
        return
    for terminal in (["x-terminal-emulator", "-e"], ["gnome-terminal", "--"], ["konsole", "-e"],
                     ["xfce4-terminal", "-x"], ["xterm", "-e"]):
        if _which(terminal[0]):
            subprocess.Popen([*terminal, "bash", "-c", quoted + "; exec bash"])
            return
    raise RuntimeError("Không tìm thấy ứng dụng terminal để mở cửa sổ đăng nhập")


def login(engine):
    if engine not in LOGIN_COMMANDS:
        raise ValueError("Công cụ không hỗ trợ đăng nhập")
    activate()
    open_terminal(LOGIN_COMMANDS[engine])


class SetupJobs:
    """Runs one installation at a time in a background thread and keeps its log."""

    def __init__(self, installers=None):
        self.installers = installers or INSTALLERS
        self.jobs = {}
        self.lock = threading.Lock()

    def start(self, tool):
        if tool not in self.installers:
            raise ValueError("Công cụ không nằm trong danh sách được phép cài")
        with self.lock:
            if any(job["state"] == "running" for job in self.jobs.values()):
                raise RuntimeError("Đang cài một công cụ khác, vui lòng chờ xong")
            job_id = uuid4().hex
            self.jobs[job_id] = {"id": job_id, "tool": tool, "state": "running", "log": [], "error": None,
                                 "started_at": time.time()}
        threading.Thread(target=self._run, args=(job_id,), daemon=True).start()
        return job_id

    def _log(self, job_id, line):
        with self.lock:
            log = self.jobs[job_id]["log"]
            log.append(line)
            del log[:-400]

    def _run(self, job_id):
        tool = self.jobs[job_id]["tool"]
        try:
            self.installers[tool](lambda line: self._log(job_id, line))
            activate()
            self._log(job_id, "Hoàn tất.")
            state, error = "done", None
        except Exception as exc:  # noqa: BLE001 - shown to the user
            state, error = "error", f"Cài {tool} thất bại: {exc}"
            self._log(job_id, error)
        with self.lock:
            self.jobs[job_id].update(state=state, error=error)

    def get(self, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            return None if job is None else {**job, "log": list(job["log"])}
