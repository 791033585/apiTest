import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from core.openapi_serialization import imported_from_dict, imported_to_dict
from core.openapi_models import ImportedOpenApi


SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")


class FileStorage:
    """Small JSON-file store for the single-project MVP."""

    def __init__(self, root: str | Path = "storage"):
        self.root = Path(root)
        self.uploads = self.root / "uploads"
        self.specs = self.root / "specs"
        self.interfaces = self.root / "interfaces"
        self.cases = self.root / "cases"
        self.runs = self.root / "runs"
        for directory in (self.uploads, self.specs, self.interfaces, self.cases, self.runs):
            directory.mkdir(parents=True, exist_ok=True)

    def save_spec(
        self,
        filename: str,
        content: bytes,
        imported: ImportedOpenApi,
    ) -> dict[str, Any]:
        spec_id = self._new_id()
        safe_name = Path(filename).name or "openapi.yaml"
        (self.uploads / f"{spec_id}_{safe_name}").write_bytes(content)
        imported_data = imported_to_dict(imported)
        metadata = {
            "spec_id": spec_id,
            "filename": safe_name,
            "title": imported.title,
            "version": imported.version,
            "interfaces": imported_data["interfaces"],
        }
        self._write_json(self.specs / f"{spec_id}.json", metadata)
        self._write_json(self.interfaces / f"{spec_id}.json", imported_data)
        self._write_json(
            self.cases / f"{spec_id}.json",
            {
                "schema_version": "1.0",
                "source_document": {"title": imported.title, "version": imported.version},
                "generation_requirement": "",
                "cases": [],
            },
        )
        self._write_json(self.root / "current.json", {"spec_id": spec_id})
        return metadata

    def current_spec_id(self) -> str:
        current_path = self.root / "current.json"
        if not current_path.exists():
            raise FileNotFoundError("尚未上传 Swagger/OpenAPI 文件")
        return str(self._read_json(current_path)["spec_id"])

    def load_imported(self, spec_id: str | None = None) -> ImportedOpenApi:
        spec_id = spec_id or self.current_spec_id()
        return imported_from_dict(self._read_json(self.interfaces / f"{self._safe_id(spec_id)}.json"))

    def load_cases(self, spec_id: str | None = None) -> dict[str, Any]:
        spec_id = spec_id or self.current_spec_id()
        return self._read_json(self.cases / f"{self._safe_id(spec_id)}.json")

    def save_cases(self, output: dict[str, Any], spec_id: str | None = None) -> None:
        spec_id = spec_id or self.current_spec_id()
        self._write_json(self.cases / f"{self._safe_id(spec_id)}.json", output)

    def replace_operation_cases(
        self,
        operation_id: str,
        generated: dict[str, Any],
        spec_id: str | None = None,
    ) -> dict[str, Any]:
        current = self.load_cases(spec_id)
        imported = self.load_imported(spec_id)
        interface = next(
            (item for item in imported.interfaces if item.operation_id == operation_id),
            None,
        )
        kept = [
            case
            for case in current.get("cases", [])
            if self.case_operation_id(case) != operation_id
        ]
        new_cases = deepcopy(generated.get("cases", []))
        if interface is not None:
            source_interface = {
                "operation_id": interface.operation_id,
                "method": interface.method.upper(),
                "path": interface.path,
                "tags": interface.tags,
                "summary": interface.summary,
            }
            for case in new_cases:
                case.setdefault("source_interface", source_interface)
        current["cases"] = kept + new_cases
        current["generation_requirement"] = generated.get("generation_requirement", "")
        self.save_cases(current, spec_id)
        return current

    def find_case(self, case_id: str, spec_id: str | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        output = self.load_cases(spec_id)
        for case in output.get("cases", []):
            if str(case.get("case_id")) == case_id:
                return case, output["cases"]
        raise KeyError(f"测试用例不存在: {case_id}")

    @staticmethod
    def case_operation_id(case: dict[str, Any]) -> str:
        source = case.get("source_interface") or {}
        operation_id = str(source.get("operation_id", ""))
        if operation_id:
            return operation_id

        # 兼容早期已经保存、但没有 source_interface 的 AI 用例。
        case_id = str(case.get("case_id", ""))
        for case_type in ("positive", "negative", "boundary", "dependency"):
            marker = f"-{case_type}-"
            if marker in case_id:
                return case_id.split(marker, 1)[0]
        return ""

    @staticmethod
    def _new_id() -> str:
        from uuid import uuid4

        return uuid4().hex[:12]

    @staticmethod
    def _safe_id(value: str) -> str:
        return SAFE_ID.sub("_", value)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"数据文件不存在: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
