import json
from pathlib import Path
import time
from .agent import evaluate
from .config import cache_path
from .contracts import Finding
from .documents import load_document
from .engines import get_engine
from .errors import AuditError
from .facts import build_facts
from .inventory import build_inventory, inventory_observations
from .fetch import fetch
from .playstore import resolve
from .report import write_report
from .rules.engine import evaluate_static
from .rules.loader import load_pack
from .tools import WorkspaceTools
from .unpack import unpack
from .utils import write_json
from .verdict_cache import VerdictCache

def prepare(target, cache_dir=None, no_cache=False, provider=None):
    value = str(target)
    if value.startswith(("http://", "https://")):
        source = resolve(value)
        archive = fetch(source, cache_path(cache_dir), provider, no_cache)
        workspace, metadata = unpack(archive, cache_path(cache_dir), no_cache)
        return workspace, {**metadata, **source}
    path = Path(target).expanduser().resolve()
    if path.is_dir():
        if not any((path / item).exists() for item in ("resources/AndroidManifest.xml", "AndroidManifest.xml", "sources")):
            raise AuditError("Thư mục không phải workspace jadx (cần sources hoặc manifest)")
        return path, {"download_source": "workspace"}
    if not path.is_file():
        raise AuditError(f"Không tìm thấy đầu vào: {path}")
    return unpack(path, cache_path(cache_dir), no_cache)

def run(target, *, rules=None, out=None, engine="codex", only=None, cache_dir=None,
        refresh=False, refresh_rule=None, max_tool_calls=400, trace=False,
        format="both", no_cache=False, ads_scripts=None, checklist=None, provider=None,
        progress=None, rule_progress=None):
    started = time.monotonic()
    if type(max_tool_calls) is not int or max_tool_calls < 0:
        raise AuditError("max_tool_calls phải >= 0")
    if format not in {"md", "json", "both"}:
        raise AuditError("format không hợp lệ")
    pack = load_pack(rules)
    selected = [r for r in pack.rules if only is None or only in {r.id, r.area}]
    if only is not None and not selected:
        raise AuditError(f"Không có rule hoặc area: {only}", 5)
    if refresh_rule and refresh_rule not in {r.id for r in pack.rules}:
        raise AuditError(f"Không có rule: {refresh_rule}", 5)
    adapter = get_engine(engine) if isinstance(engine, str) else engine
    if progress:
        progress("documents")
    documents = {k:v for k,v in {"ads_scripts": load_document(ads_scripts, "ads_scripts"), "checklist":load_document(checklist, "checklist")}.items() if v is not None}
    if progress:
        progress("unpack")
    workspace, source = prepare(target, cache_dir, no_cache, provider)
    if progress:
        progress("facts")
    facts = build_facts(workspace, source, pack.extract).to_dict()
    identity = facts["workspace"]["content_sha256"][:12]
    output = Path(out or Path("out") / identity).resolve()
    if output == workspace or output.is_relative_to(workspace):
        raise AuditError("Thư mục out phải nằm ngoài workspace đầu vào")
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "facts.json", facts)
    inventory = build_inventory(workspace, facts, documents)
    write_json(output / "inventory.json", inventory)
    inventory_context = {key: inventory[key] for key in ("expected_count", "local_count", "missing_local", "extra_local", "mismatched_ids", "config_references")}
    tools = WorkspaceTools(workspace, facts)
    write_json(output / "xref_index.json", tools.xref_index)
    cache = VerdictCache(cache_path(cache_dir))
    findings = []
    used = 0
    if progress:
        progress("rules")
    for index, rule in enumerate(selected, 1):
        if rule_progress:
            rule_progress("start", {"index": index, "total": len(selected), "rule_id": rule.id, "title": rule.title, "completed": index - 1})
        if rule.mode == "static":
            try:
                finding = evaluate_static(rule, facts, documents)
            except Exception as exc:
                finding = Finding.for_rule(rule, reason="rule_error", reasoning=str(exc), resolved_by="static")
        else:
            prior = [{"rule_id": item["rule_id"], "status": item["status"], "reasoning": item["reasoning"][:700]}
                     for item in findings] if rule.id == "ADS_CROSS_FLOW_BUGS" else None
            key = cache.key(facts, pack, rule, adapter.name, documents, dependencies=prior)
            cached = None if refresh or refresh_rule == rule.id or adapter.name == "none" else cache.get(key)
            finding = None
            if cached:
                try:
                    finding = Finding(**cached["finding"])
                    if finding.rule_id != rule.id or not isinstance(finding.status, str) or finding.status not in {"PASS","FAIL","UNKNOWN","SKIPPED"}:
                        finding = None
                    else:
                        finding.from_cache = True
                        run_trace = cached["trace"]
                except TypeError:
                    finding = None
            if finding is None:
                context = pack.context + "\nDocuments:\n" + json.dumps(documents, ensure_ascii=False)
                context += "\nDeterministic inventory (config local, chưa chứng minh runtime):\n" + json.dumps(inventory_context, ensure_ascii=False)
                if rule.id == "ADS_CROSS_FLOW_BUGS":
                    context += "\nCác finding trước, tránh lặp lỗi:\n" + json.dumps(prior, ensure_ascii=False)
                finding, run_trace = evaluate(rule, tools, adapter, context, max_tool_calls-used)
                used += finding.tool_calls
                if adapter.name != "none" and finding.reason not in {"engine_error", "global_budget", "tool_budget", "invalid_json", "invalid_tool_count", "unverified_evidence"}:
                    cache.put(key, finding, run_trace)
            if trace:
                finding.trace = "trace/" + rule.id + ".json"
                write_json(output / finding.trace, run_trace)
        if finding.status == "UNKNOWN" and not finding.hint:
            finding.hint = (facts["manifest"].get("application_file") or facts["manifest"].get("file") or "AndroidManifest.xml") + ":1 (điểm bắt đầu kiểm tra)"
        findings.append(finding.to_dict())
        if rule_progress:
            rule_progress("complete", {"index": index, "total": len(selected), "rule_id": rule.id, "title": rule.title,
                                       "completed": index, "status": finding.status, "from_cache": finding.from_cache})
    summary = {status.lower():sum(f["status"] == status for f in findings) for status in ("PASS","FAIL","UNKNOWN","SKIPPED")}
    summary.update(total=len(findings), static=sum(f["mode"]=="static" for f in findings), agent=sum(f["mode"]=="agent" for f in findings), from_cache=sum(f["from_cache"] for f in findings), tool_calls=used, duration_seconds=time.monotonic()-started)
    report = {"schema_version":2,"package":facts["source"].get("package"),"version_name":facts["source"].get("version_name"),"apk_sha256":facts["source"].get("sha256"), "rulepack":{"name":pack.name,"version":pack.version,"fingerprint":pack.fingerprint},"engine":adapter.name,"docs_provided":{k:k in documents for k in ("ads_scripts","checklist")},"summary":summary,"findings":findings,"inventory":inventory,"observations":inventory_observations(inventory),"warnings":facts["warnings"]+([] if selected else ["no_rules"]),"output":str(output),"tool_versions":facts["tool_versions"]}
    if progress:
        progress("report")
    write_report(report, output, format)
    return report
