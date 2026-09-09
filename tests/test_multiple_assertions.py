from core.assertion_models import AssertionRule, ExtractRule
from core.case_runner import CaseRunner
from core.models import ApiCase


def test_case_runner_executes_multiple_assertions_and_extracts(api_client, case_variables):
    case = ApiCase(
        case_id="ai-login-001",
        module="认证",
        feature="登录",
        story="AI 生成场景",
        title="登录并提取 Token",
        method="POST",
        path="/login",
        json_body={"username": "admin", "password": "123456"},
        assertions=[
            AssertionRule("status_code", operator="eq", expected=200),
            AssertionRule("json", path="$.code", operator="eq", expected=0),
            AssertionRule("json", path="$.msg", operator="eq", expected="登录成功"),
        ],
        extract_rules=[ExtractRule("TOKEN", "$.data.token")],
    )

    result = CaseRunner(api_client, case_variables).run(case)

    assert result.status_code == 200
    assert case_variables["TOKEN"] == "demo-token"

