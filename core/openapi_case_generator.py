from typing import Any

from core.models import ApiCase
from core.openapi_models import ImportedOpenApi, OpenApiInterface, OpenApiParameter, OpenApiResponse


class OpenApiCaseGenerator:
    """Create executable baseline cases without inventing business assertions."""

    def generate(self, imported: ImportedOpenApi) -> list[ApiCase]:
        return [self._case_from_interface(index, interface, imported) for index, interface in enumerate(imported.interfaces, 1)]

    def _case_from_interface(self, index: int, interface: OpenApiInterface, imported: ImportedOpenApi) -> ApiCase:
        path = interface.path
        params: dict[str, Any] = {}
        headers: dict[str, Any] = {}
        data: dict[str, Any] = {}
        json_body: Any = {}
        notes: list[str] = []
        enabled = True

        for parameter in interface.parameters:
            value = self._parameter_value(parameter)
            if value is None:
                if parameter.location == "path":
                    value = "{{" + parameter.name.upper() + "}}"
                    enabled = False
                    notes.append(f"path 参数 {parameter.name} 缺少 example/default")
                elif parameter.required:
                    enabled = False
                    notes.append(f"必填参数 {parameter.name} 缺少 example/default")
                else:
                    continue
            if parameter.location == "path":
                path = path.replace("{" + parameter.name + "}", str(value))
            elif parameter.location == "query":
                params[parameter.name] = value
            elif parameter.location == "header":
                headers[parameter.name] = value
            elif parameter.location == "cookie":
                headers["Cookie"] = f"{parameter.name}={value}"

        if interface.request_body:
            body = interface.request_body
            json_body = self._example_or_schema(body.example, body.examples, body.schema)
            if "json" in body.content_type:
                headers.setdefault("Content-Type", body.content_type)
            else:
                data = json_body if isinstance(json_body, dict) else {"value": json_body}
                json_body = {}
            if body.required and not json_body and not data:
                enabled = False
                notes.append("必填 requestBody 缺少 example，无法生成请求体")

        self._apply_security(headers, interface.security, imported.security_schemes)
        expected = self._success_status(interface.responses)
        if expected is None:
            enabled = False
            notes.append("responses 中没有 2xx 成功状态码")

        return ApiCase(
            case_id=str(index),
            module=interface.tags[0] if interface.tags else "default",
            feature=interface.summary or interface.operation_id,
            story="OpenAPI 基础调用",
            title=interface.summary or interface.operation_id,
            method=interface.method,
            path=path,
            headers=headers,
            params=params,
            data=data,
            json_body=json_body,
            check="status_code" if expected is not None else "",
            expected=expected,
            notes="；".join(notes),
            enabled=enabled,
        )

    def _parameter_value(self, parameter: OpenApiParameter) -> Any:
        if parameter.example is not None:
            return parameter.example
        if parameter.examples:
            return parameter.examples[0]
        return self._sample_from_schema(parameter.schema)

    def _example_or_schema(self, example: Any, examples: list[Any], schema: dict[str, Any]) -> Any:
        if example is not None:
            return example
        if examples:
            return examples[0]
        return self._sample_from_schema(schema)

    def _sample_from_schema(self, schema: dict[str, Any]) -> Any:
        if not isinstance(schema, dict):
            return None
        if "example" in schema:
            return schema["example"]
        if "default" in schema:
            return schema["default"]
        if "enum" in schema and schema["enum"]:
            return schema["enum"][0]
        if "allOf" in schema:
            merged: dict[str, Any] = {}
            for item in schema["allOf"]:
                value = self._sample_from_schema(item)
                if isinstance(value, dict):
                    merged.update(value)
            return merged or None

        schema_type = schema.get("type")
        if schema_type == "object" or "properties" in schema:
            return {
                name: self._sample_from_schema(property_schema)
                for name, property_schema in schema.get("properties", {}).items()
                if not property_schema.get("readOnly", False)
            }
        if schema_type == "array":
            item = self._sample_from_schema(schema.get("items", {}))
            return [] if item is None else [item]
        if schema_type == "integer":
            return 1
        if schema_type == "number":
            return 1.0
        if schema_type == "boolean":
            return True
        if schema_type == "string":
            formats = {
                "email": "user@example.com",
                "date": "2026-01-01",
                "date-time": "2026-01-01T00:00:00Z",
                "uuid": "00000000-0000-0000-0000-000000000000",
                "password": "Password123",
            }
            return formats.get(schema.get("format"), "string")
        return None

    def _apply_security(
        self,
        headers: dict[str, Any],
        security: list[dict[str, list[str]]],
        schemes: dict[str, dict[str, Any]],
    ) -> None:
        if not security:
            return
        selected = next(iter(security), {})
        for scheme_name in selected:
            scheme = schemes.get(scheme_name, {})
            scheme_type = scheme.get("type")
            if scheme_type == "http" and scheme.get("scheme", "").lower() == "bearer":
                headers.setdefault("Authorization", "Bearer {{TOKEN}}")
            elif scheme_type == "apiKey":
                key_name = scheme.get("name", "X-API-Key")
                location = scheme.get("in", "header")
                if location == "header":
                    headers.setdefault(key_name, "{{API_KEY}}")
            elif scheme_type == "basic" or (scheme_type == "http" and scheme.get("scheme") == "basic"):
                headers.setdefault("Authorization", "Basic {{BASIC_AUTH}}")

    @staticmethod
    def _success_status(responses: dict[str, OpenApiResponse]) -> int | None:
        for status_code in responses:
            try:
                code = int(status_code)
            except (TypeError, ValueError):
                continue
            if 200 <= code < 300:
                return code
        return None

