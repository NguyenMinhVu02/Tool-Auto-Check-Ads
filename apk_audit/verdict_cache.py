import json
from pathlib import Path
from .utils import digest_json, write_json

class VerdictCache:
    def __init__(self, directory):
        self.root = Path(directory) / "verdicts"
    def key(self, facts, pack, rule, engine, documents, dependencies=None):
        from dataclasses import asdict
        return digest_json({"tool":"0.6.0", "apk": facts["source"].get("sha256"),
                            "workspace":facts["workspace"]["content_sha256"],
                            "pack_name":pack.name, "pack_version":pack.version,
                            "context":pack.context, "extract":pack.extract,
                            "rule":asdict(rule), "engine":engine,
                            "documents":documents, "dependencies":dependencies})
    def get(self, key):
        try:
            value = json.loads((self.root / (key+".json")).read_text(encoding="utf-8"))
            return value if isinstance(value, dict) and isinstance(value.get("finding"), dict) and isinstance(value.get("trace"), dict) else None
        except (OSError, ValueError):
            return None
    def put(self, key, finding, trace):
        write_json(self.root / (key+".json"), {"finding":finding.to_dict(),"trace":trace})
