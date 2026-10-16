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
from .engine_common import audit_instruction, verdict_schema
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
    def __init__(self, responses):
        self.responses = iter(responses)
    def available(self):
        return True
    def run_agent(self, prompt, tools, max_tool_calls, timeout=600):
        value = next(self.responses, "")
        return value if isinstance(value, AgentResult) else AgentResult(value)

class CodexEngine:
    """Run one rule in an ephemeral, read-only Codex CLI session."""

    name = "codex:gpt-6-luna"
    model = "gpt-6-luna"

    def available(self):
        return shutil.which("codex") is not None

    def run_agent(self, prompt, tools, max_tool_calls, timeout=600):
        if max_tool_calls <= 0:
            return AgentResult("", exhausted_budget=True)
        schema = verdict_schema()
        instruction = audit_instruction(prompt, max_tool_calls)
        with tempfile.TemporaryDirectory(prefix="apk-audit-codex-") as temp:
            schema_path = Path(temp) / "verdict.schema.json"
            result_path = Path(temp) / "verdict.json"
            stderr_path = Path(temp) / "codex.stderr"
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
            command = [
                "codex", "exec", "--ephemeral", "--skip-git-repo-check",
                "--sandbox", "read-only", "--model", self.model,
                "--output-schema", str(schema_path), "--output-last-message", str(result_path),
                "--json", "--cd", str(tools.root), "-",
            ]
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
            if exhausted:
                return AgentResult("", tool_calls=calls, events=events, exhausted_budget=True)
            if process.returncode:
                detail = stderr_path.read_text(encoding="utf-8", errors="replace")[-1000:].strip()
                raise AuditError("Codex Luna lỗi: " + (detail or f"exit {process.returncode}"), 6)
            if not result_path.is_file():
                raise AuditError("Codex Luna không trả kết quả", 6)
            return AgentResult(result_path.read_text(encoding="utf-8"), tool_calls=calls, events=events)

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
                    raise AuditError("Codex Luna quá thời gian chờ", 6)
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
                    kind = event.get("type", "")
                    item_type = event.get("item", {}).get("type", "") if isinstance(event.get("item"), dict) else ""
                    if kind == "item.started" and item_type in {"command_execution", "mcp_tool_call", "web_search"}:
                        calls += 1
                        if calls > max_tool_calls:
                            exhausted = True
                            process.kill()
                            break
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
    engines = [{'id': 'codex', 'label': 'Codex CLI (GPT-6 Luna)', 'installed': shutil.which('codex') is not None},
               {'id': 'claude', 'label': 'Claude CLI (model mặc định)', 'installed': shutil.which('claude') is not None}]
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
