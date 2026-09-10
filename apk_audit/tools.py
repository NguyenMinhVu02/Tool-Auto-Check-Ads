import re
import json
from pathlib import Path
from .facts import build_facts, build_xrefs
from .utils import safe_path, source_files, read_text, lookup

class WorkspaceTools:
    """Read-only source inspection. Lists are bounded; locations are one-based."""
    def __init__(self, workspace, facts=None):
        self.root = Path(workspace).resolve()
        self.facts = facts if facts is not None else build_facts(self.root).to_dict()
        self.classes = []
        for path in source_files(self.root):
            rel = path.relative_to(self.root).as_posix()
            if rel.startswith("sources/") and rel.endswith(".java"):
                self.classes.append({"name": rel[len("sources/"):-5].replace("/", "."), "file": rel, "line": 1})
        self.xref_index = build_xrefs(self.root)

    @staticmethod
    def page(items, limit=100, offset=0):
        if type(limit) is not int or type(offset) is not int or not 1 <= limit <= 2000 or offset < 0:
            raise ValueError("limit phải từ 1 đến 2000; offset >= 0")
        return {"items": items[offset:offset+limit], "total": len(items), "truncated": len(items) > offset+limit, "next_offset": offset+limit if len(items)>offset+limit else None}

    def get_facts(self, path: str = "") -> dict | list | str | int | bool | None:
        """Read a facts value using the documented JSON path subset."""
        value = lookup(self.facts, path)
        if len(json.dumps(value, ensure_ascii=False).encode("utf-8")) > 65536:
            raise ValueError("Kết quả facts vượt 64 KiB; truyền path cụ thể hơn hoặc dùng chỉ số mảng")
        return value

    def list_classes(self, prefix: str = "", limit: int = 100, offset: int = 0) -> dict:
        """List Java classes with file and line locations."""
        return self.page([c for c in self.classes if c["name"].startswith(prefix)], limit, offset)

    def search_classes(self, pattern: str, limit: int = 100, offset: int = 0) -> dict:
        """Search class names by Python regex."""
        regex = re.compile(pattern)
        return self.page([c for c in self.classes if regex.search(c["name"])], limit, offset)

    def get_class(self, name: str = "", file: str = "") -> dict:
        """Read at most 2000 lines; use read_lines to continue."""
        if bool(name) == bool(file):
            raise ValueError("Chỉ truyền name hoặc file")
        return self.read_lines(file or "sources/" + name.replace(".", "/") + ".java", 1, 2000)

    def get_smali(self, name: str, method: str = "") -> dict:
        """Read raw smali if supplied; absence is not proof of missing code."""
        file = "smali/" + name.replace(".", "/") + ".smali"
        path = safe_path(self.root, file)
        if not path.is_file():
            return {"file": file, "lines": [], "available": False, "reason": "smali_unavailable"}
        if not method:
            return self.read_lines(file)
        lines = read_text(path).splitlines()
        for i, line in enumerate(lines):
            if line.startswith(".method") and re.search(r"(?:^|\s)"+re.escape(method)+r"\(", line):
                end = next((j+1 for j in range(i+1, len(lines)) if lines[j].startswith(".end method")), len(lines))
                return self.read_lines(file, i+1, min(end, i+2000))
        return {"file": file, "lines": [], "available": False, "reason": "method_not_found"}

    def get_methods(self, name: str, limit: int = 100, offset: int = 0) -> dict:
        """Heuristic Java declarations, not a complete Java parser."""
        file = "sources/" + name.replace(".", "/") + ".java"
        lines = read_text(safe_path(self.root, file)).splitlines()
        items = [{"file": file, "line": i, "text": line} for i, line in enumerate(lines,1) if re.search(r"^\s*(?:public|protected|private)\s+.*\([^;]*\)\s*(?:throws[^{}]+)?\{", line)]
        return {**self.page(items, limit, offset), "heuristic": True}

    def xrefs_to(self, method: str = "", class_name: str = "", limit: int = 100, offset: int = 0) -> dict:
        """Look up prebuilt smali invoke references, not Java name guesses."""
        if bool(method) == bool(class_name):
            raise ValueError("Chỉ truyền method hoặc class_name")
        key = method or class_name
        if key.startswith("L") and ";->" in key:
            owner, member = key.split(";->",1)
            key = owner[1:].replace("/", ".") + "." + member.split("(",1)[0]
        return {**self.page(self.xref_index.get(key, []), limit, offset), "scope": "smali_invoke_only", "available": any(p.suffix == ".smali" for p in source_files(self.root))}

    def grep(self, pattern: str, path_glob: str = "*", limit: int = 100, offset: int = 0) -> dict:
        """Search decoded text with Python regex; returns file and line."""
        regex = re.compile(pattern)
        items = []
        for path in source_files(self.root):
            rel = path.relative_to(self.root)
            if not rel.match(path_glob) or path.suffix not in {".java", ".kt", ".smali", ".xml", ".json", ".txt", ".properties"}:
                continue
            try:
                lines = read_text(path).splitlines()
            except (ValueError, OSError):
                continue
            for i, line in enumerate(lines,1):
                if regex.search(line):
                    items.append({"file": rel.as_posix(), "line": i, "text": line[:2000]})
        return self.page(items, limit, offset)

    def read_lines(self, file: str, start: int = 1, end: int = 2000) -> dict:
        """Read up to 2000 source lines. Absolute/escaping paths are rejected."""
        if type(start) is not int or type(end) is not int or start < 1 or end < start or end-start >= 2000:
            raise ValueError("Khoảng dòng không hợp lệ; tối đa 2000 dòng")
        path = safe_path(self.root, file)
        lines = read_text(path).splitlines()
        return {"file": path.relative_to(self.root).as_posix(), "lines": [{"line": i+1, "text": line[:4000]} for i, line in enumerate(lines[start-1:end], start-1)], "total_lines": len(lines), "truncated": end < len(lines) or any(len(x)>4000 for x in lines[start-1:end])}
