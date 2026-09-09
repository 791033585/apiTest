import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from ai.case_generator import AiCaseGenerator
from ai.llm_client import LlmConfigurationError, LlmResponseError, DeepSeekClient
from core.openapi_importer import OpenApiDocumentError, OpenApiImporter
from core.openapi_serialization import imported_to_dict
from web.runner import PytestRunService
from web.schemas import CaseUpdate, GenerateRequest, RunRequest
from web.storage import FileStorage


router = APIRouter(prefix="/api")
storage = FileStorage()
runner = PytestRunService(storage_root=storage.root)


def _interface_summary(imported) -> list[dict[str, Any]]:
    return [
        {
            "operation_id": item.operation_id,
            "method": item.method,
            "path": item.path,
            "summary": item.summary,
            "tags": item.tags,
        }
        for item in imported.interfaces
    ]


def _get_interface(operation_id: str):
    imported = storage.load_imported()
    return imported, next(
        (item for item in imported.interfaces if item.operation_id == operation_id),
        None,
    )


@router.post("/specs/upload")
async def upload_spec(file: UploadFile = File(...)):
    filename = Path(file.filename or "").name
    if Path(filename).suffix.lower() not in {".json", ".yaml", ".yml"}:
        raise HTTPException(status_code=400, detail="只支持 .json、.yaml、.yml 文件")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    temporary = storage.uploads / f"_upload_{filename}"
    temporary.write_bytes(content)
    try:
        imported = OpenApiImporter.from_file(temporary).parse()
        metadata = storage.save_spec(filename, content, imported)
        return {
            "spec_id": metadata["spec_id"],
            "title": imported.title,
            "version": imported.version,
            "filename": filename,
            "interfaces": _interface_summary(imported),
        }
    except (OpenApiDocumentError, ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=f"OpenAPI 解析失败: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)


@router.get("/specs/{spec_id}/interfaces")
def list_spec_interfaces(spec_id: str):
    try:
        imported = storage.load_imported(spec_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"spec_id": spec_id, "interfaces": _interface_summary(imported)}


@router.get("/interfaces")
def list_current_interfaces():
    try:
        spec_id = storage.current_spec_id()
        imported = storage.load_imported(spec_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"spec_id": spec_id, "interfaces": _interface_summary(imported)}


@router.post("/interfaces/{operation_id}/generate")
def generate_cases(operation_id: str, request: GenerateRequest):
    try:
        imported, interface = _get_interface(operation_id)
        if interface is None:
            raise HTTPException(status_code=404, detail=f"接口不存在: {operation_id}")
        generated = AiCaseGenerator(
            DeepSeekClient.from_env(),
            max_cases_per_interface=request.max_cases,
        ).generate_one(imported, operation_id, request.requirement)
        merged = storage.replace_operation_cases(operation_id, generated)
        return {"operation_id": operation_id, "cases": [case for case in merged["cases"] if storage.case_operation_id(case) == operation_id]}
    except (LlmConfigurationError, LlmResponseError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/interfaces/{operation_id}/cases")
def list_cases(operation_id: str):
    try:
        imported, interface = _get_interface(operation_id)
        if interface is None:
            raise HTTPException(status_code=404, detail=f"接口不存在: {operation_id}")
        output = storage.load_cases()
        cases = [case for case in output.get("cases", []) if storage.case_operation_id(case) == operation_id]
        return {"operation_id": operation_id, "cases": cases}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/cases/{case_id}")
def update_case(case_id: str, request: CaseUpdate):
    try:
        output = storage.load_cases()
        case, _ = storage.find_case(case_id)
        updates = request.model_dump(exclude_unset=True, by_alias=True)
        case.update(updates)
        storage.save_cases(output)
        return case
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/cases/{case_id}")
def delete_case(case_id: str):
    try:
        output = storage.load_cases()
        storage.find_case(case_id)
        output["cases"] = [case for case in output.get("cases", []) if str(case.get("case_id")) != case_id]
        storage.save_cases(output)
        return {"deleted": case_id}
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/runs")
def run_cases(request: RunRequest):
    if not request.base_url.strip():
        raise HTTPException(status_code=400, detail="必须填写被测项目 Base URL")
    try:
        output = storage.load_cases()
        selected = [
            case
            for case in output.get("cases", [])
            if str(case.get("case_id")) in set(request.case_ids) and case.get("enabled", True)
        ]
        missing = sorted(set(request.case_ids) - {str(case.get("case_id")) for case in selected})
        if missing:
            raise HTTPException(status_code=400, detail=f"用例不存在或未启用: {', '.join(missing)}")
        result = runner.execute(
            {**output, "cases": selected},
            request.base_url.strip(),
            request.headers,
            request.variables,
        )
        return result
    except HTTPException:
        raise
    except (FileNotFoundError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    path = storage.runs / run_id / "summary.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"运行记录不存在: {run_id}")
    return json.loads(path.read_text(encoding="utf-8"))
