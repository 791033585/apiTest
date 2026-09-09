from dataclasses import replace
from typing import Any

from common.variable_resolver import VariableResolver
from core.assertions import assert_response
from core.extractor import extract_variables
from core.assertion_models import AssertionRule
from core.models import ApiCase, ExecutionResult
from core.request_client import RequestClient


class CaseRunner:
    def __init__(self, client: RequestClient, variables: dict[str, Any] | None = None):
        self.client = client
        self.variables = variables if variables is not None else {}

    def run(self, case: ApiCase) -> ExecutionResult:
        resolved_case = self._resolve_case(case)
        response = self.client.request(resolved_case)
        extracted = extract_variables(response, resolved_case.extract, resolved_case.extract_rules)
        assert_response(
            response,
            resolved_case.check,
            resolved_case.expected,
            resolved_case.assertions,
        )
        self.variables.update(extracted)
        try:
            response_json = response.json()
        except ValueError:
            response_json = None
        return ExecutionResult(
            case=resolved_case,
            status_code=response.status_code,
            response_text=response.text,
            response_json=response_json,
            extracted=extracted,
        )

    def _resolve_case(self, case: ApiCase) -> ApiCase:
        resolver = VariableResolver(self.variables)
        assertions = [
            AssertionRule(
                target=rule.target,
                path=resolver.resolve(rule.path),
                operator=rule.operator,
                expected=resolver.resolve(rule.expected),
            )
            for rule in case.assertions
        ]
        return replace(
            case,
            path=resolver.resolve(case.path),
            headers=resolver.resolve(case.headers),
            params=resolver.resolve(case.params),
            data=resolver.resolve(case.data),
            json_body=resolver.resolve(case.json_body),
            files=resolver.resolve(case.files),
            assertions=assertions,
        )
