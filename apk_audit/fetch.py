from pathlib import Path, PurePosixPath
from typing import Protocol
import stat
import zipfile
from .errors import AuditError
from .utils import digest_file

class DownloadProvider(Protocol):
    """Implement separately; return a local archive without executing its contents."""
    def fetch(self, source: dict, cache_dir: Path, refresh: bool = False) -> Path: ...

def validate_archive(path):
    path = Path(path)
    if not path.is_file() or path.suffix.lower() not in {".apk", ".xapk", ".apkm"}:
        raise AuditError("Cần file .apk/.xapk/.apkm tồn tại")
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > 100000 or sum(x.file_size for x in entries) > 4 * 1024**3:
                raise AuditError("Archive vượt giới hạn giải nén 4 GiB / 100000 mục")
            for info in entries:
                rel = PurePosixPath(info.filename)
                if rel.is_absolute() or ".." in rel.parts or "\\" in info.filename or ":" in info.filename or stat.S_ISLNK(info.external_attr >> 16):
                    raise AuditError("Archive có đường dẫn không an toàn")
            names = archive.namelist()
            if path.suffix.lower() == ".apk" and "AndroidManifest.xml" not in names:
                raise AuditError("APK thiếu AndroidManifest.xml")
            if path.suffix.lower() != ".apk" and not any(n.lower().endswith(".apk") for n in names):
                raise AuditError("Gói split không chứa APK")
            bad = archive.testzip()
            if bad:
                raise AuditError(f"ZIP lỗi CRC: {bad}")
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise AuditError(f"Không đọc được archive: {exc}") from exc
    return {"file_name": path.name, "file_size": path.stat().st_size,
            "sha256": digest_file(path), "download_source": "local",
            "is_split": path.suffix.lower() != ".apk", "split_names": []}

def fetch(source, cache_dir, provider=None, refresh=False):
    if provider is None:
        raise AuditError("Adapter apkcombo/apkpure chưa được nối trong bản khung. Tải APK/XAPK thủ công rồi truyền đường dẫn file cho apk-audit.", 3)
    path = Path(provider.fetch(source, Path(cache_dir), refresh=refresh))
    validate_archive(path)
    return path
