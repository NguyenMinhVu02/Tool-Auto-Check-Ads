import json
from pathlib import Path
import time
from .agent import evaluate, _verify_evidence
from .cache_identity import engine_identity
from .scoped_cache import ScopedIndex, dependency_paths, hash_dependencies, scoped_key, tree_digest
from .engine_common import SLICE_MARK
from .slicer import SLICE_VERSION, build_slices
from .context_scope import SCOPE_VERSION, compact_prior, not_applicable_by_document, scope_documents, scope_inventory
from .engine_common import ACTIVITY, policy_identity
from .execution import CROSS_FLOW_RULE, RuleOutcome, execute_rules, MAX_WORKERS, valid_workers
from .source_index import SourceIndex
from .utils import digest_json
import threading
from .config import cache_path
from .contracts import Finding
from .documents import load_document
from .document_structure import ai_mapper
from .engines import get_engine
from .errors import AuditError
from .facts import build_facts
from .inventory import build_inventory, inventory_observations
from .agent import checklist_placeholder
from .preflight import DocumentMismatch, check_documents
from .rules.code_facts import app_roots, code_profile
from .dev_view import build_dev_view
from .passed_history import PassedHistory
from .flow_map import build_flow_map
from .marketing import build_marketing_summary
from .fetch import fetch
from .playstore import resolve
from .report import write_report
from .rules.engine import evaluate_static
from .rules.loader import load_pack
from .tools import WorkspaceTools
from .unpack import unpack
from .utils import write_json, source_files
from .verdict_cache import VerdictCache, verdict_record, valid_record

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

def _cached_finding(cached, rule, tools, strict):
    """Recheck disk data against current sources; never trust persisted verified flags."""
    if not valid_record(cached):
        return None
    try:
        finding = Finding(**cached["finding"])
    except (TypeError, ValueError):
        return None
    if finding.rule_id != rule.id or not isinstance(finding.status,str) or finding.status not in {"PASS","FAIL","UNKNOWN","SKIPPED"}:
        return None
    if type(finding.tool_calls) is not int or finding.tool_calls < 0:
        return None
    if (not isinstance(finding.evidence,list) or not isinstance(finding.claims,list)
            or not isinstance(finding.verification,dict)):
        return None
    checked = _verify_evidence({"evidence": finding.evidence}, tools)
    if strict and finding.status == 'UNKNOWN':
        from .claim_verifier import verify_claims
        if (not checked or not all(item['verified'] for item in checked)
                or not verify_claims({'status': 'UNKNOWN', 'claims': finding.claims}, checked).get('valid')):
            return None
    if finding.status in {"PASS", "FAIL"}:
        if not checked or len(checked) != len(finding.evidence) or not all(x["verified"] for x in checked):
            return None
        if strict:
            from .claim_verifier import verify_claims
            verdict = verify_claims({"status": finding.status, "claims": finding.claims}, checked)
            if not verdict.get("valid"):
                return None
            # FAIL is accepted from disk only if the live reviewer completed before persistence.
            if finding.status == "FAIL" and finding.verification.get("review") != "accepted":
                return None
            if finding.verification.get("review") == "accepted":
                attempts = cached["trace"].get("attempts",[])
                if not isinstance(attempts,list):
                    return None
                reviewed = next((a for a in reversed(attempts) if isinstance(a,dict) and a.get("review") is True),None)
                if not reviewed or reviewed.get("error"):
                    return None
                try:
                    payload = json.loads(reviewed["text"])
                    if (not isinstance(payload,dict) or payload.get("status") != finding.status
                            or payload.get("rule_id") != rule.id or payload.get("claims") != finding.claims
                            or str(payload.get("reasoning","")) != finding.reasoning
                            or _verify_evidence(payload,tools) != checked):
                        return None
                except (ValueError,KeyError,TypeError):
                    return None
    finding.evidence = checked
    finding.from_cache = True
    return finding


SLICED_BUNDLE_CHARS = 5000  # the slice already carries the relevant code; keep only a small heuristic bundle
BUNDLE_CHARS = 12000  # heuristic code hints; the AI reads files itself, so a smaller bundle saves tokens on every turn


def normalize_usage(usage):
    """Common token names across Codex/Claude CLI usage objects."""
    def pick(*names):
        return sum(usage.get(name, 0) for name in names if type(usage.get(name)) in (int, float))
    return {"input": pick("input_tokens"),
            "cache_read": pick("cache_read_input_tokens", "cached_input_tokens"),
            "cache_write": pick("cache_creation_input_tokens", "cache_write_input_tokens"),
            "output": pick("output_tokens")}


