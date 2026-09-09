import json
import os
from typing import Any

import requests


class LlmConfigurationError(RuntimeError):
    pass


class LlmResponseError(RuntimeError):
    pass


class DeepSeekClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 60,
        max_tokens: int = 12000,
    ):
        if not api_key:
            raise LlmConfigurationError("未配置 DEEPSEEK_API_KEY")
        if not base_url.strip():
            raise LlmConfigurationError("未配置 DEEPSEEK_BASE_URL")
        if not model.strip():
            raise LlmConfigurationError("未配置 DEEPSEEK_MODEL")
        if timeout <= 0:
            raise LlmConfigurationError("DEEPSEEK_TIMEOUT 必须大于 0")
        if max_tokens <= 0:
            raise LlmConfigurationError("DEEPSEEK_MAX_TOKENS 必须大于 0")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens

    @classmethod
    def from_env(cls) -> "DeepSeekClient":
        try:
            timeout = float(os.getenv("DEEPSEEK_TIMEOUT", "60"))
            max_tokens = int(os.getenv("DEEPSEEK_MAX_TOKENS", "12000"))
        except ValueError as exc:
            raise LlmConfigurationError(
                "DEEPSEEK_TIMEOUT 和 DEEPSEEK_MAX_TOKENS 必须是数字"
            ) from exc
        return cls(
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            timeout=timeout,
            max_tokens=max_tokens,
        )

    def generate_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": self.max_tokens,
                    "response_format": {"type": "json_object"},
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise LlmResponseError("DeepSeek 请求失败，请检查网络、Base URL 或服务状态") from exc

        if response.status_code >= 400:
            raise LlmResponseError(f"DeepSeek 请求失败，状态码: {response.status_code}")

        try:
            payload = response.json()
        except (ValueError, TypeError) as exc:
            raise LlmResponseError("DeepSeek 返回体不是合法 JSON") from exc

        try:
            choice = payload["choices"][0]
            finish_reason = choice.get("finish_reason")
            if finish_reason == "length":
                raise LlmResponseError("DeepSeek 输出被 max_tokens 截断，请提高 DEEPSEEK_MAX_TOKENS")
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmResponseError("DeepSeek 返回缺少 choices.message.content") from exc

        if not isinstance(content, str) or not content.strip():
            raise LlmResponseError("DeepSeek 返回内容为空")
        try:
            result = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise LlmResponseError("DeepSeek 返回内容不是合法 JSON") from exc
        if not isinstance(result, dict):
            raise LlmResponseError("DeepSeek 返回 JSON 必须是对象")
        return result
