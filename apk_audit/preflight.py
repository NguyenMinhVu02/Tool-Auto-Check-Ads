"""Stop before spending AI quota when the documents clearly belong to another app.

Two consecutive audits ran against ADS SCRIPTS from a different AdMob account and still burned a
full AI pass on a meaningless comparison. Checks are cheap and use only facts already extracted.
"""
import re

from .errors import AuditError
from .inventory import _working_package

DEMO_PUBLISHER = '3940256099942544'


def _publisher(ad_id):
    match = re.match(r'ca-app-pub-(\d+)', str(ad_id or ''))
    return match.group(1) if match else None


class DocumentMismatch(AuditError):
    def __init__(self, details):
        reasons = '; '.join(item['message'] for item in details['reasons'])
        super().__init__(f"Tài liệu có thể không thuộc app này: {reasons}. Chạy lại với --confirm-mismatch nếu chắc tài liệu đúng.", 7)
        self.details = details


def check_documents(documents, facts, inventory):
    """{'level': ok|block, 'reasons': [...], publishers...}; only runs when ADS SCRIPTS/working file were given."""
    result = {'level': 'ok', 'reasons': []}
    if not documents:
        return result

    def add(code, message):
        result['reasons'].append({'code': code, 'message': message})
        result['level'] = 'block'

    if inventory.get('package_match') is False:
        add('package', f"package working file là {_working_package(documents)} nhưng APK là {(facts.get('source') or {}).get('package')}")
    if inventory.get('app_id_match') is False:
        add('app_id', 'AdMob App ID trong app không khớp ADS SCRIPTS')
    ads = documents.get('ads_scripts')
    rows = ads.get('placements') if isinstance(ads, dict) else None
    if rows:
        doc_pubs = {_publisher(r.get('id')) for r in rows if isinstance(r, dict) and r.get('state') == 'active'} - {None, DEMO_PUBLISHER}
        config = (facts.get('assets', {}).get('json', {}).get('ad_config.json') or {})
        app_pubs = {_publisher(v.get('id')) for v in config.values() if isinstance(v, dict)} - {None, DEMO_PUBLISHER}
        result.update(document_publishers=sorted(doc_pubs), app_publishers=sorted(app_pubs))
        if doc_pubs and app_pubs and not doc_pubs & app_pubs:
            add('publisher', 'ID quảng cáo trong app thuộc tài khoản AdMob pub-' + ', pub-'.join(sorted(app_pubs))
                + ' còn ADS SCRIPTS thuộc pub-' + ', pub-'.join(sorted(doc_pubs)))
    return result
