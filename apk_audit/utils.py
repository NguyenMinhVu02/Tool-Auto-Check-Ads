import hashlib
import json
import os
from pathlib import Path
import tempfile

MAX_TEXT_BYTES = 8 * 1024 * 1024

def digest_file(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".audit-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)

def safe_path(root, relative):
    root = Path(root).resolve()
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or "\\" in str(relative):
        raise ValueError("Đường dẫn phải tương đối và nằm trong workspace")
    path = (root / rel).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Đường dẫn vượt ngoài workspace")
    return path

def source_files(root):
    root = Path(root).resolve()
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.resolve().is_relative_to(root) and not path.is_symlink():
            yield path

def read_text(path):
    if path.stat().st_size > MAX_TEXT_BYTES:
        raise ValueError(f"File quá lớn để đọc: {path.name}")
    return path.read_text(encoding="utf-8", errors="replace")

def lookup(data, path):
    """A small documented JSON path subset: $.key, key[index], ["key.with.dot"]."""
    import re
    path = path.removeprefix("$").removeprefix(".")
    if not path:
        return data
    tokens = re.findall(r'(?:^|\.)([^.\[\]]+)|\[(\d+)\]|\["([^"\n]+)"\]', path)
    reconstructed = "".join(("." + a if a else "["+b+"]" if b else '["'+c+'"]') for a,b,c in tokens).removeprefix(".")
    if reconstructed != path:
        raise ValueError("JSONPath chỉ hỗ trợ key, [index], [\"key\"]")
    for key, index, quoted in tokens:
        data = data[int(index)] if index else data[key or quoted]
    return data
