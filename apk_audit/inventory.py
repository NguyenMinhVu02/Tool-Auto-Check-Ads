"""Deterministic placement inventory; references are leads, not proof of load/show."""

import re
from xml.etree import ElementTree
from .placement_policy import config_key, integration_policy, normalize_ads_document


PACKAGE = re.compile(r"\b(?:[A-Za-z_][A-Za-z_0-9]*\.)+[A-Za-z_][A-Za-z_0-9]*\b")


def _working_package(documents):
    checklist = documents.get("checklist")
    rows = checklist.get("checklist_rows", []) if isinstance(checklist, dict) else []
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict):
            continue
        if "package name" in (row.get("task", "") + " " + row.get("detail", "")).lower():
            for field in ("detail", "document"):
                match = PACKAGE.search(row.get(field, ""))
                if match:
                    return match.group(0)
    return None


def _manifest_app_id(workspace, facts):
    value = facts.get("manifest", {}).get("meta_data", {}).get("com.google.android.gms.ads.APPLICATION_ID")
    if not isinstance(value, str):
        return None
    if not value.startswith("@string/"):
        return value
    resource = workspace / "resources/res/values/strings.xml"
    try:
        root = ElementTree.parse(resource).getroot()
    except (OSError, ElementTree.ParseError):
        return None
    name = value.removeprefix("@string/")
    for item in root.findall("string"):
        if item.get("name") == name:
            return "".join(item.itertext()).strip()
    return None


def build_inventory(workspace, facts, documents, files=None):
    ads = normalize_ads_document(documents.get("ads_scripts", {}))
    rows = ads.get("placements") if isinstance(ads, dict) else None
    config = facts.get("assets", {}).get("json", {}).get("ad_config.json", {})
    if not isinstance(config, dict):
        config = {}
    local = {key: value for key, value in config.items() if isinstance(value, dict) and "id" in value}
    # Compare under the app's own placement name when the document uses a known alias.
    documented = {(config_key(row["name"], local) or row["name"]): row for row in rows or [] if isinstance(row, dict) and row.get("name")}
    expected = {key: row for key, row in documented.items() if row['state'] == 'active'}
    optional = {key for key in documented.keys() | local.keys() if key.casefold() == 'inter_onboarding'}
    shared = sorted(expected.keys() & local.keys())
    expected_package = _working_package(documents)
    expected_app_id = ads.get("app_id") if isinstance(ads, dict) else None
    actual_app_id = _manifest_app_id(workspace, facts) if expected_app_id else None
    inventory = {
        "documents_available": isinstance(rows, list),
        "documented_count": len(documented),
        "expected_count": len(expected),
        "local_count": len(local),
        "missing_local": sorted(expected.keys() - local.keys() - optional),
        "extra_local": sorted(local.keys() - documented.keys() - optional) if documented else [],
        "optional_placements": sorted(optional),
        "disabled_placements": sorted(key for key, row in documented.items() if row['state'] == 'disabled'),
        "uncertain_placements": sorted(key for key, row in documented.items() if row['state'] == 'unknown'),
        "integration_policy": integration_policy(ads),
        "document_warnings": ads.get('warnings', []) if isinstance(ads, dict) else [],
        "matching_ids": [key for key in shared if expected[key].get("id") and expected[key]["id"] == local[key].get("id")],
        "mismatched_ids": [key for key in shared if expected[key].get("id") and expected[key]["id"] != local[key].get("id")],
        "empty_expected_ids": [key for key in shared if not expected[key].get("id")],
        "package_match": expected_package == facts.get("source", {}).get("package") if expected_package else None,
        "app_id_match": expected_app_id == actual_app_id if expected_app_id and actual_app_id else None,
        "code_references": {},
        "config_references": {},
    }
    keys = sorted(documented.keys() | local.keys())
    config_names = {"ad_config.json", "ad_config_debug.json", "ad_remote_config"}
    if keys or config_names:
        pattern = re.compile('"(' + '|'.join(re.escape(key) for key in sorted(set(keys) | config_names)) + ')"')
        for path in ((workspace / "sources").rglob("*.java") if files is None else
                     (p for p in files if p.suffix == ".java" and p.is_relative_to(workspace / "sources"))):
            try:
                with path.open(encoding="utf-8", errors="replace") as source:
                    for line_number, line in enumerate(source, 1):
                        for match in pattern.finditer(line):
                            group = "config_references" if match.group(1) in config_names else "code_references"
                            matches = inventory[group].setdefault(match.group(1), [])
                            if len(matches) < 8:
                                matches.append({"file": path.relative_to(workspace).as_posix(), "line": line_number})
            except OSError:
                continue
    return inventory


def inventory_observations(inventory):
    if not inventory["documents_available"]:
        return ["Chưa có ADS SCRIPTS dạng placement để đối chiếu inventory ID."]
    lines = [f"ADS SCRIPTS: {inventory['expected_count']} placement; ad_config.json: {inventory['local_count']} placement; {len(inventory['matching_ids'])} ID chung khớp."]
    for field, label in (("missing_local", "Thiếu trong config local"),
                         ("extra_local", "Thừa trong config local"),
                         ("mismatched_ids", "ID lệch ADS SCRIPTS"),
                         ("empty_expected_ids", "ID trống trong ADS SCRIPTS")):
        if inventory[field]:
            lines.append(label + ": " + ", ".join(inventory[field]))
    for field, label in (("optional_placements", "Placement tùy chọn, không bắt buộc có local/load/show"),
                         ("disabled_placements", "Placement không dùng theo ADS SCRIPTS"),
                         ("uncertain_placements", "Chưa xác định trạng thái sử dụng trong tài liệu")):
        if inventory.get(field):
            lines.append(label + ": " + ", ".join(inventory[field]))
    lines.extend(inventory.get('document_warnings', []))
    if inventory["package_match"] is not None:
        lines.append("Package APK " + ("khớp" if inventory["package_match"] else "không khớp") + " working file.")
    if inventory["app_id_match"] is not None:
        lines.append("AdMob App ID manifest " + ("khớp" if inventory["app_id_match"] else "không khớp") + " ADS SCRIPTS.")
    lines.append("Code references chỉ là vị trí có chuỗi placement trong Java đã giải mã; thiếu reference không chứng minh slot không được dùng.")
    return lines
