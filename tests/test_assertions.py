import json

import pytest
from requests import Response

from core.assertions import assert_response


def make_response(status_code: int, body: dict) -> Response:
    response = Response()
    response.status_code = status_code
    response._content = json.dumps(body, ensure_ascii=False).encode("utf-8")
    response.encoding = "utf-8"
    return response


def test_status_code_and_jsonpath_assertions():
    response = make_response(200, {"code": 0, "msg": "登录成功"})

    assert_response(response, "status_code", 200)
    assert_response(response, "$.msg", "登录成功")


def test_contains_assertion():
    response = make_response(200, {"msg": "获取用户列表成功"})

    assert_response(response, "$.msg", "contains:用户列表")


def test_failed_assertion_contains_actual_value():
    response = make_response(200, {"msg": "登录失败"})

    with pytest.raises(AssertionError, match="actual"):
        assert_response(response, "$.msg", "登录成功")

