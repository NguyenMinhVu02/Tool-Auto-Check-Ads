from typing import Protocol
from .contracts import AgentResult
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

class ClaudeEngine:
    name = "claude"
    def available(self):
        return False
    def run_agent(self, prompt, tools, max_tool_calls, timeout=600):
        raise AuditError("Claude adapter chưa được triển khai; dùng MCP với client hoặc --engine none", 6)

class CodexEngine(ClaudeEngine):
    name = "codex"
    def run_agent(self, prompt, tools, max_tool_calls, timeout=600):
        raise AuditError("Codex adapter chưa được triển khai; dùng MCP với client hoặc --engine none", 6)

def get_engine(name):
    engine = {"none": NoneEngine, "claude": ClaudeEngine, "codex": CodexEngine}.get(name)
    if engine is None:
        raise AuditError(f"Engine không hỗ trợ: {name}", 6)
    result = engine()
    if not result.available():
        raise AuditError(f"Adapter {name} chưa nối ở bản khung. Dùng --engine none hoặc MCP trực tiếp.", 6)
    return result
