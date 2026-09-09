import json

import pytest
import requests

from ai.llm_client import DeepSeekClient, LlmConfigurationError, LlmResponseError


def test_llm_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(LlmConfigurationError, match="DEEPSEEK_API_KEY"):
        DeepSeekClient.from_env()


def test_llm_client_uses_safe_defaults(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-key")
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)

    client = DeepSeekClient.from_env()

    assert client.base_url == "https://api.deepseek.com"
    assert client.model == "deepseek-v4-flash"
    assert client.max_tokens == 24000


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def make_client():
    return DeepSeekClient("test-only-key", "https://api.deepseek.com", "deepseek-v4-flash")


def test_llm_client_parses_json_response(monkeypatch):
    response = FakeResponse(
        payload={
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": json.dumps({"schema_version": "1.0", "cases": []})},
                }
            ]
        }
    )
    monkeypatch.setattr("ai.llm_client.requests.post", lambda *args, **kwargs: response)

    assert make_client().generate_json([])["schema_version"] == "1.0"


def test_llm_client_rejects_invalid_json(monkeypatch):
    response = FakeResponse(
        payload={
            "choices": [
                {"finish_reason": "stop", "message": {"content": "not-json"}}
            ]
        }
    )
    monkeypatch.setattr("ai.llm_client.requests.post", lambda *args, **kwargs: response)

    with pytest.raises(LlmResponseError, match="不是合法 JSON"):
        make_client().generate_json([])


def test_llm_client_rejects_truncated_output(monkeypatch):
    response = FakeResponse(
        payload={
            "choices": [
                {"finish_reason": "length", "message": {"content": "{}"}}
            ]
        }
    )
    monkeypatch.setattr("ai.llm_client.requests.post", lambda *args, **kwargs: response)

    with pytest.raises(LlmResponseError, match="截断"):
        make_client().generate_json([])


def test_llm_client_wraps_network_error(monkeypatch):
    def raise_network_error(*args, **kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr("ai.llm_client.requests.post", raise_network_error)

    with pytest.raises(LlmResponseError, match="网络"):
        make_client().generate_json([])
