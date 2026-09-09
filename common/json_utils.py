import json
from typing import Any


def parse_json_cell(value: Any, field_name: str) -> Any:
    """Parse a JSON value stored in an Excel cell.

    Empty request fields become an empty object so callers can pass them directly
    to requests. Invalid JSON fails early with the case field name included.
    """
    if value is None or str(value).strip() == "":
        return {}
    if isinstance(value, (dict, list, int, float, bool)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError as exc:
        raise ValueError(f"字段 {field_name} 不是合法 JSON: {value}") from exc


def parse_json_text(value: str) -> Any:
    """Parse JSON text and expose a small, reusable error message."""
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"不是合法 JSON: {value}") from exc

