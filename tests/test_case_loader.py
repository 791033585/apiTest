from pathlib import Path

from core.case_loader import ExcelCaseLoader


DATA_FILE = Path(__file__).parents[1] / "data" / "api_cases.xlsx"


def test_excel_case_loader_reads_cases_and_disabled_case():
    cases = ExcelCaseLoader.load(DATA_FILE)

    assert len(cases) == 7
    assert cases[0].title == "管理员登录成功"
    assert cases[0].json_body["username"] == "admin"
    assert cases[-1].enabled is False

