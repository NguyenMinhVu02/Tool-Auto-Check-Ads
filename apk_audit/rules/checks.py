import re
from ..utils import lookup

def read_value(rule, facts):
    p = rule.params
    if rule.check == "manifest_meta":
        return facts["manifest"]["meta_data"][p["key"]]
    if rule.check == "manifest_has":
        return any(x["name"] == p["name"] for x in facts["manifest"][p["collection"]])
    if rule.check in {"string_present", "string_absent"}:
        return facts["strings"]["candidates"][p["key"]]
    if rule.check.startswith("asset_json_"):
        return lookup(facts["assets"]["json"][p["file"]], p["path"])
    if rule.check == "sdk_version":
        return facts["strings"]["sdk_versions"][p["key"]]
    raise ValueError("check không hỗ trợ")

def compare(rule, value, expected):
    p = rule.params
    if rule.check == "sdk_version":
        def version(v):
            if not re.fullmatch(r"\d+(?:\.\d+)*", str(v)):
                raise ValueError("SDK version chỉ hỗ trợ phiên bản số x.y.z")
            return tuple(int(x) for x in str(v).split("."))
        actual, minimum = version(value), version(p["min"])
        length = max(len(actual), len(minimum))
        return actual+(0,)*(length-len(actual)) >= minimum+(0,)*(length-len(minimum))
    if rule.check in {"string_present", "string_absent"}:
        values = [x["value"] for x in value]
        present = any(re.search(p["regex"], str(x)) for x in values) if "regex" in p else expected in values if "equals" in p or "equals_doc" in p else bool(values)
        return not present if rule.check == "string_absent" else present
    if "regex" in p:
        return re.fullmatch(p["regex"], str(value)) is not None
    if "equals" in p or "equals_doc" in p:
        return value == expected
    return value if rule.check == "manifest_has" else value is not None
