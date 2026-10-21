from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class Facts:
    schema_version: int = 2
    generated_at: str = ""
    tool_versions: dict = field(default_factory=dict)
    source: dict = field(default_factory=dict)
    workspace: dict = field(default_factory=dict)
    manifest: dict = field(default_factory=dict)
    assets: dict = field(default_factory=dict)
    strings: dict = field(default_factory=dict)
    code_index: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

@dataclass
class Rule:
    id: str
    title: str
    mode: str
    severity: str = "medium"
    area: str = "general"
    check: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    on_missing: str = "unknown"
    hint: str = ""
    question: str = ""
    verdict: dict = field(default_factory=dict)
    start_hints: list = field(default_factory=list)
    budget: dict = field(default_factory=lambda: {"max_tool_calls": 25})

@dataclass
class Finding:
    rule_id: str
    title: str
    mode: str
    status: str = "UNKNOWN"
    area: str = "general"
    severity: str = "medium"
    expected: Any = None
    actual: Any = None
    evidence: list = field(default_factory=list)
    claims: list = field(default_factory=list)
    verification: dict = field(default_factory=dict)
    reasoning: str = ""
    reason: str = ""
    hint: str = ""
    marketing_summary: str = ""
    screen_report: dict = field(default_factory=dict)
    resolved_by: str = ""
    tool_calls: int = 0
    exhausted_budget: bool = False
    from_cache: bool = False
    trace: str = ""

    @classmethod
    def for_rule(cls, rule, **kwargs):
        return cls(rule_id=rule.id, title=rule.title, mode=rule.mode,
                   area=rule.area, severity=rule.severity, hint=rule.hint, **kwargs)

    def to_dict(self):
        return asdict(self)

@dataclass
class RulePack:
    name: str
    version: str
    fingerprint: str
    rules: list[Rule] = field(default_factory=list)
    context: str = ""
    extract: dict = field(default_factory=dict)
    references: dict = field(default_factory=dict)

@dataclass
class AgentResult:
    text: str
    tool_calls: int = 0
    events: list = field(default_factory=list)
    exhausted_budget: bool = False
    usage: dict = field(default_factory=dict)
    session_id: str | None = None
