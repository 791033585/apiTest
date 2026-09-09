from typing import Any
from urllib.parse import urljoin

import requests

from common.logger import get_logger
from core.models import ApiCase


logger = get_logger(__name__)


class RequestExecutionError(RuntimeError):
    """Raised when an HTTP request cannot be sent."""


class RequestClient:
    def __init__(
        self,
        base_url: str,
        default_headers: dict[str, Any] | None = None,
        timeout: float = 10,
        session: requests.Session | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_headers = dict(default_headers or {})
        self.timeout = timeout
        self.session = session or requests.Session()

    def request(self, case: ApiCase) -> requests.Response:
        url = urljoin(f"{self.base_url}/", case.path.lstrip("/"))
        headers = {**self.default_headers, **case.headers}
        kwargs: dict[str, Any] = {
            "headers": headers,
            "params": case.params or None,
            "timeout": self.timeout,
        }
        if case.data:
            kwargs["data"] = case.data
        if case.json_body:
            kwargs["json"] = case.json_body
        if case.files:
            kwargs["files"] = case.files

        logger.info("请求 %s %s", case.method, url)
        logger.info("请求参数: %s", {key: value for key, value in kwargs.items() if key != "timeout"})
        try:
            response = self.session.request(case.method, url, **kwargs)
        except requests.RequestException as exc:
            raise RequestExecutionError(f"请求失败 {case.method} {url}: {exc}") from exc

        logger.info("响应状态码: %s", response.status_code)
        logger.info("响应内容: %s", response.text[:1000])
        return response

