import json
import os
import re
import selectors
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Protocol
from .contracts import AgentResult
from .claude_engine import ClaudeEngine
from .engine_common import agent_error, audit_instruction, report_activity, retain_source_read, verdict_schema
from .errors import AuditError

class Engine(Protocol):
    name: str
    def available(self) -> bool: ...
    def run_agent(self, prompt: str, tools, max_tool_calls: int, timeout: int = 600) -> AgentResult: ...

class NoneEngine:
    name = "none"
    def available(self):
        return True
    def run_agent(self, prompt, tools, max_tool_calls, timeout=600):
        return AgentResult("")

class ReplayEngine:
    """Offline adapter for recorded outputs; never pretends to execute live AI."""
    name = "replay"
    requires_claims = False
    def __init__(self, responses):
        self.responses = iter(responses)
    def available(self):
        return True
    def run_agent(self, prompt, tools, max_tool_calls, timeout=600):
        value = next(self.responses, "")
        return value if isinstance(value, AgentResult) else AgentResult(value)

# Tiers tried in order: the newest "terra" (efficient, cheaper) first, then the newest "sol".
CODEX_FAMILIES = ("terra", "sol")
_codex_models_cache = {"at": 0.0, "models": None}


def codex_models(ttl=300):
    """Model slugs this Codex CLI/account offers (``codex debug models``), cached briefly."""
    now = time.monotonic()
    if _codex_models_cache["models"] is not None and now - _codex_models_cache["at"] < ttl:
        return _codex_models_cache["models"]
    models = []
    binary = shutil.which("codex")
    if binary:
        try:
            done = subprocess.run([binary, "debug", "models"], capture_output=True, text=True, timeout=20,
                                  stdin=subprocess.DEVNULL)
            data = json.loads(done.stdout) if done.returncode == 0 else []
            items = data.get("models", []) if isinstance(data, dict) else data
            models = [item["slug"] for item in items if isinstance(item, dict) and item.get("slug")
                      and item.get("visibility", "list") == "list"]
        except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError):
            models = []
    _codex_models_cache.update(at=now, models=models)
    return models


def pick_codex_model(models):
    """Newest model of the first available tier in CODEX_FAMILIES, else None (Codex default)."""
    for family in CODEX_FAMILIES:
        def version(slug, family=family):
            match = re.fullmatch(rf"gpt-(\d+(?:\.\d+)*)-{family}", slug)
            return tuple(int(part) for part in match.group(1).split(".")) if match else None
        ranked = sorted((version(slug), slug) for slug in models if version(slug))
        if ranked:
            return ranked[-1][1]
    return None


