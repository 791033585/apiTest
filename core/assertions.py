import json
from typing import Any

import requests
from jsonpath_ng import parse

from core.assertion_models import AssertionRule


def assert_response(
    response: requests.Response,
    check: str = "",
    expected: Any = None,
    assertions: list[AssertionRule] | None = None,
) -> None:
    """Apply the assertions described by the Excel check/expected columns."""
    if assertions:
        for rule in assertions:
            _assert_one(response, rule.path or rule.target, rule.expected, rule.operator, rule.target)
        return
    if not check:
        if response.status_code >= 400:
            raise AssertionError(f"未配置断言，但响应状态码为 {response.status_code}")
        return

    if not expected and "=" in check and not check.strip().lower().startswith("status_code="):
        for expression in check.split("&"):
            path, value = expression.split("=", 1)
            _assert_one(response, path.strip(), _parse_expected(value.strip()), "eq")
        return

    stripped_check = check.strip()
    if stripped_check.startswith("[") or stripped_check.startswith("{"):
        try:
            specs = json.loads(stripped_check)
        except json.JSONDecodeError as exc:
            raise AssertionError(f"check 不是合法 JSON: {check}") from exc
        if isinstance(specs, dict):
            specs = [specs]
        for spec in specs:
            _assert_one(
                response,
                str(spec.get("path") or spec.get("target", "")),
                spec.get("expected"),
                str(spec.get("operator", "eq")),
                str(spec.get("target", "json")),
            )
        return

    operator = "eq"
    expected_value = expected
    if isinstance(expected, str) and expected.startswith("contains:"):
        operator = "contains"
        expected_value = expected.removeprefix("contains:")
    _assert_one(response, stripped_check, _parse_expected(expected_value), operator)


def _assert_one(
    response: requests.Response,
    path: str,
    expected: Any,
    operator: str,
    target: str = "json",
) -> None:
    actual = _read_value(response, path, target)
    if operator == "eq":
        passed = actual == expected
    elif operator == "ne":
        passed = actual != expected
    elif operator == "contains":
        passed = expected in actual
    elif operator == "gt":
        passed = actual > expected
    elif operator == "ge":
        passed = actual >= expected
    elif operator == "lt":
        passed = actual < expected
    elif operator == "le":
        passed = actual <= expected
    else:
        raise AssertionError(f"不支持的断言操作符: {operator}")
    if not passed:
        raise AssertionError(
            f"断言失败: path={path}, operator={operator}, expected={expected!r}, actual={actual!r}"
        )


def _read_value(response: requests.Response, path: str, target: str = "json") -> Any:
    if target == "status_code" or path.lower() == "status_code":
        return response.status_code
    if target == "header":
        if path not in response.headers:
            raise AssertionError(f"响应 Header 不存在: {path}")
        return response.headers[path]
    if target == "response_time":
        return response.elapsed.total_seconds()
    try:
        body = response.json()
    except ValueError as exc:
        raise AssertionError("响应不是 JSON，无法执行 JSONPath 断言") from exc
    matches = parse(path).find(body)
    if not matches:
        raise AssertionError(f"断言路径未匹配到响应字段: {path}")
    return matches[0].value


def _parse_expected(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
