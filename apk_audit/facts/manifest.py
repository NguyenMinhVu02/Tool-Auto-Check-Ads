import xml.etree.ElementTree as ET
from ..utils import safe_path, read_text

ANDROID = "{http://schemas.android.com/apk/res/android}"

def parse_manifest(root):
    candidates = ["resources/AndroidManifest.xml", "AndroidManifest.xml"]
    relative = next((x for x in candidates if safe_path(root, x).is_file()), None)
    if relative is None:
        raise ValueError("Không tìm thấy AndroidManifest.xml đã decode")
    xml = ET.fromstring(read_text(safe_path(root, relative)))
    package = xml.get("package", "")
    def qualified(name):
        if not name:
            return None
        return package + name if name.startswith(".") else package + "." + name if "." not in name else name
    def java_file(name):
        if not name:
            return None
        rel = "sources/" + name.replace(".", "/") + ".java"
        return rel if safe_path(root, rel).is_file() else None
    def integer(value):
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    sdk = xml.find("uses-sdk")
    app = xml.find("application")
    result = {"file": relative, "package": package,
              "version_name": xml.get(ANDROID+"versionName"),
              "version_code": integer(xml.get(ANDROID+"versionCode")),
              "min_sdk": integer(sdk.get(ANDROID+"minSdkVersion")) if sdk is not None else None,
              "target_sdk": integer(sdk.get(ANDROID+"targetSdkVersion")) if sdk is not None else None,
              "application_class": None, "application_file": None,
              "permissions": [x.get(ANDROID+"name") for x in xml.findall("uses-permission")],
              "meta_data": {}, "activities": [], "services": [], "receivers": [], "providers": []}
    if app is None:
        return result
    name = qualified(app.get(ANDROID+"name"))
    result.update(application_class=name, application_file=java_file(name))
    result["meta_data"] = {x.get(ANDROID+"name"): x.get(ANDROID+"value", x.get(ANDROID+"resource")) for x in app.findall("meta-data")}
    for tag, key in [("activity", "activities"), ("activity-alias", "activities"), ("service", "services"), ("receiver", "receivers"), ("provider", "providers")]:
        for item in app.findall(tag):
            name = qualified(item.get(ANDROID+"name"))
            exported = item.get(ANDROID+"exported")
            launcher = any(any(a.get(ANDROID+"name") == "android.intent.action.MAIN" for a in f.findall("action")) and any(c.get(ANDROID+"name") == "android.intent.category.LAUNCHER" for c in f.findall("category")) for f in item.findall("intent-filter"))
            result[key].append({"name": name, "file": java_file(name), "exported": exported == "true" if exported in {"true", "false"} else None, "is_launcher": launcher})
    return result