class CodexEngine:
    """Run one rule in an ephemeral, read-only Codex CLI session."""

    requires_claims = True
    reasoning_effort = "low"
    # Audits must not inherit the user's personal skills, plugins, hooks or AGENTS.md:
    # they cost tool calls/quota and can steer verdicts away from the rule pack.
    isolation = [
        "--ignore-rules",
        "--config", "features.plugins=false", "--config", "features.apps=false",
        "--config", "features.hooks=false", "--config", "features.multi_agent=false",
        "--config", "skills.include_instructions=false", "--config", "include_apps_instructions=false",
        "--config", "project_doc_max_bytes=0",
    ]

    def __init__(self, model=None):
        # The model is chosen at run time from what the installed CLI supports, so a retired
        # model never breaks audits. It is part of ``name`` and therefore of every cache key.
        pinned = os.environ.get("APK_AUDIT_CODEX_MODEL")  # optional manual override
        self.model = model if model is not None else pinned or pick_codex_model(codex_models())
        self.name = f"codex:{self.model or 'cli-default'}:{self.reasoning_effort}"
        self.label = f"Codex CLI ({self.model or 'model mặc định của CLI'} · low)"

    def available(self):
        return shutil.which("codex") is not None

    # Follow-up repair/investigation turns continue the rule's own Codex session instead of
    # resending the whole prompt; the transcript is deleted when the rule finishes.
    supports_resume = True

    def run_agent(self, prompt, tools, max_tool_calls, timeout=600, resume=None):
        if max_tool_calls <= 0:
            return AgentResult("", exhausted_budget=True)
        return self._run_structured(audit_instruction(prompt, max_tool_calls), tools,
                                    verdict_schema(), max_tool_calls, timeout, session=resume, persist=True)

    def map_document(self, instruction, tools, schema, timeout=90):
        return self._run_structured(instruction, tools, schema, 0, timeout)

    @staticmethod
    def close_session(session_id):
        root = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "sessions"
        for path in root.glob(f"**/rollout-*-{session_id}.jsonl"):
            path.unlink(missing_ok=True)

    def _run_structured(self, instruction, tools, schema, max_tool_calls, timeout, session=None, persist=False):
        with tempfile.TemporaryDirectory(prefix="apk-audit-codex-") as temp:
            schema_path = Path(temp) / "verdict.schema.json"
            result_path = Path(temp) / "verdict.json"
            stderr_path = Path(temp) / "codex.stderr"
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
            effort = ["--config", f'model_reasoning_effort="{self.reasoning_effort}"']
            model = ["--model", self.model] if self.model else []
            outputs = ["--output-schema", str(schema_path), "--output-last-message", str(result_path), "--json"]
            if session:
                # resume has no --sandbox/--cd: force read-only through config and run from the workspace.
                command = [shutil.which("codex") or "codex", "exec", "resume", session, "--skip-git-repo-check", *model,
                           *effort, "--config", 'sandbox_mode="read-only"', *outputs, *self.isolation, "-"]
            else:
                command = [shutil.which("codex") or "codex", "exec", *([] if persist else ["--ephemeral"]), "--skip-git-repo-check",
                           "--sandbox", "read-only", *model, *effort, *outputs,
                           "--cd", str(tools.root), *self.isolation, "-"]
            if max_tool_calls == 0:
                command[2:2] = ['--config', 'features.shell_tool=false',
                                '--config', 'web_search="disabled"']
            with stderr_path.open("wb") as stderr:
                process = subprocess.Popen(command, cwd=tools.root, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr)
                try:
                    process.stdin.write(instruction.encode("utf-8"))
                    process.stdin.close()
                    calls, events, exhausted = self._collect(process, max_tool_calls, timeout)
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.wait()
                    process.stdout.close()
            usage = next((event['usage'] for event in reversed(events) if isinstance(event.get('usage'), dict)), {})
            thread = session or next((e.get("thread_id") for e in events if e.get("type") == "thread.started"), None)
            events = [e for e in events if e.get("type") != "thread.started"]
            if exhausted:
                return AgentResult("", tool_calls=calls, events=events, exhausted_budget=True, usage=usage,
                                   session_id=thread if persist else None)
            if process.returncode:
                # Quota/auth failures arrive as JSON error events on stdout, not stderr.
                detail = next((e["message"] for e in reversed(events) if e.get("type") in {"error", "turn.failed"} and e.get("message")), "")
                detail = detail or stderr_path.read_text(encoding="utf-8", errors="replace")[-1000:].strip()
                raise agent_error("Codex CLI lỗi: " + (detail or f"exit {process.returncode}"), calls, usage)
            if not result_path.is_file():
                raise agent_error("Codex CLI không trả kết quả", calls, usage)
            return AgentResult(result_path.read_text(encoding="utf-8"), tool_calls=calls, events=events, usage=usage,
                               session_id=thread if persist else None)

    @staticmethod
    def _collect(process, max_tool_calls, timeout):
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + timeout
        buffer = b""
        calls = 0
        events = []
        exhausted = False
        try:
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise agent_error("Codex CLI quá thời gian chờ", calls)
                ready = selector.select(min(remaining, 1))
                if not ready:
                    continue
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    selector.unregister(process.stdout)
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    try:
                        event = json.loads(line)
                    except (ValueError, UnicodeDecodeError):
                        continue
                    if not isinstance(event, dict):
                        continue
                    kind = event.get("type", "")
                    item_type = event.get("item", {}).get("type", "") if isinstance(event.get("item"), dict) else ""
                    if kind == "item.started" and item_type in {"command_execution", "mcp_tool_call", "web_search"}:
                        calls += 1
                        item = event["item"]
                        report_activity(tool_calls=calls, command=str(item.get("command") or item.get("tool") or item.get("query") or item_type)[:300])
                        if calls > max_tool_calls:
                            exhausted = True
                            process.kill()
                            break
                    if kind == "thread.started" and event.get("thread_id"):
                        events.append({"type": kind, "thread_id": str(event["thread_id"])})
                    if kind == "turn.completed" and isinstance(event.get("usage"), dict):
                        events.append({"type": kind, "usage": event["usage"]})
                    if kind == 'item.completed' and item_type == 'command_execution':
                        item = event['item']
                        retain_source_read(events, item.get('command', ''), item.get('aggregated_output', ''))
                    if kind == 'item.completed' and item_type == 'mcp_tool_call':
                        item = event['item']
                        retain_source_read(events, item.get('tool', ''), json.dumps(item.get('result', {}), ensure_ascii=False))
                    if kind in {"turn.failed", "error"}:
                        error = event.get("error") if isinstance(event.get("error"), dict) else {}
                        events.append({"type": kind, "message": str(event.get("message") or error.get("message") or "")[:500]})
                    if exhausted:
                        break
                if exhausted:
                    break
        finally:
            selector.close()
        return calls, events, exhausted

def detect_engines():
    """Only the AI CLIs installed on this machine; one CLI means no choice to make."""
    engines = []
    if shutil.which('claude'):
        claude = ClaudeEngine()
        engines.append({'id': 'claude', 'label': claude.label, 'model': claude.model,
                        'reasoning_effort': claude.reasoning_effort, 'installed': True})
    if shutil.which('codex'):
        codex = CodexEngine()
        engines.append({'id': 'codex', 'label': codex.label, 'model': codex.model,
                        'reasoning_effort': codex.reasoning_effort, 'installed': True})
    return {'engines': engines, 'default': engines[0]['id'] if engines else None}


def get_engine(name):
    engine = {"none": NoneEngine, "claude": ClaudeEngine, "codex": CodexEngine}.get(name)
    if engine is None:
        raise AuditError(f"Engine không hỗ trợ: {name}", 6)
    result = engine()
    if not result.available():
        label = 'Claude CLI' if name == 'claude' else 'Codex CLI'
        raise AuditError(f"Không tìm thấy {label}. Cài CLI vào PATH và đăng nhập trước khi audit.", 6)
    return result
