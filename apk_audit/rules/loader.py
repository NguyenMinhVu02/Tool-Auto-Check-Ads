from dataclasses import fields
from pathlib import Path
import re
import yaml
from ..contracts import Rule, RulePack
from ..errors import AuditError
from ..utils import digest_json, source_files, read_text

CHECKS = {"manifest_meta", "manifest_has", "string_present", "string_absent", "asset_json_path", "asset_json_match", "sdk_version"}

def load_pack(directory=None):
    if directory is None and Path("rulepacks/default/pack.yaml").is_file():
        directory = Path("rulepacks/default")
    if directory is None:
        return RulePack("empty", "0.1.0", digest_json({"empty": True}))
    root = Path(directory).resolve()
    try:
        metadata = yaml.safe_load((root / "pack.yaml").read_text(encoding="utf-8"))
        if not isinstance(metadata, dict) or metadata.get("schema_version") != 2:
            raise ValueError("pack.yaml yêu cầu schema_version: 2")
        if not all(isinstance(metadata.get(key), str) and metadata[key].strip() for key in ("name", "version")):
            raise ValueError("name và version phải là chuỗi không rỗng")
        extract = yaml.safe_load((root / "extract.yaml").read_text(encoding="utf-8")) if (root / "extract.yaml").exists() else {}
        extract = extract or {}
        if not isinstance(extract, dict) or extract.get("schema_version", 2) != 2:
            raise ValueError("extract.yaml không đúng schema 2")
        if not isinstance(extract.get("string_patterns", {}), dict):
            raise ValueError("string_patterns phải là mapping")
        for pattern in extract.get("string_patterns", {}).values():
            re.compile(pattern)
        if not isinstance(extract.get("known_packages", []), list) or not all(isinstance(p, str) for p in extract.get("known_packages", [])):
            raise ValueError("known_packages phải là danh sách chuỗi")
        rules = []
        ids = set()
        for path in sorted((root / "rules").glob("*.y*ml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError(f"{path.name}: cần danh sách luật YAML, dùng [] khi trống")
            for item in data:
                if not isinstance(item, dict) or set(item) - {f.name for f in fields(Rule)}:
                    raise ValueError(f"{path.name}: trường luật không hợp lệ")
                rule = Rule(**item)
                if not isinstance(rule.id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", rule.id) or rule.id in ids:
                    raise ValueError(f"ID trùng hoặc không an toàn: {rule.id}")
                if not isinstance(rule.title, str) or not rule.title.strip():
                    raise ValueError(f"{rule.id}: thiếu title")
                if rule.mode not in {"static", "agent"} or rule.on_missing not in {"pass", "fail", "unknown"}:
                    raise ValueError(f"{rule.id}: mode/on_missing không hợp lệ")
                if not isinstance(rule.params, dict) or not isinstance(rule.budget, dict):
                    raise ValueError(f"{rule.id}: params/budget phải là mapping")
                if rule.mode == "static":
                    if rule.check not in CHECKS:
                        raise ValueError(f"{rule.id}: check không hỗ trợ")
                    required = {"manifest_meta": ["key"], "manifest_has": ["collection", "name"], "string_present": ["key"], "string_absent": ["key"], "asset_json_path": ["file", "path"], "asset_json_match": ["file", "path"], "sdk_version": ["key", "min"]}[rule.check]
                    if any(k not in rule.params for k in required):
                        raise ValueError(f"{rule.id}: params cần {required}")
                if rule.mode == "agent":
                    if not rule.question or not isinstance(rule.verdict, dict) or any(not rule.verdict.get(k) for k in ("pass_when", "fail_when", "unknown_when")):
                        raise ValueError(f"{rule.id}: agent cần question và đủ ba verdict")
                    budget = rule.budget.get("max_tool_calls", 25)
                    if type(budget) is not int or budget <= 0:
                        raise ValueError(f"{rule.id}: max_tool_calls phải > 0")
                ids.add(rule.id)
                rules.append(rule)
        context = (root / "context.md").read_text(encoding="utf-8") if (root / "context.md").exists() else ""
        fingerprint = digest_json([(p.relative_to(root).as_posix(), read_text(p)) for p in source_files(root)])
        return RulePack(metadata["name"], metadata["version"], fingerprint, rules, context, extract)
    except (OSError, ValueError, TypeError, KeyError, yaml.YAMLError, re.error) as exc:
        raise AuditError(f"Bộ luật không hợp lệ: {exc}", 5) from exc
