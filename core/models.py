from dataclasses import dataclass, field
from typing import Any

from core.assertion_models import AssertionRule, ExtractRule


@dataclass
class ApiCase:
    case_id: str
    module: str
    feature: str
    story: str
    title: str
    method: str
    path: str
    headers: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    json_body: Any = field(default_factory=dict)
    files: dict[str, Any] = field(default_factory=dict)
    check: str = ""
    expected: Any = None
    extract: str = ""
    sql_check: str = ""
    notes: str = ""
    enabled: bool = True
    assertions: list[AssertionRule] = field(default_factory=list)
    extract_rules: list[ExtractRule] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    case_type: str = ""
    priority: str = ""


@dataclass
class ExecutionResult:
    case: ApiCase
    status_code: int
    response_text: str
    response_json: Any
    extracted: dict[str, Any] = field(default_factory=dict)
