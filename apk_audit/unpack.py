import json
from pathlib import Path
import subprocess
import tempfile
import time
import zipfile
from .config import find_jadx
from .errors import AuditError
from .fetch import validate_archive
from .utils import write_json

def unpack(archive, cache_dir, refresh=False):
    archive = Path(archive).resolve()
    source = validate_archive(archive)
    jadx = find_jadx()
    if not jadx:
        raise AuditError("Không tìm thấy jadx. Cài jadx rồi đặt JADX_PATH hoặc thêm vào PATH.", 4)
    try:
        version = subprocess.run([jadx, "--version"], capture_output=True, text=True, timeout=30, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise AuditError(f"Không chạy được jadx: {exc}", 4) from exc
    base = Path(cache_dir) / "workspaces" / source["sha256"]
    base.mkdir(parents=True, exist_ok=True)
    marker = base / "current.json"
    if marker.exists() and not refresh:
        try:
            saved = json.loads(marker.read_text())
            ws = base / saved["directory"]
            if ws.resolve().is_relative_to(base.resolve()) and saved["jadx"] == version and (ws / "resources/AndroidManifest.xml").is_file():
                return ws, {**source, "split_names": saved.get("split_names", [])}
        except (ValueError, KeyError, OSError):
            pass
    ws = Path(tempfile.mkdtemp(prefix="run-", dir=base))
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="apk-input-", dir=base) as staging:
        inputs = [archive]
        if source["is_split"]:
            inputs = []
            with zipfile.ZipFile(archive) as z:
                for name in z.namelist():
                    if name.lower().endswith(".apk"):
                        item = Path(z.extract(name, staging))
                        validate_archive(item)
                        inputs.append(item)
                        source["split_names"].append(name)
        try:
            completed = subprocess.run([jadx, "--no-debug-info", "--no-inline-anonymous", "-d", str(ws), *map(str, inputs)], capture_output=True, text=True, errors="replace", timeout=600)
        except (OSError, subprocess.SubprocessError) as exc:
            raise AuditError(f"jadx thất bại: {exc}", 4) from exc
    metadata = {"jadx": version, "returncode": completed.returncode,
                "duration_seconds": time.monotonic()-started,
                "warnings": ["smali_unavailable: cung cấp workspace có smali để dùng xrefs bytecode"],
                "stderr": completed.stderr[-12000:], "stdout": completed.stdout[-12000:]}
    write_json(ws / "unpack.json", metadata)
    if not (ws / "resources/AndroidManifest.xml").is_file():
        raise AuditError(f"jadx không tạo manifest đọc được. Xem {ws / 'unpack.json'}", 4)
    if completed.returncode:
        metadata["warnings"].append("jadx_partial_output")
        write_json(ws / "unpack.json", metadata)
    write_json(marker, {"directory": ws.name, "jadx": version, "split_names": source["split_names"]})
    return ws, source