def run(target, *, rules=None, out=None, engine="codex", only=None, cache_dir=None,
        refresh=False, refresh_rule=None, max_tool_calls=400, trace=False,
        format="both", no_cache=False, ads_scripts=None, checklist=None, provider=None,
        progress=None, rule_progress=None, workers=1, resume=False, ads_sheet=None, checklist_sheet=None,
        cross_flow=False, scoped_cache=True, recheck_all=False, full_scope=False, confirm_mismatch=False):
    started = time.monotonic()
    if type(max_tool_calls) is not int or max_tool_calls < 0:
        raise AuditError("max_tool_calls phải >= 0")
    if not valid_workers(workers):
        raise AuditError(f"workers phải từ 1 đến {MAX_WORKERS}")
    if format not in {"md", "json", "both"}:
        raise AuditError("format không hợp lệ")
    phases = {}
    phase_name, phase_started = "setup", started
    def phase(name, public=True):
        nonlocal phase_name, phase_started
        now = time.monotonic()
        phases[phase_name] = now-phase_started
        phase_name, phase_started = name, now
        if progress and public:
            progress(name)
    pack = load_pack(rules)
    selected = [r for r in pack.rules if only is None or only in {r.id, r.area}]
    if not full_scope and only is None:
        # Core scope: initialisation, Remote Config/consent/fallback, IDs and the four first screens.
        selected = [r for r in selected if r.params.get("tier") != "full"]
    if not cross_flow and only is None:
        # Cross-flow re-reads every other rule's result; opt-in because it costs a full extra session.
        selected = [r for r in selected if r.id != CROSS_FLOW_RULE]
    if only is not None and not selected:
        raise AuditError(f"Không có rule hoặc area: {only}", 5)
    if refresh_rule and refresh_rule not in {r.id for r in pack.rules}:
        raise AuditError(f"Không có rule: {refresh_rule}", 5)
    adapter = get_engine(engine) if isinstance(engine, str) else engine
    identity, reusable = engine_identity(adapter)
    policy = policy_identity()
    strict = bool(getattr(adapter, "requires_claims", False))
    phase("documents")
    document_attempts = []
    mapper = ai_mapper(adapter, document_attempts) if max_tool_calls > 0 else None
    documents = {kind: load_document(path, kind, mapper=mapper, sheet=sheet)
                 for kind, path, sheet in (("ads_scripts", ads_scripts, ads_sheet), ("checklist", checklist, checklist_sheet))
                 if path is not None}
    phase("unpack")
    workspace, source = prepare(target, cache_dir, no_cache, provider)
    phase("facts")
    workspace_files = list(source_files(workspace))
    facts = build_facts(workspace, source, pack.extract, files=workspace_files).to_dict()
    output = Path(out or Path("out") / facts["workspace"]["content_sha256"][:12]).resolve()
    if output == workspace or output.is_relative_to(workspace):
        raise AuditError("Thư mục out phải nằm ngoài workspace đầu vào")
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "facts.json", facts)
    inventory = build_inventory(workspace, facts, documents, files=workspace_files)
    preflight = check_documents(documents, facts, inventory)
    if preflight["level"] == "block" and adapter.name != "none" and not confirm_mismatch:
        raise DocumentMismatch(preflight)   # before any AI quota is spent
    write_json(output / "inventory.json", inventory)
    tools = WorkspaceTools(workspace, facts, files=workspace_files)
    write_json(output / "xref_index.json", tools.xref_index)
    phase("index", public=False)
    source_index = SourceIndex.build(workspace, facts["workspace"]["content_sha256"], cache_path(cache_dir))
    cache = VerdictCache(cache_path(cache_dir))
    scoped_index = ScopedIndex(cache_path(cache_dir))
    passed_history = PassedHistory(cache_path(cache_dir))
    package_name = facts["source"].get("package") or ""
    apk_sha = facts["source"].get("sha256") or facts["workspace"]["content_sha256"]
    workspace_tree = tree_digest(workspace, workspace_files) if scoped_cache else None
    fingerprint = digest_json({"workspace":facts["workspace"]["content_sha256"], "apk":facts["source"].get("sha256"),
                               "rules":pack.fingerprint, "selected":[r.id for r in selected],
                               "documents":documents, "engine":identity, "policy":policy,
                               "index_policy":source_index.policy})
    checkpoint_path = output / "checkpoint.json"
    completed = {}
    if resume and reusable and not refresh and checkpoint_path.is_file():
        try:
            saved = json.loads(checkpoint_path.read_text())
            if saved.get("fingerprint") == fingerprint and isinstance(saved.get("completed"),dict):
                completed = saved["completed"]
        except (OSError, ValueError, AttributeError):
            pass
    checkpoint = {"schema_version":1, "fingerprint":fingerprint, "completed":dict(completed)}
    checkpoint_lock = threading.Lock()
    inventory_context = {key: inventory[key] for key in (
        "expected_count", "local_count", "missing_local", "extra_local", "mismatched_ids",
        "config_references", "code_references", "package_match", "app_id_match",
        "optional_placements", "disabled_placements", "uncertain_placements", "integration_policy", "document_warnings")}
    flow_map_json = json.dumps(build_flow_map(workspace, facts, workspace_files), ensure_ascii=False)
    config_names = set((facts.get("assets", {}).get("json", {}).get("ad_config.json") or {}))
    doc_names = {row.get("name") for row in (documents.get("ads_scripts") or {}).get("placements", []) if isinstance(row, dict)}
    slices = build_slices(workspace, facts, workspace_files, sorted(n for n in config_names | doc_names if n))
    profile_data = code_profile(workspace, app_roots(facts))
    profile_json = json.dumps({k: v for k, v in profile_data.items() if k != 'gap_samples'}, ensure_ascii=False)

    def context_for(rule):
        # Rule-scoped slices: smaller prompts on every tool turn, less unrelated noise.
        return (pack.context + "\nDocuments (lọc theo phạm vi rule; scope ghi số dòng giữ lại/tổng):\n"
                + json.dumps(scope_documents(documents, rule.area), ensure_ascii=False)
                + "\nDeterministic inventory (config local, chưa chứng minh runtime; lọc theo phạm vi rule):\n"
                + json.dumps(scope_inventory(inventory_context, rule.area), ensure_ascii=False)
                + "\nflow_map (điểm bắt đầu đọc code):\n" + flow_map_json
                + "\ncode_profile (độ tin cậy của việc 'không tìm thấy' trong mã giải mã):\n" + profile_json)
    noncacheable = {"engine_error", "global_budget", "tool_budget", "invalid_json", "invalid_tool_count",
                    "unverified_evidence", "unverified_claims", "review_error", "review_budget", "review_incomplete", "invalid_review", "repair_error", "repair_invalid_result", "investigation_invalid_result", "wrong_rule_id", "invalid_status"}

    def execute(rule, allocation, prior):
        if rule_progress:
            ACTIVITY.set(lambda **fields: rule_progress("activity", {"rule_id": rule.id, "title": rule.title, **fields}))
        if prior is not None:
            prior = compact_prior(prior)
        if rule.mode == "static":
            try:
                return RuleOutcome(evaluate_static(rule, facts, documents, workspace=workspace))
            except Exception as exc:
                return RuleOutcome(Finding.for_rule(rule, reason="rule_error", reasoning=str(exc), resolved_by="static"))
        skipped = not_applicable_by_document(documents, rule.area)
        if skipped:
            return RuleOutcome(Finding.for_rule(
                rule, status="SKIPPED", reason="not_applicable_by_document", resolved_by="document",
                screen_report=checklist_placeholder(rule.params.get("checklist") or [], "na") if rule.params.get("checklist") else {},
                reasoning=f"Kết luận: không áp dụng. {skipped}.",
                marketing_summary="Tài liệu ADS SCRIPTS xác định phần này không dùng nên không cần kiểm tra."))
        earlier = (passed_history.lookup(package_name, rule.id, apk_sha)
                   if rule.params.get("skip_after_pass") and not recheck_all and package_name and adapter.name != "none" else None)
        if earlier:
            return RuleOutcome(Finding.for_rule(
                rule, status="SKIPPED", reason="passed_previously", resolved_by="history",
                reasoning=(f"Kết luận: bỏ qua. Rule này đã Đạt ở bản trước (version {earlier.get('version_name') or '?'}, "
                           f"{earlier.get('at') or '?'}); tool bỏ qua theo cấu hình để tiết kiệm token. Chọn kiểm lại mọi rule để chạy lại."),
                marketing_summary="Phần này đã đạt ở bản trước nên không kiểm lại; chọn 'kiểm lại mọi rule' nếu cần."))
        sliced = slices.get(rule.area) if rule.mode == "agent" else ""
        bundle = source_index.bundle(rule, facts, inventory,
                                     max_chars=rule.budget.get('context_chars', SLICED_BUNDLE_CHARS if sliced else BUNDLE_CHARS))
        reference = {'source': pack.references.get('source', {}), 'rule': pack.references.get('rules', {}).get(rule.id, {})}
        rule_policy = {**policy, "bundle_policy":bundle.get("policy"), 'base_reference': digest_json(reference),
                       'context_scope': SCOPE_VERSION, 'slice': SLICE_VERSION,
                       'absence_gate': profile_data['obfuscation'] == 'thấp' and not profile_data['decompile_gap_files']}
        key = cache.key(facts, pack, rule, adapter.name, documents, dependencies=prior, policy=rule_policy, identity=identity)
        finding = None
        run_trace = {}
        bypass = refresh or refresh_rule == rule.id or adapter.name == "none" or not reusable
        from_checkpoint = False
        from_scoped = False
        scoped_ok = scoped_cache and reusable and adapter.name != "none" and prior is None and rule.id != CROSS_FLOW_RULE
        skey = scoped_key(pack, rule, adapter.name, identity, rule_policy, scope_documents(documents, rule.area),
                          scope_inventory(inventory_context, rule.area)) if scoped_ok else None
        if not bypass:
            saved_rule = completed.get(rule.id)
            if isinstance(saved_rule,dict) and saved_rule.get("cache_key") == key:
                finding = _cached_finding(saved_rule,rule,tools,strict)
                if finding:
                    run_trace = saved_rule.get("trace",{})
                    from_checkpoint = True
            if finding is None:
                cached = cache.get(key)
                finding = _cached_finding(cached,rule,tools,strict)
                if finding:
                    run_trace = cached.get("trace",{})
            if finding is None and skey and not (refresh or refresh_rule == rule.id):
                main_key = scoped_index.find(skey, workspace, workspace_tree)
                cached = cache.get(main_key) if main_key else None
                finding = _cached_finding(cached,rule,tools,strict) if cached and cached["finding"].get("status") in {"PASS","FAIL"} else None
                if finding:
                    run_trace = cached.get("trace",{})
                    from_scoped = True
                    cache.put(key,finding,run_trace)
        if finding is None:
            context = context_for(rule) + (SLICE_MARK + sliced + SLICE_MARK if sliced else "") + "\nevidence_bundle (gợi ý heuristic, không chứng minh thiếu hành vi):\n" + json.dumps(bundle, ensure_ascii=False)
            if reference['rule']:
                context += '\nbase_reference (mã mẫu để hiểu logic, KHÔNG phải evidence của APK; integration_policy và rule hiện tại có ưu tiên):\n' + json.dumps(reference, ensure_ascii=False)
            if prior is not None:
                context += "\nCác finding đã kiểm trước, kèm claim/evidence; rà mâu thuẫn, tránh lặp lỗi:\n" + json.dumps(prior, ensure_ascii=False)
            finding, run_trace = evaluate(rule,tools,adapter,context,allocation,profile=profile_data)
            if rule.params.get("checklist") and not finding.screen_report:
                finding.screen_report = checklist_placeholder(rule.params["checklist"])
            if reusable and adapter.name != "none" and finding.reason not in noncacheable:
                cache.put(key,finding,run_trace)
                if skey and finding.status in {"PASS","FAIL"}:
                    paths = dependency_paths(finding, run_trace)
                    hashes = hash_dependencies(workspace, paths) if paths else None
                    if hashes:
                        scoped_index.put(skey, key, hashes, workspace_tree)
        run_trace = dict(run_trace) if isinstance(run_trace,dict) else {}
        run_trace["from_scoped_cache"] = from_scoped
        run_trace["from_checkpoint"] = from_checkpoint
        if finding.status == "UNKNOWN" and not finding.hint:
            finding.hint = (facts["manifest"].get("application_file") or facts["manifest"].get("file") or "AndroidManifest.xml") + ":1 (điểm bắt đầu kiểm tra)"
        if trace:
            finding.trace = "trace/" + rule.id + ".json"
            write_json(output / finding.trace,run_trace)
        if reusable and adapter.name != "none" and finding.reason not in noncacheable:
            with checkpoint_lock:
                checkpoint["completed"][rule.id] = verdict_record(finding,run_trace,cache_key=key)
                write_json(checkpoint_path,checkpoint)
        return RuleOutcome(finding,run_trace)

    phase("rules")
    outcomes, used = execute_rules(selected,execute,max_tool_calls=max_tool_calls,workers=workers,progress=rule_progress)
    findings = [item.finding.to_dict() for item in outcomes]
    if not checkpoint_path.exists():
        write_json(checkpoint_path,checkpoint)
    metrics_rules = []
    for rule,outcome in zip(selected,outcomes):
        attempts = [] if outcome.finding.from_cache else outcome.trace.get("attempts",[])
        usage = {}
        for attempt in attempts:
            for key,value in attempt.get("usage",{}).items():
                if type(value) in (int,float) and value >= 0:
                    usage[key] = usage.get(key,0)+value
        metrics_rules.append({"rule_id":rule.id,"duration_seconds":outcome.duration_seconds,
            "from_cache":outcome.finding.from_cache,"from_checkpoint":outcome.trace.get("from_checkpoint",False),
            "from_scoped_cache":outcome.trace.get("from_scoped_cache",False),
            "tool_calls":0 if outcome.finding.from_cache else outcome.finding.tool_calls,
            "allocated_tool_calls":outcome.allocated_tool_calls, "attempts":len(attempts),
            "usage_observed":usage, "usage":normalize_usage(usage),
            "resumed_attempts":sum(bool(a.get("resumed")) for a in attempts),
            "repair_attempts":sum(bool(a.get("repair")) for a in attempts),
            "review_attempts":sum(bool(a.get("review")) for a in attempts),
            "investigation_attempts":sum(bool(a.get("investigation")) for a in attempts),
            "base_reference_snippets":len(pack.references.get('rules', {}).get(rule.id, {}).get('snippets', [])),
            "prompt_bytes_sent":sum(a.get("prompt_bytes",0) for a in attempts)})
    usage_totals = {key:sum(item["usage"][key] for item in metrics_rules) for key in ("input","cache_read","cache_write","output")}
    summary = {status.lower():sum(f["status"] == status for f in findings) for status in ("PASS","FAIL","UNKNOWN","SKIPPED")}
    summary.update(total=len(findings),static=sum(f["mode"]=="static" for f in findings),agent=sum(f["mode"]=="agent" for f in findings),
                   from_cache=sum(f["from_cache"] for f in findings),tool_calls=used,duration_seconds=time.monotonic()-started)
    metrics = {"phases":phases,"rules":metrics_rules,"workers":workers,
               "documents": {"parsed": [dict(kind=kind, **document.get('parsing', {}),
                   sheet=document.get('sheet'), rows=len(document.get('placements', document.get('checklist_rows', []))))
                   for kind, document in documents.items()], "ai_attempts": document_attempts},
               "base_reference_source":pack.references.get('source', {}),
               "index":{"cache_hit":source_index.cache_hit,**source_index.stats},
               "engine_identity":identity,"verdict_cache_enabled":reusable and adapter.name != "none","policy":policy,
               "input_fingerprint":fingerprint,"usage":"Không ước lượng token/chi phí khi CLI không cung cấp",
               "usage_totals":usage_totals}
    warnings = facts["warnings"]+([] if selected else ["no_rules"])
    if preflight["level"] == "block":
        warnings.append("documents_may_not_match_app: " + "; ".join(item["message"] for item in preflight["reasons"]) + " (đã được xác nhận tiếp tục)")
    quota = next((f["reasoning"] for f in findings if "usage limit" in str(f.get("reasoning"))), None)
    if quota:
        blocked = sum("usage limit" in str(f.get("reasoning")) for f in findings)
        warnings.append(f"engine_quota_exhausted: {blocked} rule không kiểm được vì AI hết hạn mức; {quota.strip()[-140:]}")
    if not reusable:
        warnings.append("verdict_cache_disabled: model hoặc CLI version chưa xác định")
    if used > max_tool_calls:
        warnings.append(f"observed_tool_budget_overrun: {used}/{max_tool_calls}; CLI báo tool sau khi bắt đầu, đã dừng và giữ UNKNOWN")
    metrics["tool_budget"] = {"configured":max_tool_calls,"observed":used,
        "overrun":max(0,used-max_tool_calls),"enforcement":"reservation plus observed CLI stop; not a pre-execution tool gateway"}
    marketing = build_marketing_summary(documents,facts,inventory,findings)
    report = {"schema_version":2,"package":facts["source"].get("package"),"version_name":facts["source"].get("version_name"),
        "apk_sha256":facts["source"].get("sha256"),"rulepack":{"name":pack.name,"version":pack.version,"fingerprint":pack.fingerprint},
        "engine":adapter.name,"docs_provided":{k:k in documents for k in ("ads_scripts","checklist")},"summary":summary,
        "findings":findings,"inventory":inventory,"observations":inventory_observations(inventory),"metrics":metrics,
        "marketing":marketing,"dev_view":build_dev_view(findings,marketing),
        "code_profile":code_profile(workspace,app_roots(facts)),"preflight":preflight,
        "warnings":warnings,"output":str(output),"tool_versions":facts["tool_versions"]}
    phase("report")
    passed_history.record(report, apk_sha)
    write_report(report,output,format)
    phases["report"] = time.monotonic()-phase_started
    summary["duration_seconds"] = time.monotonic()-started
    write_json(output/"metrics.json",metrics)
    write_report(report,output,format)
    return report
