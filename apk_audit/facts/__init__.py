from datetime import datetime, timezone
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from ..contracts import Facts
from ..utils import source_files, read_text, digest_file, digest_json
from .manifest import parse_manifest
from .assets import extract_assets
from .strings import extract_strings

def build_xrefs(root, files=None):
    index = {}
    for path in (source_files(root) if files is None else files):
        if path.suffix != ".smali":
            continue
        try:
            lines = read_text(path).splitlines()
        except (ValueError, OSError):
            continue
        for number, line in enumerate(lines, 1):
            if not line.strip().startswith("invoke-"):
                continue
            match = re.search(r'L([^;]+);->([^ (]+)\(', line)
            if match:
                owner = match[1].replace("/", ".")
                item = {"file": path.relative_to(root).as_posix(), "line": number, "text": line}
                index.setdefault(owner + "." + match[2], []).append(item)
                index.setdefault(owner, []).append(item)
    return index

def build_facts(workspace, source=None, extract=None, files=None):
    root = Path(workspace).resolve()
    extract = extract or {}
    files = list(source_files(root) if files is None else files)
    content_hash = digest_json([(p.relative_to(root).as_posix(), digest_file(p)) for p in files])
    facts = Facts(generated_at=datetime.now(timezone.utc).isoformat(), tool_versions={"apk_audit": "0.1.0"},
                  source=dict(source or {}), workspace={"root": str(root), "sources_dir": "sources", "smali_dir": "smali", "resources_dir": "resources", "file_count": len(files), "content_sha256": content_hash})
    facts.source.setdefault("sha256", None)
    facts.source.setdefault("download_source", "workspace")
    try:
        facts.manifest = parse_manifest(root)
    except (ValueError, OSError, ET.ParseError) as exc:
        facts.warnings.append(f"manifest_unreadable: {exc}")
    for key in ("package", "version_name", "version_code"):
        facts.source[key] = facts.manifest.get(key) or facts.source.get(key)
    facts.assets, warnings = extract_assets(root, files=files)
    facts.warnings.extend(warnings)
    facts.strings, warnings = extract_strings(root, extract, files=files)
    facts.warnings.extend(warnings)
    java = [p for p in files if p.suffix == ".java" and p.relative_to(root).parts[0] == "sources"]
    ratio = sum(len(p.stem) <= 2 for p in java) / len(java) if java else None
    facts.code_index = {"class_count": len(java), "obfuscation_ratio": ratio, "obfuscated": None,
                        "known_packages": [{"prefix": prefix, "class_count": sum(p.relative_to(root / "sources").as_posix().replace("/", ".").startswith(prefix + ".") for p in java), "obfuscated": None} for prefix in extract.get("known_packages", [])]}
    if not any(p.suffix == ".smali" for p in files):
        facts.warnings.append("smali_unavailable")
    return facts
