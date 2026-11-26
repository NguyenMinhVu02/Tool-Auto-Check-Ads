"""Check GitHub Releases for a newer APK Audit and update the install folder in place.

Only the folders shipped in the release ZIP are replaced (see build_release.INCLUDE); audit
results (out/), the virtualenv and downloaded tools are left alone. A git checkout is never
overwritten: developers update with git.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import tomllib
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO = "NguyenMinhVu02/Tool-Auto-Check-Ads"
SHIPPED = ["apk_audit", "rulepacks", "installer", "pyproject.toml", "uv.lock", "README.md"]
RESTART_EXIT_CODE = 75
CHECK_TTL = 6 * 3600
USER_AGENT = "apk-audit-updater"


def repo():
    return os.environ.get("APK_AUDIT_UPDATE_REPO", DEFAULT_REPO)


def current_version(root=PROJECT_ROOT):
    try:
        return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    except (OSError, KeyError, ValueError):
        return "0"


def parse_version(text):
    parts = re.findall(r"\d+", str(text or "").split("-")[0])
    return tuple(int(p) for p in parts[:3]) or (0,)


def is_git_checkout(root=PROJECT_ROOT):
    return (root / ".git").exists()


def _request(url, accept="application/vnd.github+json"):
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    token = os.environ.get("APK_AUDIT_GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def fetch_latest_release():
    # APK_AUDIT_UPDATE_FEED points at a release JSON elsewhere (testing, mirrors).
    feed = os.environ.get("APK_AUDIT_UPDATE_FEED")
    url = feed or f"https://api.github.com/repos/{repo()}/releases/latest"
    try:
        with urllib.request.urlopen(_request(url), timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # The API allows 60 calls/hour per IP; offices share one IP. github.com pages are not limited.
        if feed or exc.code not in {403, 429}:
            raise
        return fetch_latest_release_page()


def fetch_latest_release_page():
    """Latest release without the API: follow /releases/latest and use the ZIP naming convention."""
    request = urllib.request.Request(f"https://github.com/{repo()}/releases/latest", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        final = response.geturl()
    match = re.search(r"/releases/tag/(v?[\w.\-]+)$", final)
    if not match:
        raise urllib.error.HTTPError(final, 404, "Chưa có Release", {}, None)
    tag = match.group(1)
    name = f"apk-audit-{tag.lstrip('v')}.zip"
    return {"tag_name": tag, "html_url": final, "body": "Xem ghi chú thay đổi trên trang GitHub Release.",
            "assets": [{"name": name,
                        "browser_download_url": f"https://github.com/{repo()}/releases/download/{tag}/{name}"}]}


def _zip_asset(release):
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if name.startswith("apk-audit-") and name.endswith(".zip"):
            return asset
    return None


class Updater:
    def __init__(self, root=PROJECT_ROOT, fetch=fetch_latest_release, busy=lambda: False):
        self.root = Path(root)
        self.fetch = fetch
        self.busy = busy
        self.lock = threading.Lock()
        self.cached = None
        self.cached_at = 0.0
        self.job = None
        self.restart_requested = threading.Event()

    # ------------------------------------------------------------------ check
    def check(self, force=False):
        with self.lock:
            if not force and self.cached and time.time() - self.cached_at < CHECK_TTL:
                return dict(self.cached)
        current = current_version(self.root)
        result = {"current": current, "latest": None, "available": False, "notes": "", "url": None,
                  "published_at": None, "git_checkout": is_git_checkout(self.root), "error": None,
                  "checked_at": time.time()}
        try:
            release = self.fetch()
            latest = str(release.get("tag_name", "")).lstrip("v")
            asset = _zip_asset(release)
            result.update(latest=latest, notes=(release.get("body") or "")[:4000], url=release.get("html_url"),
                          published_at=release.get("published_at"))
            result["available"] = bool(asset) and parse_version(latest) > parse_version(current)
            if parse_version(latest) > parse_version(current) and not asset:
                result["error"] = "Bản phát hành mới chưa có file ZIP"
        except urllib.error.HTTPError as exc:
            result["error"] = ("Không đọc được bản phát hành (repo riêng tư hoặc chưa có Release)"
                               if exc.code in {401, 404} else f"GitHub tạm từ chối ({exc.code}), thử lại sau")
        except (OSError, ValueError) as exc:
            result["error"] = f"Không kiểm tra được cập nhật: {exc}"
        with self.lock:
            self.cached, self.cached_at = result, time.time()
        return dict(result)

    # ------------------------------------------------------------------ apply
    def start(self):
        if is_git_checkout(self.root):
            raise ValueError("Đây là bản dev (thư mục git): cập nhật bằng git pull")
        if self.busy():
            raise RuntimeError("Đang có lượt kiểm tra chạy; chờ xong rồi cập nhật")
        with self.lock:
            if self.job and self.job["state"] == "running":
                raise RuntimeError("Đang cập nhật")
            self.job = {"state": "running", "log": [], "error": None, "version": None}
        threading.Thread(target=self._run, daemon=True).start()

    def status(self):
        with self.lock:
            return None if self.job is None else {**self.job, "log": list(self.job["log"])}

    def _log(self, line):
        with self.lock:
            self.job["log"].append(line)

    def _run(self):
        try:
            version = self.apply(self._log)
            with self.lock:
                self.job.update(state="restarting", version=version)
            self.restart_requested.set()
        except Exception as exc:  # noqa: BLE001 - shown to the user
            with self.lock:
                self.job.update(state="error", error=f"Cập nhật thất bại, vẫn giữ bản cũ: {exc}")

    def apply(self, log, release=None):
        release = release or self.fetch()
        asset = _zip_asset(release)
        if not asset:
            raise RuntimeError("Bản phát hành không có file ZIP")
        version = str(release.get("tag_name", "")).lstrip("v")
        work = self.root / ".update"
        if work.exists():
            shutil.rmtree(work)
        work.mkdir()
        try:
            archive = work / asset["name"]
            log(f"Đang tải {asset['name']}...")
            digest = hashlib.sha256()
            with urllib.request.urlopen(_request(asset["browser_download_url"], "application/octet-stream"),
                                        timeout=120) as response, archive.open("wb") as stream:
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    stream.write(chunk)
                    digest.update(chunk)
            expected = (asset.get("digest") or "").removeprefix("sha256:")
            if expected and digest.hexdigest() != expected.lower():
                raise RuntimeError("File tải về không khớp SHA256")
            log("Đã kiểm tra file tải về" + (" (SHA256 khớp)" if expected else ""))
            staging = work / "new"
            with zipfile.ZipFile(archive) as bundle:
                for member in bundle.namelist():
                    target = (staging / member).resolve()
                    if not str(target).startswith(str(staging.resolve())):
                        raise RuntimeError(f"ZIP chứa đường dẫn không an toàn: {member}")
                bundle.extractall(staging)
                for info in bundle.infolist():  # keep the executable bit of installer scripts
                    mode = info.external_attr >> 16
                    if mode & 0o111:
                        (staging / info.filename).chmod(mode & 0o777)
            tops = [p for p in staging.iterdir()]
            source = tops[0] if len(tops) == 1 and tops[0].is_dir() else staging
            if not (source / "pyproject.toml").is_file() or not (source / "apk_audit").is_dir():
                raise RuntimeError("ZIP không đúng cấu trúc APK Audit")
            self._swap(source, work / "backup", log)
        finally:
            shutil.rmtree(work / "new", ignore_errors=True)
            (work / asset["name"]).unlink(missing_ok=True)
        log("Đang cập nhật thư viện (uv sync)...")
        uv = shutil.which("uv") or str(Path.home() / ".local" / "bin" / ("uv.exe" if os.name == "nt" else "uv"))
        done = subprocess.run([uv, "sync", "--project", str(self.root)], capture_output=True, text=True,
                              timeout=600, errors="replace")
        if done.returncode != 0:
            log((done.stderr or done.stdout)[-1500:])
            self._restore(work / "backup", log)
            raise RuntimeError("uv sync lỗi, đã khôi phục bản cũ")
        shutil.rmtree(work, ignore_errors=True)
        try:
            from .launcher import create_shortcut
            create_shortcut()
            log("Đã làm mới biểu tượng trên màn hình chính")
        except Exception:  # noqa: BLE001 - a stale shortcut still works
            pass
        log(f"Đã cập nhật lên bản {version}. Đang khởi động lại...")
        return version

    def _swap(self, source, backup, log):
        backup.mkdir(parents=True, exist_ok=True)
        moved = []
        try:
            for name in SHIPPED:
                new = source / name
                if not new.exists():
                    continue
                old = self.root / name
                if old.exists():
                    shutil.move(str(old), str(backup / name))
                    moved.append(name)
                shutil.move(str(new), str(old))
            log("Đã thay file của bản mới")
        except OSError:
            for name in SHIPPED:
                if (self.root / name).exists() and name in moved:
                    shutil.rmtree(self.root / name, ignore_errors=True) if (self.root / name).is_dir() \
                        else (self.root / name).unlink(missing_ok=True)
            self._restore(backup, log)
            raise

    def _restore(self, backup, log):
        if not backup.is_dir():
            return
        for item in backup.iterdir():
            target = self.root / item.name
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            elif target.exists():
                target.unlink()
            shutil.move(str(item), str(target))
        log("Đã khôi phục bản cũ")
