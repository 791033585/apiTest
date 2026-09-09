from typing import Any, Protocol

from ai.output_validator import AiOutputValidator
from ai.prompt_builder import build_messages
from ai.schemas import AiOutputError, ensure_output_object
from core.models import ApiCase
from core.openapi_models import ImportedOpenApi, OpenApiInterface


class JsonGenerator(Protocol):
    def generate_json(self, messages: list[dict[str, str]]) -> dict[str, Any]: ...


class AiCaseGenerator:
    def __init__(self, client: JsonGenerator, max_cases_per_interface: int = 20):
        if max_cases_per_interface <= 0:
            raise ValueError("max_cases_per_interface 必须大于 0")
        self.client = client
        self.max_cases_per_interface = max_cases_per_interface

    def generate(self, imported: ImportedOpenApi, requirement: str = "") -> dict[str, Any]:
        all_cases: list[dict[str, Any]] = []
        known_case_ids: set[str] = set()

        for interface in imported.interfaces:
            batch = self._generate_interface(
                imported,
                interface,
                requirement,
                known_case_ids,
            )
            batch_case_ids = {str(case["case_id"]) for case in batch["cases"]}
            duplicates = sorted(known_case_ids & batch_case_ids)
            if duplicates:
                raise AiOutputError(f"跨接口生成了重复 case_id: {', '.join(duplicates)}")
            all_cases.extend(batch["cases"])
            known_case_ids.update(batch_case_ids)

        result = {
            "schema_version": "1.0",
            "source_document": {"title": imported.title, "version": imported.version},
            "generation_requirement": requirement,
            "cases": all_cases,
        }
        return AiOutputValidator(imported).validate(result)

    def generate_one(
        self,
        imported: ImportedOpenApi,
        operation_id: str,
        requirement: str = "",
    ) -> dict[str, Any]:
        """只为一个 operation_id 生成用例，适合先做小范围真实验证。"""
        interface = next(
            (item for item in imported.interfaces if item.operation_id == operation_id),
            None,
        )
        if interface is None:
            available = ", ".join(item.operation_id for item in imported.interfaces)
            raise ValueError(f"找不到 operation_id={operation_id}，可选值: {available}")

        batch = self._generate_interface(imported, interface, requirement, set())
        result = {
            "schema_version": "1.0",
            "source_document": {"title": imported.title, "version": imported.version},
            "generation_requirement": requirement,
            "cases": batch["cases"],
        }
        return AiOutputValidator(imported).validate(result)

    def _generate_interface(
        self,
        imported: ImportedOpenApi,
        interface: OpenApiInterface,
        requirement: str,
        known_case_ids: set[str],
    ) -> dict[str, Any]:
        messages = build_messages(
            imported,
            requirement,
            interface,
            known_case_ids,
            self.max_cases_per_interface,
        )
        output = self.client.generate_json(messages)
        validator = AiOutputValidator(
            imported,
            target_interface=interface,
            allowed_dependency_ids=known_case_ids,
            max_cases=self.max_cases_per_interface,
        )
        try:
            validated = validator.validate(output)
            if not validated["cases"]:
                raise AiOutputError("当前接口没有生成任何用例")
            return validated
        except AiOutputError as first_error:
            repair_messages = [
                *messages,
                {"role": "assistant", "content": str(output)},
                {
                    "role": "user",
                    "content": (
                        "请只修复当前接口这一批 JSON 的结构或约束错误，返回完整 JSON。"
                        "不要输出其他接口的用例，不要改变合法字段。"
                        f"校验错误为：{first_error}"
                    ),
                },
            ]
            repaired = self.client.generate_json(repair_messages)
            validated = validator.validate(repaired)
            if not validated["cases"]:
                raise AiOutputError("修复后的当前接口批次没有生成任何用例")
            return validated

    @staticmethod
    def ensure_json(output: dict[str, Any]) -> dict[str, Any]:
        return ensure_output_object(output)
