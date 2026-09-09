from dataclasses import asdict
from typing import Any

from core.openapi_models import (
    ImportedOpenApi,
    OpenApiInterface,
    OpenApiParameter,
    OpenApiRequestBody,
    OpenApiResponse,
)


def imported_to_dict(imported: ImportedOpenApi) -> dict[str, Any]:
    return asdict(imported)


def imported_from_dict(value: dict[str, Any]) -> ImportedOpenApi:
    interfaces = []
    for raw_interface in value.get("interfaces", []):
        parameters = [OpenApiParameter(**item) for item in raw_interface.get("parameters", [])]
        raw_body = raw_interface.get("request_body")
        request_body = OpenApiRequestBody(**raw_body) if raw_body else None
        responses = {
            key: OpenApiResponse(**response)
            for key, response in raw_interface.get("responses", {}).items()
        }
        interfaces.append(
            OpenApiInterface(
                operation_id=raw_interface["operation_id"],
                method=raw_interface["method"],
                path=raw_interface["path"],
                tags=raw_interface.get("tags", []),
                summary=raw_interface.get("summary", ""),
                description=raw_interface.get("description", ""),
                parameters=parameters,
                request_body=request_body,
                responses=responses,
                security=raw_interface.get("security", []),
            )
        )
    return ImportedOpenApi(
        version=str(value.get("version", "")),
        title=str(value.get("title", "")),
        interfaces=interfaces,
        security_schemes=value.get("security_schemes", {}) or {},
        warnings=value.get("warnings", []) or [],
    )

