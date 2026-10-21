from ..contracts import Finding
from ..utils import lookup
from .checks import read_value, compare
from .custom import CUSTOM_CHECKS

def evaluate_static(rule, facts, documents=None, workspace=None):
    finding = Finding.for_rule(rule, resolved_by="static")
    if rule.check in CUSTOM_CHECKS:
        for key, value in CUSTOM_CHECKS[rule.check](rule, facts, documents, workspace).items():
            setattr(finding, key, value)
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
