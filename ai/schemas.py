from typing import Any


CASE_TYPES = {"positive", "negative", "boundary", "security", "dependency"}
PRIORITIES = {"P0", "P1", "P2", "P3"}
ASSERTION_TARGETS = {"status_code", "json", "header", "response_time"}
ASSERTION_OPERATORS = {"eq", "ne", "contains", "gt", "ge", "lt", "le"}

ALLOWED_CASE_FIELDS = {
    "source_interface",
    "case_id",
    "title",
    "case_type",
    "priority",
    "description",
    "method",
    "path",
    "headers",
    "params",
    "data",
    "json",
    "files",
    "assertions",
    "extracts",
    "depends_on",
    "enabled",
    "notes",
}

CASE_FIELD_ALIASES = {
    "query_params": "params",
    "query": "params",
    "body": "json",
    "body_params": "json",
    "request_body": "json",
}


class AiOutputError(ValueError):
    """Raised when model output does not match the case contract."""


def ensure_output_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AiOutputError("AI 输出必须是 JSON 对象")
    if value.get("schema_version") != "1.0":
        raise AiOutputError("AI 输出缺少 schema_version=1.0")
    if not isinstance(value.get("cases"), list):
        raise AiOutputError("AI 输出的 cases 必须是数组")
    return value
