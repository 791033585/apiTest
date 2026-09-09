import json
from pathlib import Path

import pytest

from ai.case_normalizer import normalize_cases
from ai.case_generator import AiCaseGenerator
from ai.mock_generator import MockCaseGenerator
from ai.output_validator import AiOutputError, AiOutputValidator
from core.case_loader import ExcelCaseLoader
from core.case_writer import ExcelCaseWriter
from core.openapi_importer import OpenApiImporter


OPENAPI_FILE = Path(__file__).parents[1] / "examples" / "openapi" / "demo_openapi.yaml"


class BatchClient:
    def __init__(self):
        self.calls = []

    def generate_json(self, messages):
        self.calls.append(messages)
        request = json.loads(messages[1]["content"])
        target = request["target_interface"]
        method = target["method"].upper()
        path = target["path"]
        operation_id = target["operation_id"]
        case_id = f"{operation_id}-positive-001"
        depends_on = []
        headers = {}
        if method == "GET" and path == "/users" and "login-positive-001" in request["known_case_ids"]:
            depends_on = ["login-positive-001"]
            headers = {"Authorization": "Bearer {{TOKEN}}"}
        return {
            "schema_version": "1.0",
            "cases": [
                {
                    "case_id": case_id,
                    "title": f"{operation_id} 成功",
                    "case_type": "positive",
                    "priority": "P1",
                    "method": method,
                    "path": path,
                    "headers": headers,
                    "params": {},
                    "data": {},
                    "json": {},
                    "files": {},
                    "assertions": [{"target": "status_code", "operator": "eq", "expected": 200}],
                    "extracts": [],
                    "depends_on": depends_on,
                    "enabled": True,
                }
            ],
        }


def test_ai_generator_batches_interfaces_and_merges_results():
    imported = OpenApiImporter.from_file(OPENAPI_FILE).parse()
    client = BatchClient()

    output = AiCaseGenerator(client).generate(imported)

    assert len(client.calls) == len(imported.interfaces)
    assert len(output["cases"]) == len(imported.interfaces)
    users_case = next(case for case in output["cases"] if case["path"] == "/users")
    assert users_case["depends_on"] == ["login-positive-001"]
    first_request = json.loads(client.calls[0][1]["content"])
    assert first_request["output_rules"]["max_cases"] == 20


def test_ai_generator_can_generate_one_interface():
    imported = OpenApiImporter.from_file(OPENAPI_FILE).parse()
    client = BatchClient()

    output = AiCaseGenerator(client).generate_one(imported, "login")

    assert len(client.calls) == 1
    assert len(output["cases"]) == 1
    assert output["cases"][0]["method"] == "POST"
    assert output["cases"][0]["path"] == "/login"


def test_validator_normalizes_common_request_field_aliases():
    imported = OpenApiImporter.from_file(OPENAPI_FILE).parse()
    output = {
        "schema_version": "1.0",
        "cases": [
            {
                "case_id": "login-001",
                "title": "登录",
                "method": "POST",
                "path": "/login",
                "query_params": {"trace": "1"},
                "body": {"username": "admin"},
                "assertions": [
                    {"target": "status_code", "operator": "eq", "expected": 200}
                ],
            }
        ],
    }

    validated = AiOutputValidator(imported).validate(output)
    case = validated["cases"][0]
    assert case["params"] == {"trace": "1"}
    assert case["json"] == {"username": "admin"}
    assert "query_params" not in case
    assert "body" not in case


def test_mock_output_round_trips_to_excel(tmp_path):
    imported = OpenApiImporter.from_file(OPENAPI_FILE).parse()
    output = MockCaseGenerator().generate(imported, "生成正常、异常、边界和依赖场景")

    AiOutputValidator(imported).validate(output)
    cases = normalize_cases(output)
    excel_path = ExcelCaseWriter.write(cases, tmp_path / "ai_cases.xlsx")
    loaded = ExcelCaseLoader.load(excel_path)

    assert len(loaded) == 4
    assert len(loaded[0].assertions) == 3
    assert loaded[0].extract_rules[0].name == "TOKEN"
    assert loaded[3].depends_on == ["login-positive-001"]


def test_validator_rejects_unknown_interface_and_code():
    imported = OpenApiImporter.from_file(OPENAPI_FILE).parse()
    output = {
        "schema_version": "1.0",
        "cases": [
            {
                "case_id": "bad-001",
                "title": "非法用例",
                "case_type": "positive",
                "priority": "P1",
                "method": "POST",
                "path": "/not-found",
                "assertions": [
                    {"target": "json", "path": "$.msg", "operator": "eq", "expected": "eval(1)"}
                ],
            }
        ],
    }

    with pytest.raises(AiOutputError, match="接口不存在"):
        AiOutputValidator(imported).validate(output)


def test_validator_rejects_dependency_cycle():
    imported = OpenApiImporter.from_file(OPENAPI_FILE).parse()
    output = {
        "schema_version": "1.0",
        "cases": [
            {
                "case_id": "a",
                "title": "A",
                "method": "GET",
                "path": "/users",
                "assertions": [{"target": "status_code", "operator": "eq", "expected": 200}],
                "depends_on": ["b"],
            },
            {
                "case_id": "b",
                "title": "B",
                "method": "GET",
                "path": "/users",
                "assertions": [{"target": "status_code", "operator": "eq", "expected": 200}],
                "depends_on": ["a"],
            },
        ],
    }

    with pytest.raises(AiOutputError, match="循环依赖"):
        AiOutputValidator(imported).validate(output)
