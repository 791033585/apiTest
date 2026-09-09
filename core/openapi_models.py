from dataclasses import dataclass, field
from typing import Any


@dataclass
class OpenApiParameter:
    name: str
    location: str
    required: bool = False
    schema: dict[str, Any] = field(default_factory=dict)
    example: Any = None
    examples: list[Any] = field(default_factory=list)
    description: str = ""


@dataclass
class OpenApiRequestBody:
    content_type: str
    required: bool = False
    schema: dict[str, Any] = field(default_factory=dict)
    example: Any = None
    examples: list[Any] = field(default_factory=list)


@dataclass
class OpenApiResponse:
    status_code: str
    description: str = ""
    schema: dict[str, Any] = field(default_factory=dict)
    example: Any = None
    examples: list[Any] = field(default_factory=list)


@dataclass
class OpenApiInterface:
    operation_id: str
    method: str
    path: str
    tags: list[str] = field(default_factory=list)
    summary: str = ""
    description: str = ""
    parameters: list[OpenApiParameter] = field(default_factory=list)
    request_body: OpenApiRequestBody | None = None
    responses: dict[str, OpenApiResponse] = field(default_factory=dict)
    security: list[dict[str, list[str]]] = field(default_factory=list)


@dataclass
class ImportedOpenApi:
    version: str
    title: str
    interfaces: list[OpenApiInterface] = field(default_factory=list)
    security_schemes: dict[str, dict[str, Any]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

