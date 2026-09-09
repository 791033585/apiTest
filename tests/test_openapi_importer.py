import json
from pathlib import Path

from core.case_loader import ExcelCaseLoader
from core.case_writer import ExcelCaseWriter
from core.openapi_case_generator import OpenApiCaseGenerator
from core.openapi_importer import OpenApiImporter


OPENAPI_DIR = Path(__file__).parents[1] / "examples" / "openapi"


def test_openapi_yaml_import_resolves_ref_and_generates_cases(tmp_path):
    imported = OpenApiImporter.from_file(OPENAPI_DIR / "demo_openapi.yaml").parse()

    assert imported.version == "3.0.3"
    assert len(imported.interfaces) == 4
    assert imported.interfaces[0].request_body.schema["properties"]["username"]["example"] == "admin"
    assert imported.interfaces[2].parameters[0].schema["example"] == 1
    assert imported.security_schemes["bearerAuth"]["scheme"] == "bearer"

    cases = OpenApiCaseGenerator().generate(imported)
    assert len(cases) == 4
    assert cases[0].json_body["password"] == "123456"
    assert cases[1].headers["Authorization"] == "Bearer {{TOKEN}}"
    assert cases[2].path == "/users/1"
    assert cases[3].json_body["state"] is True

    excel_path = ExcelCaseWriter.write(cases, tmp_path / "imported_cases.xlsx")
    loaded_cases = ExcelCaseLoader.load(excel_path)
    assert len(loaded_cases) == 4
    assert loaded_cases[1].headers["Authorization"] == "Bearer {{TOKEN}}"


def test_openapi_json_import(tmp_path):
    imported = OpenApiImporter.from_file(OPENAPI_DIR / "demo_openapi.json").parse()
    assert len(imported.interfaces) == 1
    assert imported.interfaces[0].path == "/health"
    assert OpenApiCaseGenerator().generate(imported)[0].expected == 200


def test_imported_definition_can_be_serialized(tmp_path):
    imported = OpenApiImporter.from_file(OPENAPI_DIR / "demo_openapi.yaml").parse()
    payload = {
        "version": imported.version,
        "interfaces": [interface.operation_id for interface in imported.interfaces],
    }
    output = tmp_path / "interfaces.json"
    output.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    assert json.loads(output.read_text(encoding="utf-8"))["interfaces"] == [
        "login", "listUsers", "getUser", "updateUserState"
    ]

