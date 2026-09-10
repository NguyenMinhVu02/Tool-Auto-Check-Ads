import json
from ..utils import source_files, read_text, digest_file

def extract_assets(root):
    result = {"files": [], "json": {}}
    warnings = []
    for path in source_files(root):
        rel = path.relative_to(root).as_posix()
        if not (rel.startswith("resources/assets/") or rel.startswith("assets/")):
            continue
        result["files"].append({"path": rel, "size": path.stat().st_size, "sha256": digest_file(path)})
        if path.suffix.lower() == ".json":
            try:
                key = rel.split("assets/", 1)[1]
                result["json"][key] = json.loads(read_text(path))
            except (ValueError, OSError) as exc:
                warnings.append(f"asset_unreadable: {rel}: {exc}")
    return result, warnings
