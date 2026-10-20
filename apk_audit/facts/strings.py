import re
from ..utils import source_files, read_text

def extract_strings(root, extract, files=None):
    patterns = {key: re.compile(pattern) for key, pattern in extract.get("string_patterns", {}).items()}
    result = {"admob_app_ids": [], "ad_unit_ids": [], "sdk_versions": {}, "candidates": {key: [] for key in patterns}}
    warnings = ["sdk_versions_not_extracted", "strings_from_decoded_text_only"]
    for path in (source_files(root) if files is None else files):
        if path.suffix not in {".java", ".kt", ".smali", ".xml", ".json", ".properties"}:
            continue
        try:
            content = read_text(path)
        except (ValueError, OSError):
            warnings.append(f"strings_unreadable: {path.relative_to(root)}")
            continue
        for line_number, line in enumerate(content.splitlines(), 1):
            for value in re.findall(r'"([^"\n]*)"', line):
                for key, pattern in patterns.items():
                    if pattern.search(value):
                        result["candidates"][key].append({"value": value, "source": path.relative_to(root).as_posix(), "line": line_number})
    return result, warnings
