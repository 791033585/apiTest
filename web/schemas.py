from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class InterfaceSummary(BaseModel):
    operation_id: str
    method: str
    path: str
    summary: str = ""
    tags: list[str] = Field(default_factory=list)


class SpecSummary(BaseModel):
    spec_id: str
    title: str
    version: str
    filename: str
    interfaces: list[InterfaceSummary]


class GenerateRequest(BaseModel):
    requirement: str = ""
    max_cases: int = Field(default=20, ge=1, le=100)


class CaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    title: str | None = None
    headers: dict[str, Any] | None = None
    params: dict[str, Any] | None = None
    data: dict[str, Any] | None = None
    json_body: Any | None = Field(default=None, alias="json")
    assertions: list[dict[str, Any]] | None = None
    extracts: list[dict[str, Any]] | None = None
    depends_on: list[str] | None = None
    enabled: bool | None = None
    notes: str | None = None


class RunRequest(BaseModel):
    case_ids: list[str] = Field(min_length=1)
    base_url: str = Field(min_length=1)
    headers: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)


class RunSummary(BaseModel):
    run_id: str
    total: int
    passed: int
    failed: int
    duration: float
    output: str
    report_url: str | None = None
    allure_results_url: str | None = None
