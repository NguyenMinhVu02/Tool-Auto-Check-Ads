import re
from urllib.parse import urlparse, parse_qs
from .errors import AuditError

def resolve(url):
    parsed = urlparse(url)
    package = parse_qs(parsed.query).get("id", [""])[0]
    if parsed.scheme != "https" or parsed.hostname != "play.google.com" or parsed.path != "/store/apps/details" or not re.fullmatch(r"[A-Za-z][\w]*(?:\.[A-Za-z][\w]*)+", package):
        raise AuditError("Link Google Play không hợp lệ")
    return {"play_url": url, "package": package, "version_name": None}
