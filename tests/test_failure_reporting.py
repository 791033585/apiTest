import json

import pytest
from requests import Response

from core.assertions import assert_response


def test_failure_message_is_actionable():
    response = Response()
    response.status_code = 200
    response._content = json.dumps({"msg": "登录失败"}, ensure_ascii=False).encode("utf-8")
    response.encoding = "utf-8"

    with pytest.raises(AssertionError, match=r"path=\$\.msg.*登录成功.*登录失败"):
        assert_response(response, "$.msg", "登录成功")

