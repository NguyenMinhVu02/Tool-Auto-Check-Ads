"""Reusable lexical leads for decoded sources; no inferred call graph.

Only the cold build scans source text. Bundles read small windows from selected
files; cached paths are relative so identical content can move to another root.
The caller supplies the digest of the trusted, immutable decoded workspace.
"""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from .utils import safe_path


INDEX_POLICY = "audit-vocabulary-source-v2"
_SUFFIXES = {".java", ".kt", ".smali", ".xml", ".json", ".properties", ".txt"}
_MAX_TERMS = 192
_MAX_SYMBOLS = 16
_MAX_LINE = 65536
_WORD = re.compile(r"[A-Za-z_][A-Za-z_0-9$]*")
_CAMEL = re.compile(r"([a-z0-9])([A-Z])")
_STRING = re.compile(r'"((?:[^"\\]|\\.)*)"')
_METHOD = re.compile(r"(?:\b(?:public|private|protected|static|final|synchronized|suspend|fun|void)\s+)[^;{}=]*?\b([\w$]+)\s*\(")
_AREAS = {
    "init": "application onCreate initialize init registerActivityLifecycleCallbacks MobileAds lifecycle",
    "remote_config": "FirebaseRemoteConfig fetch activate timeout ad_config fallback local remote debug release",
    "config": "ad_config remote config id enable placement admob_id",
    "splash": "splash uninstall inter_splash native_language native_lang banner_splash timeout",
    "language": "language lang native_language native_lang native_lang_click onboarding obd settings done",
    "onboarding": "onboarding onboard obd native_obd native_full inter_onboarding positionIndicator",
    "welcome": "welcome resume open_resume appopen lifecycle purchase",
    "render": "load observe observer populate render native isEnable purchase network null lifecycle",
    "tracking": "FirebaseAnalytics logEvent scr_view scr_click request_ad ad_load user_close_ad",
    "banner": "banner reloadIntervalSeconds handler pause destroy",
    "cross_flow": "callback retry timeout onResume onStart postDelayed purchase offline fail destroy",
}
_GUIDANCE = "AI may search the entire workspace beyond these lexical leads; missing or truncated hits do not prove missing behavior."
_LIMITATIONS = "Limited audit vocabulary/placement keys; lexical heuristic, no call graph or runtime proof."


def _tokens(text):
    result = set()
    for word in _WORD.findall(text):
        result.add(word.lower()[:128])
        result.update(part.lower()[:128] for part in _CAMEL.sub(r"\1_\2", word).split("_") if len(part) >= 3)
    return {word for word in result if len(word) >= 3}


_VOCABULARY = _tokens(" ".join(_AREAS.values()))
_PLACEMENT = re.compile(r"(?:native|inter|banner|open|app_open|reward|rewarded|ad)_[a-z][a-z0-9_]{1,94}")
_EVENT = re.compile(r"[a-z][a-z0-9_]{0,94}_(?:scr_view|scr_click|request_ad|ad_load|user_close_ad)")
_AD_ID = re.compile(r"ca-app-pub-\d{8,}(?:[/~]\d+)?")


def _audit_tokens(text):
    """Discard arbitrary SDK identifiers while retaining custom placement keys."""
    tokens = _tokens(text)
    result = {token for token in tokens if token in _VOCABULARY or _PLACEMENT.fullmatch(token) or _EVENT.fullmatch(token)}
    if _AD_ID.search(text):
        result.add("admob_id")
    return result


