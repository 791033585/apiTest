from typing import Any

from ai.schemas import ensure_output_object
from core.assertion_models import AssertionRule, ExtractRule
from core.models import ApiCase


def normalize_cases(output: dict[str, Any]) -> list[ApiCase]:
    ensure_output_object(output)
    result = []
    for case in output["cases"]:
        result.append(
            ApiCase(
                case_id=str(case["case_id"]),
                module=str(case.get("source_interface", {}).get("tags", ["AI 生成"])[0])
                if case.get("source_interface", {}).get("tags")
                else "AI 生成",
                feature=str(case.get("source_interface", {}).get("summary", "")),
                story=str(case.get("description", "")),
                title=str(case["title"]),
                method=str(case["method"]).upper(),
                path=str(case["path"]),
                headers=case.get("headers", {}) or {},
                params=case.get("params", {}) or {},
                data=case.get("data", {}) or {},
                json_body=case.get("json", {}) or {},
                files=case.get("files", {}) or {},
                notes=str(case.get("notes", "")),
                enabled=bool(case.get("enabled", True)),
                assertions=[AssertionRule.from_dict(item) for item in case.get("assertions", [])],
                extract_rules=[ExtractRule.from_dict(item) for item in case.get("extracts", [])],
                depends_on=[str(item) for item in case.get("depends_on", [])],
                case_type=str(case.get("case_type", "")),
                priority=str(case.get("priority", "")),
            )
        )
    return result

