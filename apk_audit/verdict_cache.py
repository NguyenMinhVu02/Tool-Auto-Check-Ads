import json
from pathlib import Path
from .utils import digest_json, write_json


def verdict_record(finding, trace, **extra):
    record = {"finding":finding.to_dict(), "trace":trace, **extra}
    record["checksum"] = digest_json(record)
    return record


def valid_record(value):
    if not isinstance(value,dict) or not isinstance(value.get("finding"),dict) or not isinstance(value.get("trace"),dict):
        return False
    return value.get("checksum") == digest_json({k:v for k,v in value.items() if k != "checksum"})


class VerdictCache:
    def __init__(self, directory):
        self.root = Path(directory) / "verdicts"
    def key(self, facts, pack, rule, engine, documents, dependencies=None, policy=None, identity=None):
        from dataclasses import asdict
        return digest_json({"tool":"audit-policy-v2", "policy": policy, "engine_identity": identity, "apk": facts["source"].get("sha256"),
                            "workspace":facts["workspace"]["content_sha256"],
                            "pack_name":pack.name, "pack_version":pack.version,
                            "context":pack.context, "extract":pack.extract,
                            "rule":asdict(rule), "engine":engine,
                            "documents":documents, "dependencies":dependencies})
    def get(self, key):
        try:
            value = json.loads((self.root / (key+".json")).read_text(encoding="utf-8"))
            return value if valid_record(value) else None
        except (OSError, ValueError):
            return None
    def put(self, key, finding, trace):
        write_json(self.root / (key+".json"), verdict_record(finding,trace))