def _write_cache(path, data):
    """Compact atomic JSON; keep the shared report writer's formatting unchanged."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".source-index-", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, separators=(",", ":"))
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _lines(path):
    """Stream physical lines without allocating arbitrary single-line literals."""
    with path.open(encoding="utf-8", errors="replace") as stream:
        number = 0
        while chunk := stream.readline(_MAX_LINE + 1):
            number += 1
            clipped = len(chunk) > _MAX_LINE
            if clipped and not chunk.endswith("\n"):
                while tail := stream.readline(_MAX_LINE + 1):
                    if tail.endswith("\n"):
                        break
            yield number, chunk[:_MAX_LINE].rstrip("\r\n"), clipped


class SourceIndex:
    def __init__(self, root, data, cache_hit):
        self.root = root
        self.policy = data["policy"]
        self.cache_hit = cache_hit
        self.stats = dict(data["stats"])
        self._files = data["files"]
        self._terms = data["terms"]
        self._by_path = {item["file"]: index for index, item in enumerate(self._files)}
        self._path_terms = {}
        for file_id, item in enumerate(self._files):
            for token in _audit_tokens(item["file"]):
                self._path_terms.setdefault(token, []).append(file_id)

    @classmethod
    def build(cls, workspace, content_hash, cache_dir):
        root = Path(workspace).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("workspace must be a directory")
        cache_dir = Path(cache_dir).resolve()
        key = hashlib.sha256(json.dumps([str(content_hash), INDEX_POLICY]).encode()).hexdigest()
        cache = cache_dir / ("source-index-" + key + ".json")
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            cls._validate(data, root, str(content_hash))
        except (OSError, ValueError, TypeError, KeyError, OverflowError):
            data = cls._scan(root, str(content_hash), cache_dir)
            # A read-only/full cache must not prevent a read-only audit.
            try:
                _write_cache(cache, data)
            except OSError:
                pass
            return cls(root, data, False)
        return cls(root, data, True)

    @staticmethod
    def _validate(data, root, content_hash):
        if data["policy"] != INDEX_POLICY or data["content_hash"] != content_hash:
            raise ValueError("stale index")
        files, terms, stats = data["files"], data["terms"], data["stats"]
        if not isinstance(files, list) or not isinstance(terms, dict) or not isinstance(stats, dict):
            raise ValueError("invalid index shape")
        for key in ("files_indexed", "files_skipped", "files_truncated", "lines_indexed", "bytes_indexed", "methods_indexed", "strings_indexed"):
            if type(stats[key]) is not int or stats[key] < 0:
                raise ValueError("invalid statistics")
        seen = set()
        checked_parents = {}
        for item in files:
            relative = item["file"]
            if not isinstance(relative, str) or not relative or relative in seen:
                raise ValueError("invalid file")
            seen.add(relative)
            rel = Path(relative)
            if rel.is_absolute() or ".." in rel.parts or "\\" in relative:
                raise ValueError("invalid relative path")
            # Most sources share package directories. Resolve each parent once,
            # then only inspect the leaf for a symlink instead of resolving the
            # workspace and every directory component for each of 60k files.
            if rel.parent not in checked_parents:
                parent = (root / rel.parent).resolve()
                if not parent.is_relative_to(root):
                    raise ValueError("source parent escapes workspace")
                checked_parents[rel.parent] = parent
            path = checked_parents[rel.parent] / rel.name
            if path.is_symlink() and not path.resolve().is_relative_to(root):
                raise ValueError("source escapes workspace")
            if type(item["line_count"]) is not int or item["line_count"] < 0:
                raise ValueError("invalid file length")
            if type(item["truncated"]) is not bool:
                raise ValueError("invalid file truncation flag")
            for field in ("methods", "strings"):
                if not isinstance(item[field], list):
                    raise ValueError("invalid symbols")
                for symbol in item[field]:
                    if not isinstance(symbol["value"], str) or type(symbol["line"]) is not int or not 1 <= symbol["line"] <= item["line_count"]:
                        raise ValueError("invalid symbol")
        for token, postings in terms.items():
            if not isinstance(token, str) or not isinstance(postings, list):
                raise ValueError("invalid token")
            for posting in postings:
                if not isinstance(posting, list) or len(posting) != 2:
                    raise ValueError("invalid posting")
                file_id, line = posting
                if type(file_id) is not int or not 0 <= file_id < len(files) or type(line) is not int or not 1 <= line <= files[file_id]["line_count"]:
                    raise ValueError("invalid location")

    @staticmethod
    def _scan(root, content_hash, cache_dir):
        files, terms = [], {}
        stats = dict.fromkeys(("files_indexed", "files_skipped", "files_truncated", "lines_indexed", "bytes_indexed", "methods_indexed", "strings_indexed"), 0)
        for directory, directories, names in os.walk(root, followlinks=False):
            directories[:] = sorted(name for name in directories if not name.startswith(".")
                                    and not (Path(directory) / name).is_symlink()
                                    and (Path(directory) / name).resolve() != cache_dir)
            for name in sorted(names):
                path = Path(directory) / name
                if path.suffix.lower() not in _SUFFIXES:
                    continue
                # os.walk does not follow directory symlinks; file symlinks are
                # skipped too. Bundle reads re-check resolved selected paths.
                if path.is_symlink():
                    stats["files_skipped"] += 1
                    continue
                relative = path.relative_to(root).as_posix()
                item = {"file": relative, "line_count": 0, "methods": [], "strings": [], "truncated": False}
                locations = {}
                try:
                    size = path.stat().st_size
                    for number, text, clipped in _lines(path):
                        item["line_count"] = number
                        item["truncated"] |= clipped
                        for token in sorted(_audit_tokens(text)):
                            if token not in locations:
                                if len(locations) < _MAX_TERMS:
                                    locations[token] = number
                                else:
                                    item["truncated"] = True
                        for field, regex in (("methods", _METHOD), ("strings", _STRING)):
                            for match in regex.finditer(text):
                                if not _audit_tokens(match[1]):
                                    continue
                                if len(item[field]) < _MAX_SYMBOLS:
                                    item[field].append({"value": match[1][:160], "line": number})
                                    item["truncated"] |= len(match[1]) > 160
                                else:
                                    item["truncated"] = True
                except OSError:
                    stats["files_skipped"] += 1
                    continue
                file_id = len(files)
                files.append(item)
                for token, line in locations.items():
                    terms.setdefault(token, []).append([file_id, line])
                stats["files_indexed"] += 1
                stats["bytes_indexed"] += size
                stats["lines_indexed"] += item["line_count"]
                stats["files_truncated"] += int(item["truncated"])
                stats["methods_indexed"] += len(item["methods"])
                stats["strings_indexed"] += len(item["strings"])
        return {"policy": INDEX_POLICY, "content_hash": content_hash, "files": files, "terms": terms, "stats": stats}

    def bundle(self, rule, facts, inventory, max_chars=20000):
        """Return JSON bounded using json.dumps(..., ensure_ascii=False).

        Lines are one-based. Coverage counts indexed/candidate/returned files,
        never semantic branch coverage. Budgets below 700 chars are rejected.
        """
        if type(max_chars) is not int or max_chars < 700:
            raise ValueError("max_chars must be an integer >= 700")
        facts = facts.to_dict() if hasattr(facts, "to_dict") else facts
        get = rule.get if isinstance(rule, dict) else lambda key, default="": getattr(rule, key, default)
        area = get("area", "general")
        query = _tokens(_AREAS.get(area, str(area)))
        query |= _tokens(str(get("question", ""))) - {"the", "and", "not", "ads", "string", "class"}
        query |= _audit_tokens(str(get("question", "")))
        ranked = {}

        def add(relative, line, weight, reason):
            file_id = self._by_path.get(relative) if isinstance(relative, str) else None
            if file_id is None or type(line) is not int or not 1 <= line <= self._files[file_id]["line_count"]:
                return
            candidate = ranked.setdefault(file_id, {"score": 0, "lines": {}, "terms": set()})
            candidate["score"] += weight
            candidate["lines"][line] = candidate["lines"].get(line, 0) + weight
            candidate["terms"].add(reason)

        for token in sorted(query):
            for file_id, line in self._terms.get(token, []):
                add(self._files[file_id]["file"], line, 12, token)
        filename_hits = set()
        for token in query:
            filename_hits.update(self._path_terms.get(token, []))
        for file_id in sorted(filename_hits):
            add(self._files[file_id]["file"], 1, 8, "filename")
        manifest = (facts or {}).get("manifest", {})
        add(manifest.get("file"), 1, 80, "manifest")
        add(manifest.get("application_file"), 1, 100, "Application")
        for path in ("resources/AndroidManifest.xml", "AndroidManifest.xml"):
            if path != manifest.get("file"):
                add(path, 1, 80, "manifest")
        for hint in get("start_hints", []) or []:
            add(hint, 1, 50, "rule_start_hint")
        for field in ("code_references", "config_references"):
            references = (inventory or {}).get(field, {})
            if not isinstance(references, dict):
                continue
            for key, refs in references.items():
                if not isinstance(key, str) or not isinstance(refs, list):
                    continue
                relevant = bool(_tokens(key) & query) or area in {"config", "init", "render", "cross_flow"}
                if field == "config_references" or relevant:
                    for ref in refs:
                        if isinstance(ref, dict):
                            add(ref.get("file"), ref.get("line", 1), 160 if relevant else 45, key[:128])
        candidates = sorted(ranked, key=lambda file_id: (-ranked[file_id]["score"], self._files[file_id]["file"]))
        result = {"policy": self.policy, "cache_hit": self.cache_hit, "heuristic": True,
                  "limitations": _LIMITATIONS, "search_guidance": _GUIDANCE,
                  "coverage": {"files_indexed": self.stats["files_indexed"], "candidate_files": len(candidates),
                               "files_included": 0, "files_skipped": self.stats["files_skipped"],
                               "files_truncated": self.stats["files_truncated"], "index_filtered": True,
                               "vocabulary_policy": self.policy},
                  "truncated": bool(self.stats["files_truncated"] or self.stats["files_skipped"]), "snippets": []}

        def length():
            return len(json.dumps(result, ensure_ascii=False))

        # Reading at most 24 selected files prevents materializing SDK libraries.
        for file_id in candidates[:24]:
            item, lead = self._files[file_id], ranked[file_id]
            anchors = sorted(lead["lines"], key=lambda line: (-lead["lines"][line], line))[:3]
            wanted = set()
            for anchor in anchors:
                wanted.update(range(max(1, anchor - 3), min(item["line_count"], anchor + 5) + 1))
            try:
                path = safe_path(self.root, item["file"])
                if path.is_symlink() or not path.is_file():
                    raise ValueError("source no longer available")
                selected = []
                for number, text, clipped in _lines(path):
                    if number in wanted:
                        selected.append({"line": number, "text": text[:1200]})
                    if number >= max(wanted):
                        break
            except (OSError, ValueError):
                result["truncated"] = True
                continue
            if not selected:
                result["truncated"] = True
                continue
            # A snippet is a contiguous window, so start + numbered lines cannot
            # imply a contiguous excerpt over omitted source between anchors.
            windows = []
            for line in selected:
                if not windows or line["line"] != windows[-1][-1]["line"] + 1:
                    windows.append([])
                windows[-1].append(line)
            accepted = False
            for lines in windows:
                snippet = {"file": item["file"], "start": lines[0]["line"], "lines": lines,
                           "matched_terms": sorted(lead["terms"])[:12],
                           "truncated": item["truncated"] or len(wanted) < item["line_count"] or any(len(x["text"]) == 1200 for x in lines)}
                result["snippets"].append(snippet)
                result["coverage"]["files_included"] += int(not accepted)
                while length() > max_chars and len(snippet["lines"]) > 1:
                    # Preserve the line closest to the strongest lexical anchor.
                    end = -1 if abs(snippet["lines"][-1]["line"] - anchors[0]) >= abs(snippet["lines"][0]["line"] - anchors[0]) else 0
                    snippet["lines"].pop(end)
                    snippet["start"] = snippet["lines"][0]["line"]
                    snippet["truncated"] = result["truncated"] = True
                if length() > max_chars:
                    result["snippets"].pop()
                    result["coverage"]["files_included"] -= int(not accepted)
                    result["truncated"] = True
                else:
                    accepted = True
                    result["truncated"] |= snippet["truncated"]
                if length() > max_chars - 250:
                    break
        if result["coverage"]["files_included"] < len(candidates):
            result["truncated"] = True
        # Fixed metadata is small; guard even huge file-count digit widths.
        if length() > max_chars:
            raise ValueError("max_chars too small for bundle metadata")
        return result
