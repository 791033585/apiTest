import json
from typing import Any

from ai.skill_loader import load_skills
from core.openapi_models import ImportedOpenApi, OpenApiInterface
from core.openapi_serialization import imported_to_dict


def build_messages(
    imported: ImportedOpenApi,
    requirement: str = "",
    target_interface: OpenApiInterface | None = None,
    known_case_ids: set[str] | None = None,
    max_cases: int = 20,
) -> list[dict[str, str]]:
    interface_data = imported_to_dict(imported)
    known_case_ids = known_case_ids or set()
    skills = load_skills()
    if target_interface is None:
        task = "根据接口定义生成正常、异常、边界和必要的依赖测试场景"
        input_data: dict[str, Any] = {"interface_definitions": interface_data}
    else:
        task = "只为 target_interface 生成正常、异常、边界和必要的依赖测试场景"
        input_data = {
            "target_interface": imported_to_dict(
                ImportedOpenApi(
                    version=imported.version,
                    title=imported.title,
                    interfaces=[target_interface],
                    security_schemes=imported.security_schemes,
                )
            )["interfaces"][0],
            "available_interfaces": [
                {
                    "operation_id": item.operation_id,
                    "method": item.method,
                    "path": item.path,
                    "summary": item.summary,
                }
                for item in imported.interfaces
            ],
            "known_case_ids": sorted(known_case_ids),
        }
    system_prompt = (
        "你是接口自动化测试用例设计器。只返回符合 schema_version=1.0 的 JSON，禁止 Markdown，"
        "禁止 Python 代码。method 和 path 必须来自输入接口定义，不得编造不存在的接口。"
        "输出必须是 JSON 对象，顶层必须包含 schema_version 和 cases。"
        f"每次只处理当前 Prompt 指定的接口，最多生成 {max_cases} 条有依据的用例。"
        "不要输出解释、分析过程或 JSON 之外的任何文字。"
        "请求查询参数字段必须命名为 params，请求 JSON body 字段必须命名为 json；"
        "禁止使用 query、query_params、body、request_body 等替代字段名。"
        "\n\n你必须遵守以下接口测试 Skill：\n"
        f"{skills}"
    )
    user_prompt = json.dumps(
        {
            "task": task,
            "requirement": requirement,
            **input_data,
            "output_rules": {
                "case_type": ["positive", "negative", "boundary", "dependency"],
                "assertion_targets": ["status_code", "json", "header", "response_time"],
                "assertion_operators": ["eq", "ne", "contains", "gt", "ge", "lt", "le"],
                "no_business_guess": "Swagger 没有提供的信息不要伪造，在 notes 中说明",
                "batch_scope": "只输出当前 target_interface 的用例；如果是分批生成，不要输出其他接口的用例",
                "dependency_scope": "depends_on 只能引用 known_case_ids 中的 case_id",
                "max_cases": max_cases,
                "no_extra_text": "只返回 JSON 对象，不要 Markdown、解释、前缀或后缀",
                "canonical_request_fields": {
                    "query_parameters": "params",
                    "json_request_body": "json",
                    "form_request_body": "data",
                },
            },
            "output_example": {
                "schema_version": "1.0",
                "cases": [
                    {
                        "case_id": "operation-positive-001",
                        "title": "接口成功场景",
                        "case_type": "positive",
                        "priority": "P1",
                        "method": "GET",
                        "path": "/resource",
                        "assertions": [
                            {"target": "status_code", "operator": "eq", "expected": 200}
                        ],
                        "extracts": [],
                        "depends_on": [],
                        "enabled": True,
                    }
                ],
            },
        },
        ensure_ascii=False,
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
