import json
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font

from core.models import ApiCase


CASE_COLUMNS = [
    "id", "module", "feature", "story", "title", "method", "path",
    "headers", "params", "data", "json", "files", "check", "expected",
    "extract", "sql_check", "assertions", "extracts", "depends_on",
    "case_type", "priority", "notes", "enabled",
]


class ExcelCaseWriter:
    @classmethod
    def write(cls, cases: list[ApiCase], file_path: str | Path, sheet_name: str = "api_cases") -> Path:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet_name
        worksheet.append(CASE_COLUMNS)
        for cell in worksheet[1]:
            cell.font = Font(bold=True)
        worksheet.freeze_panes = "A2"

        for case in cases:
            worksheet.append([
                case.case_id,
                case.module,
                case.feature,
                case.story,
                case.title,
                case.method,
                case.path,
                cls._json(case.headers),
                cls._json(case.params),
                cls._json(case.data),
                cls._json(case.json_body),
                cls._json(case.files),
                case.check,
                case.expected,
                case.extract,
                case.sql_check,
                cls._json([rule.to_dict() for rule in case.assertions]),
                cls._json([rule.to_dict() for rule in case.extract_rules]),
                cls._json(case.depends_on),
                case.case_type,
                case.priority,
                case.notes,
                case.enabled,
            ])

        for column_cells in worksheet.columns:
            width = min(max(len(str(cell.value or "")) for cell in column_cells) + 2, 60)
            worksheet.column_dimensions[column_cells[0].column_letter].width = width
        workbook.save(path)
        workbook.close()
        return path

    @staticmethod
    def _json(value: Any) -> str:
        if value is None or value == "":
            return "{}"
        return json.dumps(value, ensure_ascii=False)
