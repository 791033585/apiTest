import re
from copy import deepcopy
from collections import defaultdict
from typing import Any

from ai.schemas import (
    ALLOWED_CASE_FIELDS,
    ASSERTION_OPERATORS,
    ASSERTION_TARGETS,
    CASE_FIELD_ALIASES,
    CASE_TYPES,
    PRIORITIES,
    AiOutputError,
    ensure_output_object,
)
from core.openapi_models import ImportedOpenApi, OpenApiInterface


class AiOutputValidator:
    def __init__(
        self,
        imported: ImportedOpenApi,
        target_interface: OpenApiInterface | None = None,
        allowed_dependency_ids: set[str] | None = None,
        max_cases: int | None = None,
    ):
        self.imported = imported
        self.target_interface = target_interface
        self.allowed_dependency_ids = allowed_dependency_ids or set()
        self.max_cases = max_cases
        self.interfaces = {(item.method.upper(), item.path): item for item in imported.interfaces}

    def validate(self, output: dict[str, Any]) -> dict[str, Any]:
        output = self._normalize_case_aliases(ensure_output_object(output))
        errors: list[str] = []
        case_ids: set[str] = set()
        if self.max_cases is not None and len(output["cases"]) > self.max_cases:
            errors.append(f"当前批次最多允许 {self.max_cases} 条用例，实际为 {len(output['cases'])} 条")
        for index, case in enumerate(output["cases"], start=1):
            try:
                self._validate_case(case, index, case_ids)
            except AiOutputError as exc:
                errors.append(f"cases[{index - 1}]: {exc}")
        errors.extend(self._dependency_errors(output["cases"], case_ids))
        if errors:
            raise AiOutputError("；".join(errors))
        return output

    @staticmethod
    def _normalize_case_aliases(output: dict[str, Any]) -> dict[str, Any]:
        """兼容少量模型常用字段名，内部始终使用框架标准字段。"""
        normalized = deepcopy(output)
        for case in normalized["cases"]:
            if not isinstance(case, dict):
                continue
            for alias, canonical in CASE_FIELD_ALIASES.items():
                if alias not in case:
                    continue
                if canonical in case and case[canonical] != case[alias]:
                    raise AiOutputError(f"字段 {alias} 与 {canonical} 同时存在且内容冲突")
                case.setdefault(canonical, case[alias])
                del case[alias]
        return normalized

    def _validate_case(self, case: Any, index: int, case_ids: set[str]) -> None:
        if not isinstance(case, dict):
            raise AiOutputError("用例必须是对象")
        unknown = set(case) - ALLOWED_CASE_FIELDS
        if unknown:
            raise AiOutputError(f"包含未知字段: {', '.join(sorted(unknown))}")
        for required in ("case_id", "title", "method", "path", "assertions"):
            if not case.get(required):
                raise AiOutputError(f"缺少字段: {required}")
        case_id = str(case["case_id"])
        if case_id in case_ids:
            raise AiOutputError(f"case_id 重复: {case_id}")
        case_ids.add(case_id)

        method = str(case["method"]).upper()
        path = str(case["path"])
        if not self._interface_exists(method, path):
            raise AiOutputError(f"接口不存在或 method/path 不匹配: {method} {path}")
        if self.target_interface and not self._matches_target(method, path):
            raise AiOutputError(
                "当前批次只能生成目标接口: "
                f"{self.target_interface.method.upper()} {self.target_interface.path}"
            )
        if case.get("case_type", "positive") not in CASE_TYPES:
            raise AiOutputError(f"不支持的 case_type: {case.get('case_type')}")
        if case.get("priority", "P1") not in PRIORITIES:
            raise AiOutputError(f"不支持的 priority: {case.get('priority')}")
        if not isinstance(case["assertions"], list) or not case["assertions"]:
            raise AiOutputError("assertions 必须是非空数组")
        for assertion in case["assertions"]:
            self._validate_assertion(assertion)
        if not isinstance(case.get("extracts", []), list):
            raise AiOutputError("extracts 必须是数组")
        for extract in case.get("extracts", []):
            if not isinstance(extract, dict) or not extract.get("name") or not extract.get("path"):
                raise AiOutputError("extracts 中每项必须包含 name 和 path")
        if not isinstance(case.get("depends_on", []), list):
            raise AiOutputError("depends_on 必须是数组")
        self._reject_code_like_values(case)

    def _validate_assertion(self, assertion: Any) -> None:
        if not isinstance(assertion, dict):
            raise AiOutputError("断言必须是对象")
        target = assertion.get("target")
        operator = assertion.get("operator")
        if target not in ASSERTION_TARGETS:
            raise AiOutputError(f"不支持的断言 target: {target}")
        if operator not in ASSERTION_OPERATORS:
            raise AiOutputError(f"不支持的断言 operator: {operator}")
        if target == "status_code" and not isinstance(assertion.get("expected"), int):
            raise AiOutputError("status_code 断言的 expected 必须是整数")
        if target == "json" and not str(assertion.get("path", "")).startswith("$"):
            raise AiOutputError("json 断言的 path 必须是 JSONPath")
        if target == "header" and not assertion.get("path"):
            raise AiOutputError("header 断言必须提供 path")

    def _dependency_errors(self, cases: list[dict[str, Any]], case_ids: set[str]) -> list[str]:
        graph: dict[str, list[str]] = defaultdict(list)
        errors: list[str] = []
        for case in cases:
            case_id = str(case.get("case_id"))
            for dependency in case.get("depends_on", []):
                dependency = str(dependency)
                if dependency not in case_ids and dependency not in self.allowed_dependency_ids:
                    errors.append(f"{case_id} 依赖不存在的用例: {dependency}")
                graph[case_id].append(dependency)

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                errors.append(f"发现循环依赖: {node}")
                return
            if node in visited:
                return
            visiting.add(node)
            for parent in graph[node]:
                visit(parent)
            visiting.remove(node)
            visited.add(node)

        for node in list(graph):
            visit(node)
        return errors

    def _interface_exists(self, method: str, path: str) -> bool:
        if (method, path) in self.interfaces:
            return True
        for (known_method, known_path) in self.interfaces:
            if known_method != method:
                continue
            pattern = re.sub(r"\{[^/]+\}", r"[^/]+", known_path)
            if re.fullmatch(pattern, path):
                return True
        return False

    def _matches_target(self, method: str, path: str) -> bool:
        if not self.target_interface or method != self.target_interface.method.upper():
            return False
        target_path = self.target_interface.path
        pattern = re.sub(r"\{[^/]+\}", r"[^/]+", target_path)
        return bool(re.fullmatch(pattern, path))

    @staticmethod
    def _reject_code_like_values(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if str(key) in {"script", "python", "shell", "command", "code"}:
                    raise AiOutputError(f"禁止输出脚本字段: {key}")
                AiOutputValidator._reject_code_like_values(item)
        elif isinstance(value, list):
            for item in value:
                AiOutputValidator._reject_code_like_values(item)
        elif isinstance(value, str) and re.search(r"\b(eval|exec|subprocess|os\.system)\s*\(", value):
            raise AiOutputError("输出包含禁止执行的代码片段")
