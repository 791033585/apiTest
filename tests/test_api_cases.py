from core.case_runner import CaseRunner

def test_excel_api_case(api_case, api_client, case_variables):
    result = CaseRunner(api_client, case_variables).run(api_case)

    assert result.response_text is not None
