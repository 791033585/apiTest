import copy
import json
from pathlib import Path
from typing import Any

import yaml

from core.openapi_models import (
    ImportedOpenApi,
    OpenApiInterface,
    OpenApiParameter,
    OpenApiRequestBody,
    OpenApiResponse,
)


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


class OpenApiDocumentError(ValueError):
    """Raised when an OpenAPI/Swagger document cannot be understood."""


class OpenApiImporter:
    def __init__(self, document: dict[str, Any]):
        if not isinstance(document, dict):
            raise OpenApiDocumentError("OpenAPI 文档必须是 JSON/YAML 对象")
        if not document.get("openapi") and not document.get("swagger"):
            raise OpenApiDocumentError("文档缺少 openapi 或 swagger 版本字段")
        if not isinstance(document.get("paths", {}), dict):
            raise OpenApiDocumentError("文档的 paths 必须是对象")
        self.document = document
        self.is_swagger_2 = bool(document.get("swagger"))
        self.warnings: list[str] = []

    @classmethod
    def from_file(cls, file_path: str | Path) -> "OpenApiImporter":
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"OpenAPI 文件不存在: {path}")
        try:
            with path.open("r", encoding="utf-8") as file:
                if path.suffix.lower() == ".json":
                    document = json.load(file)
                else:
                    document = yaml.safe_load(file)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
            raise OpenApiDocumentError(f"OpenAPI 文件读取失败: {exc}") from exc
        return cls(document)

    def parse(self) -> ImportedOpenApi:
        interfaces: list[OpenApiInterface] = []
        for path, path_item in self.document.get("paths", {}).items():
            if not isinstance(path_item, dict):
                self.warnings.append(f"跳过非对象 path: {path}")
                continue
            for method, operation in path_item.items():
                if method.lower() not in HTTP_METHODS:
                    continue
                if not isinstance(operation, dict):
                    self.warnings.append(f"跳过无效接口定义: {method.upper()} {path}")
                    continue
                interfaces.append(self._parse_interface(path, method.lower(), path_item, operation))

        info = self.document.get("info", {}) or {}
        version = str(self.document.get("openapi") or self.document.get("swagger"))
        return ImportedOpenApi(
            version=version,
            title=str(info.get("title", "")),
            interfaces=interfaces,
            security_schemes=self._security_schemes(),
            warnings=self.warnings,
        )

    def _parse_interface(
        self,
        path: str,
        method: str,
        path_item: dict[str, Any],
        operation: dict[str, Any],
    ) -> OpenApiInterface:
        operation_id = str(operation.get("operationId", f"{method}_{path.strip('/').replace('/', '_') or 'root'}"))
        parameters = self._parameters(path_item.get("parameters", []))
        parameters = self._parameters(operation.get("parameters", []), existing=parameters)
        request_body = self._request_body(operation)
        responses = self._responses(operation.get("responses", {}))
        security = operation["security"] if "security" in operation else self.document.get("security", [])
        return OpenApiInterface(
            operation_id=operation_id,
            method=method.upper(),
            path=path,
            tags=[str(tag) for tag in operation.get("tags", [])],
            summary=str(operation.get("summary", "")),
            description=str(operation.get("description", "")),
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            security=security or [],
        )

    def _parameters(
        self,
        raw_parameters: list[Any],
        existing: list[OpenApiParameter] | None = None,
    ) -> list[OpenApiParameter]:
        result = list(existing or [])
        positions = {(item.location, item.name): index for index, item in enumerate(result)}
        for raw in raw_parameters or []:
            parameter = self._resolve(raw)
            if not isinstance(parameter, dict):
                continue
            name = parameter.get("name")
            location = parameter.get("in")
            if not name or not location:
                self.warnings.append("跳过缺少 name 或 in 的参数")
                continue
            if self.is_swagger_2 and location in {"body", "formData"}:
                continue
            schema = self._resolve(parameter.get("schema", {}))
            if not schema:
                schema = {
                    key: parameter[key]
                    for key in ("type", "format", "enum", "default", "example", "items")
                    if key in parameter
                }
            item = OpenApiParameter(
                name=str(name),
                location=str(location),
                required=bool(parameter.get("required", False)),
                schema=schema if isinstance(schema, dict) else {},
                example=parameter.get("example"),
                examples=self._examples(parameter.get("examples")),
                description=str(parameter.get("description", "")),
            )
            key = (item.location, item.name)
            if key in positions:
                result[positions[key]] = item
            else:
                positions[key] = len(result)
                result.append(item)
        return result

    def _request_body(self, operation: dict[str, Any]) -> OpenApiRequestBody | None:
        if self.is_swagger_2:
            body_parameters = [item for item in operation.get("parameters", []) if item.get("in") == "body"]
            if not body_parameters:
                return None
            body = self._resolve(body_parameters[0])
            return OpenApiRequestBody(
                content_type=(operation.get("consumes") or self.document.get("consumes") or ["application/json"])[0],
                required=bool(body.get("required", False)),
                schema=self._resolve(body.get("schema", {})),
                example=body.get("x-example", body.get("example")),
            )

        raw_body = operation.get("requestBody")
        if not raw_body:
            return None
        body = self._resolve(raw_body)
        content = body.get("content", {}) or {}
        if not content:
            return None
        content_type = self._choose_content_type(content)
        media = content[content_type] or {}
        return OpenApiRequestBody(
            content_type=content_type,
            required=bool(body.get("required", False)),
            schema=self._resolve(media.get("schema", {})),
            example=media.get("example"),
            examples=self._examples(media.get("examples")),
        )

    def _responses(self, raw_responses: dict[str, Any]) -> dict[str, OpenApiResponse]:
        result: dict[str, OpenApiResponse] = {}
        for status_code, raw_response in (raw_responses or {}).items():
            response = self._resolve(raw_response)
            if not isinstance(response, dict):
                continue
            if self.is_swagger_2:
                schema = self._resolve(response.get("schema", {}))
                example = response.get("examples", {}).get("application/json")
                examples = []
            else:
                content = response.get("content", {}) or {}
                content_type = self._choose_content_type(content) if content else None
                media = content.get(content_type, {}) if content_type else {}
                schema = self._resolve(media.get("schema", {}))
                example = media.get("example")
                examples = self._examples(media.get("examples"))
            result[str(status_code)] = OpenApiResponse(
                status_code=str(status_code),
                description=str(response.get("description", "")),
                schema=schema if isinstance(schema, dict) else {},
                example=example,
                examples=examples,
            )
        return result

    def _security_schemes(self) -> dict[str, dict[str, Any]]:
        if self.is_swagger_2:
            return self._resolve(self.document.get("securityDefinitions", {}))
        return self._resolve(self.document.get("components", {}).get("securitySchemes", {}))

    def _choose_content_type(self, content: dict[str, Any]) -> str:
        for preferred in ("application/json", "application/*+json", "application/x-www-form-urlencoded"):
            if preferred in content:
                return preferred
        return next(iter(content))

    @staticmethod
    def _examples(value: Any) -> list[Any]:
        if not isinstance(value, dict):
            return []
        return [item.get("value") for item in value.values() if isinstance(item, dict) and "value" in item]

    def _resolve(self, value: Any, stack: tuple[str, ...] = ()) -> Any:
        if isinstance(value, list):
            return [self._resolve(item, stack) for item in value]
        if not isinstance(value, dict):
            return value
        if "$ref" in value:
            reference = value["$ref"]
            if not isinstance(reference, str) or not reference.startswith("#/"):
                self.warnings.append(f"暂不支持远程或非法 $ref: {reference}")
                return copy.deepcopy(value)
            if reference in stack:
                return {"$ref": reference}
            resolved = self._resolve(self._json_pointer(reference), (*stack, reference))
            siblings = {key: item for key, item in value.items() if key != "$ref"}
            if siblings and isinstance(resolved, dict):
                resolved = {**resolved, **self._resolve(siblings, stack)}
            return resolved
        return {key: self._resolve(item, stack) for key, item in value.items()}

    def _json_pointer(self, reference: str) -> Any:
        current: Any = self.document
        for part in reference[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(current, dict) or part not in current:
                raise OpenApiDocumentError(f"无法解析本地 $ref: {reference}")
            current = current[part]
        return current
