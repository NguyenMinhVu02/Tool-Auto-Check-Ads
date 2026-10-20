import json
import os
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

class CodexEngine:
    """Run one rule in an ephemeral, read-only Codex CLI session."""

    requires_claims = True
    model = "gpt-6.1-sol"
    reasoning_effort = "medium"
    name = f"codex:{model}:{reasoning_effort}"
    label = "Codex CLI (GPT-6.1 Sol · medium)"

    def available(self):
        return shutil.which("codex") is not None

    def run_agent(self, prompt, tools, max_tool_calls, timeout=600):
        if max_tool_calls <= 0:
            return AgentResult("", exhausted_budget=True)
        return self._run_structured(audit_instruction(prompt, max_tool_calls), tools,
                                    verdict_schema(), max_tool_calls, timeout)

    def map_document(self, instruction, tools, schema, timeout=90):
        return self._run_structured(instruction, tools, schema, 0, timeout)

    def _run_structured(self, instruction, tools, schema, max_tool_calls, timeout):
        with tempfile.TemporaryDirectory(prefix="apk-audit-codex-") as temp:
            schema_path = Path(temp) / "verdict.schema.json"
            result_path = Path(temp) / "verdict.json"
            stderr_path = Path(temp) / "codex.stderr"
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
            command = [
                "codex", "exec", "--ephemeral", "--skip-git-repo-check",
                "--sandbox", "read-only", "--model", self.model,
                "--config", f'model_reasoning_effort="{self.reasoning_effort}"',
                "--output-schema", str(schema_path), "--output-last-message", str(result_path),
                "--json", "--cd", str(tools.root), "-",
            ]
            if max_tool_calls == 0:
                command[2:2] = ['--config', 'features.shell_tool=false',
                                '--config', 'web_search="disabled"']
            with stderr_path.open("wb") as stderr:
                process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr)
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
            if exhausted:
                return AgentResult("", tool_calls=calls, events=events, exhausted_budget=True, usage=usage)
            if process.returncode:
                detail = stderr_path.read_text(encoding="utf-8", errors="replace")[-1000:].strip()
                raise agent_error("Codex CLI lỗi: " + (detail or f"exit {process.returncode}"), calls, usage)
            if not result_path.is_file():
                raise agent_error("Codex CLI không trả kết quả", calls, usage)
            return AgentResult(result_path.read_text(encoding="utf-8"), tool_calls=calls, events=events, usage=usage)

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
                    if kind == "turn.completed" and isinstance(event.get("usage"), dict):
                        events.append({"type": kind, "usage": event["usage"]})
                    if kind == 'item.completed' and item_type == 'command_execution':
                        item = event['item']
                        retain_source_read(events, item.get('command', ''), item.get('aggregated_output', ''))
                    if kind == 'item.completed' and item_type == 'mcp_tool_call':
                        item = event['item']
                        retain_source_read(events, item.get('tool', ''), json.dumps(item.get('result', {}), ensure_ascii=False))
                    if kind in {"turn.failed", "error"}:
                        events.append({"type": kind, "message": str(event.get("message", ""))[:500]})
                    if exhausted:
                        break
                if exhausted:
                    break
        finally:
            selector.close()
        return calls, events, exhausted

def detect_engines():
    engines = [{'id': 'codex', 'label': CodexEngine.label, 'model': CodexEngine.model,
                'reasoning_effort': CodexEngine.reasoning_effort, 'installed': shutil.which('codex') is not None},
               {'id': 'claude', 'label': ClaudeEngine.label, 'model': ClaudeEngine.model,
                'reasoning_effort': ClaudeEngine.reasoning_effort, 'installed': shutil.which('claude') is not None}]
    return {'engines': engines, 'default': next((item['id'] for item in engines if item['installed']), None)}


def get_engine(name):
    engine = {"none": NoneEngine, "claude": ClaudeEngine, "codex": CodexEngine}.get(name)
    if engine is None:
        raise AuditError(f"Engine không hỗ trợ: {name}", 6)
    result = engine()
    if not result.available():
        label = 'Claude CLI' if name == 'claude' else 'Codex CLI'
        raise AuditError(f"Không tìm thấy {label}. Cài CLI vào PATH và đăng nhập trước khi audit.", 6)
    return result
