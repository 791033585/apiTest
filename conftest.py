import json
import os
import sys
from pathlib import Path
from threading import Thread

import pytest

PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.case_loader import ExcelCaseLoader
from core.request_client import RequestClient
from examples.demo_server import create_demo_server


def pytest_addoption(parser):
    parser.addoption(
        "--case-file",
        action="store",
        default=os.getenv("CASE_FILE", str(PROJECT_ROOT / "data" / "api_cases.xlsx")),
        help="待执行的 Excel 接口用例文件路径，默认使用 data/api_cases.xlsx",
    )
    parser.addoption(
        "--base-url",
        action="store",
        default=os.getenv("API_BASE_URL", ""),
        help="真实接口服务的 Base URL；不传时使用内置 Demo Server",
    )


def pytest_generate_tests(metafunc):
    """让测试文件可以通过参数切换任意兼容格式的 Excel 用例。"""
    if "api_case" not in metafunc.fixturenames:
        return

    case_file = Path(metafunc.config.getoption("--case-file"))
    cases = [case for case in ExcelCaseLoader.load(case_file) if case.enabled]
    if not cases:
        raise pytest.UsageError(f"Excel 中没有可执行的用例: {case_file}")
    metafunc.parametrize("api_case", cases, ids=lambda case: f"{case.case_id}-{case.title}")


@pytest.fixture(scope="session")
def demo_server():
    server = create_demo_server()
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture(scope="session")
def api_client(request, demo_server):
    base_url = request.config.getoption("--base-url")
    return RequestClient(base_url or demo_server.url)


@pytest.fixture(scope="session")
def case_variables():
    raw = os.getenv("CASE_VARIABLES", "{}")
    try:
        variables = json.loads(raw)
    except ValueError as exc:
        raise pytest.UsageError("CASE_VARIABLES 必须是合法 JSON") from exc
    if not isinstance(variables, dict):
        raise pytest.UsageError("CASE_VARIABLES 必须是 JSON 对象")
    return variables
