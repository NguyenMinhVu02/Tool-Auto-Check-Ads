from ..contracts import Finding
from ..utils import lookup
from .checks import read_value, compare
from .code_facts import app_roots, code_profile, limits_note
from .custom import CUSTOM_CHECKS

# What each deterministic check stands on. Strings, manifest attributes and asset JSON survive
# obfuscation; names do not, so "not found" is only a defect when the profile says it is conclusive.
CHECK_BASIS = {
    'ad_config_flags': 'file cấu hình trong assets của APK', 'debug_test_ids': 'file cấu hình trong assets của APK',
    'screen_class_names': 'AndroidManifest.xml', 'screen_orientation_lock': 'AndroidManifest.xml',
    'remote_config_keys': 'chuỗi trong mã đã giải mã', 'interstitial_interval': 'lời gọi hàm trong mã đã giải mã',
    'language_dev_toggle': 'lời gọi hàm trong mã đã giải mã',
    'mediation_adapters': 'tên lớp adapter/SDK trong mã đã giải mã',
    'splash_ads_notice': 'strings/layout trong resources của APK', 'language_done_delay': 'hằng số trong mã đã giải mã',
    'uninstall_setup': 'AndroidManifest.xml và lớp ShortcutInfo trong mã đã giải mã',
}
CODE_CHECKS = {'language_done_delay', 'remote_config_keys', 'interstitial_interval', 'language_dev_toggle', 'mediation_adapters'}

def evaluate_static(rule, facts, documents=None, workspace=None):
    finding = Finding.for_rule(rule, resolved_by="static")
    if rule.check in CUSTOM_CHECKS:
        for key, value in CUSTOM_CHECKS[rule.check](rule, facts, documents, workspace).items():
            setattr(finding, key, value)
        basis = CHECK_BASIS.get(rule.check, '')
        limits = limits_note(code_profile(workspace, app_roots(facts))) if rule.check in CODE_CHECKS and workspace else ''
        finding.verification = {'basis': basis, 'limits': limits,
                                'confidence': 'cao' if finding.status in {'PASS', 'FAIL'} else 'thấp'}
        return finding
    expected = rule.params.get("equals", rule.params.get("min"))
    if "equals_doc" in rule.params:
        try:
            expected = lookup(documents or {}, rule.params["equals_doc"])
        except (KeyError, IndexError, TypeError, ValueError):
            finding.status = "SKIPPED"
            finding.reason = "missing_document"
            finding.reasoning = "Cần tài liệu hoặc giá trị: " + rule.params["equals_doc"]
            return finding
    finding.expected = expected
    try:
        value = read_value(rule, facts)
    except (KeyError, IndexError):
        finding.status = rule.on_missing.upper()
        finding.reason = "missing_fact"
        finding.reasoning = "Không có dữ liệu tại đường dẫn được khai báo"
        return finding
    try:
        finding.actual = value
        finding.status = "PASS" if compare(rule, value, expected) else "FAIL"
        finding.reasoning = "Đối chiếu dữ liệu facts theo tham số của rule pack"
    except (ValueError, TypeError, KeyError) as exc:
        finding.reason = "rule_error"
        finding.reasoning = str(exc)
    return finding
