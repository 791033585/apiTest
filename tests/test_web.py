from pathlib import Path

from fastapi.testclient import TestClient

from ai.llm_client import LlmConfigurationError
from web import routes
from web.app import app
from web.storage import FileStorage


OPENAPI_FILE = Path(__file__).parents[1] / "examples" / "openapi" / "demo_openapi.yaml"


class FakeRunner:
    def execute(self, output, base_url, global_headers, variables):
        assert base_url == "http://demo.test"
        assert global_headers == {"X-Test": "1"}
        assert variables == {"TOKEN": "demo-token"}
        return {
            "run_id": "run-test",
            "total": len(output["cases"]),
            "passed": len(output["cases"]),
            "failed": 0,
            "duration": 0.01,
            "output": "1 passed",
            "report_url": "/run-files/run-test/report.html",
            "allure_results_url": "/run-files/run-test/allure-results/",
        }


def test_web_upload_list_edit_delete_and_run(tmp_path, monkeypatch):
    test_storage = FileStorage(tmp_path / "storage")
    monkeypatch.setattr(routes, "storage", test_storage)
    monkeypatch.setattr(routes, "runner", FakeRunner())

    with TestClient(app) as client:
        with OPENAPI_FILE.open("rb") as source:
            upload = client.post(
                "/api/specs/upload",
                files={"file": ("demo_openapi.yaml", source, "application/yaml")},
            )
        assert upload.status_code == 200
        payload = upload.json()
        assert len(payload["interfaces"]) == 4

        interfaces = client.get("/api/interfaces")
        assert interfaces.status_code == 200
        assert interfaces.json()["interfaces"][0]["operation_id"] == "login"

        test_storage.save_cases(
            {
                "schema_version": "1.0",
                "cases": [
                    {
                        "source_interface": {"operation_id": "login"},
                        "case_id": "login-001",
                        "title": "登录成功",
                        "method": "POST",
                        "path": "/login",
                        "json": {"username": "admin", "password": "123456"},
                        "assertions": [{"target": "status_code", "operator": "eq", "expected": 200}],
                        "enabled": True,
                    }
                ],
            }
        )
        updated = client.put("/api/cases/login-001", json={"title": "修改后的登录"})
        assert updated.status_code == 200
        assert updated.json()["title"] == "修改后的登录"

        run = client.post(
            "/api/runs",
            json={
                "case_ids": ["login-001"],
                "base_url": "http://demo.test",
                "headers": {"X-Test": "1"},
                "variables": {"TOKEN": "demo-token"},
            },
        )
        assert run.status_code == 200
        assert run.json()["passed"] == 1

        deleted = client.delete("/api/cases/login-001")
        assert deleted.status_code == 200
        assert client.get("/api/interfaces/login/cases").json()["cases"] == []


def test_web_run_requires_base_url(tmp_path, monkeypatch):
    test_storage = FileStorage(tmp_path / "storage")
    monkeypatch.setattr(routes, "storage", test_storage)
    with TestClient(app) as client:
        response = client.post("/api/runs", json={"case_ids": ["missing"], "base_url": ""})
    assert response.status_code == 422


def test_web_lists_legacy_cases_without_source_interface(tmp_path, monkeypatch):
    test_storage = FileStorage(tmp_path / "storage")
    monkeypatch.setattr(routes, "storage", test_storage)

    with TestClient(app) as client:
        with OPENAPI_FILE.open("rb") as source:
            client.post(
                "/api/specs/upload",
                files={"file": ("demo.yaml", source, "application/yaml")},
            )
        test_storage.save_cases(
            {
                "schema_version": "1.0",
                "cases": [
                    {
                        "case_id": "login-positive-001",
                        "title": "历史登录用例",
                        "method": "POST",
                        "path": "/login",
                        "assertions": [{"target": "status_code", "operator": "eq", "expected": 200}],
                    }
                ],
            }
        )
        response = client.get("/api/interfaces/login/cases")

    assert response.status_code == 200
    assert [case["case_id"] for case in response.json()["cases"]] == ["login-positive-001"]

def test_web_generate_reports_missing_api_key(tmp_path, monkeypatch):
    test_storage = FileStorage(tmp_path / "storage")
    monkeypatch.setattr(routes, "storage", test_storage)
    monkeypatch.setattr(routes.DeepSeekClient, "from_env", lambda: (_ for _ in ()).throw(LlmConfigurationError("未配置 DEEPSEEK_API_KEY")))
    with TestClient(app) as client:
        with OPENAPI_FILE.open("rb") as source:
            client.post("/api/specs/upload", files={"file": ("demo.yaml", source, "application/yaml")})
        response = client.post("/api/interfaces/login/generate", json={})
    assert response.status_code == 502
    assert "DEEPSEEK_API_KEY" in response.json()["detail"]
