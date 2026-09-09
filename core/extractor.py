from typing import Any

from jsonpath_ng import parse
import requests

from core.assertion_models import ExtractRule


def extract_variables(
    response: requests.Response,
    expression: str = "",
    rules: list[ExtractRule] | None = None,
) -> dict[str, Any]:
    """Extract named values from either new rules or legacy text syntax."""
    if rules:
        return _extract_rules(response, rules)
    if not expression or not expression.strip():
        return {}
    try:
        response_body = response.json()
    except ValueError as exc:
        raise AssertionError("响应不是 JSON，无法提取变量") from exc

    extracted: dict[str, Any] = {}
    for item in expression.replace(";", "\n").splitlines():
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError(f"变量提取格式错误: {item}，正确格式为 NAME=$.data.id")
        name, path = [part.strip() for part in item.split("=", 1)]
        matches = parse(path).find(response_body)
        if not matches:
            raise AssertionError(f"变量提取失败: {name} 未匹配到 {path}")
        extracted[name] = matches[0].value
    return extracted


def _extract_rules(response: requests.Response, rules: list[ExtractRule]) -> dict[str, Any]:
    try:
        response_body = response.json()
    except ValueError as exc:
        raise AssertionError("响应不是 JSON，无法提取变量") from exc
    extracted: dict[str, Any] = {}
    for rule in rules:
        if rule.source != "json":
            raise ValueError(f"暂不支持的变量来源: {rule.source}")
        matches = parse(rule.path).find(response_body)
        if not matches:
            raise AssertionError(f"变量提取失败: {rule.name} 未匹配到 {rule.path}")
        extracted[rule.name] = matches[0].value
    return extracted
