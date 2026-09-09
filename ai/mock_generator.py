from typing import Any

from core.openapi_models import ImportedOpenApi


class MockCaseGenerator:
    """Deterministic stand-in for an LLM used by offline tests."""

    def generate(self, imported: ImportedOpenApi, requirement: str = "") -> dict[str, Any]:
        interfaces = {(item.method, item.path): item for item in imported.interfaces}
        required_paths = [("POST", "/login"), ("GET", "/users")]
        missing = [f"{method} {path}" for method, path in required_paths if (method, path) not in interfaces]
        if missing:
            raise ValueError(f"Mock 示例缺少接口: {', '.join(missing)}")
        return {
            "schema_version": "1.0",
            "source_document": {"title": imported.title, "version": imported.version},
            "generation_requirement": requirement,
            "cases": [
                {
                    "source_interface": {"operation_id": "login", "method": "POST", "path": "/login"},
                    "case_id": "login-positive-001",
                    "title": "管理员登录成功",
                    "case_type": "positive",
                    "priority": "P0",
                    "description": "使用正确账号密码登录",
                    "method": "POST",
                    "path": "/login",
                    "headers": {"Content-Type": "application/json"},
                    "params": {},
                    "data": {},
                    "json": {"username": "admin", "password": "123456"},
                    "files": {},
                    "assertions": [
                        {"target": "status_code", "path": "", "operator": "eq", "expected": 200},
                        {"target": "json", "path": "$.code", "operator": "eq", "expected": 0},
                        {"target": "json", "path": "$.msg", "operator": "eq", "expected": "登录成功"},
                    ],
                    "extracts": [
                        {"name": "TOKEN", "source": "json", "path": "$.data.token"},
                        {"name": "USER_ID", "source": "json", "path": "$.data.user.id"},
                    ],
                    "depends_on": [],
                    "enabled": True,
                    "notes": "",
                },
                {
                    "source_interface": {"operation_id": "login", "method": "POST", "path": "/login"},
                    "case_id": "login-negative-001",
                    "title": "错误密码登录失败",
                    "case_type": "negative",
                    "priority": "P1",
                    "description": "使用错误密码登录",
                    "method": "POST",
                    "path": "/login",
                    "headers": {"Content-Type": "application/json"},
                    "params": {},
                    "data": {},
                    "json": {"username": "admin", "password": "wrong"},
                    "files": {},
                    "assertions": [
                        {"target": "status_code", "path": "", "operator": "eq", "expected": 401},
                        {"target": "json", "path": "$.msg", "operator": "eq", "expected": "登录失败"},
                    ],
                    "extracts": [],
                    "depends_on": [],
                    "enabled": True,
                    "notes": "",
                },
                {
                    "source_interface": {"operation_id": "login", "method": "POST", "path": "/login"},
                    "case_id": "login-boundary-001",
                    "title": "密码为空登录失败",
                    "case_type": "boundary",
                    "priority": "P1",
                    "description": "验证密码为空时的接口响应",
                    "method": "POST",
                    "path": "/login",
                    "headers": {"Content-Type": "application/json"},
                    "params": {},
                    "data": {},
                    "json": {"username": "admin", "password": ""},
                    "files": {},
                    "assertions": [
                        {"target": "status_code", "path": "", "operator": "eq", "expected": 401}
                    ],
                    "extracts": [],
                    "depends_on": [],
                    "enabled": True,
                    "notes": "",
                },
                {
                    "source_interface": {"operation_id": "listUsers", "method": "GET", "path": "/users"},
                    "case_id": "users-dependency-001",
                    "title": "登录后查询用户列表",
                    "case_type": "dependency",
                    "priority": "P0",
                    "description": "使用登录接口提取的 Token 查询用户列表",
                    "method": "GET",
                    "path": "/users",
                    "headers": {"Authorization": "Bearer {{TOKEN}}"},
                    "params": {"page": 1, "page_size": 10},
                    "data": {},
                    "json": {},
                    "files": {},
                    "assertions": [
                        {"target": "status_code", "path": "", "operator": "eq", "expected": 200},
                        {"target": "json", "path": "$.code", "operator": "eq", "expected": 0},
                    ],
                    "extracts": [],
                    "depends_on": ["login-positive-001"],
                    "enabled": True,
                    "notes": "",
                },
            ],
        }

