import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class EnvironmentConfig:
    name: str
    base_url: str
    headers: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)


def load_environment(
    file_path: str | Path,
    name: str | None = None,
    base_url_override: str | None = None,
) -> EnvironmentConfig:
    path = Path(file_path)
    with path.open("r", encoding="utf-8") as file:
        environments = yaml.safe_load(file) or {}

    environment_name = name or os.getenv("API_ENV", "local")
    if environment_name not in environments:
        raise KeyError(f"环境不存在: {environment_name}")

    values = environments[environment_name] or {}
    base_url = base_url_override or os.getenv("API_BASE_URL") or values.get("base_url", "")
    if not base_url:
        raise ValueError(f"环境 {environment_name} 未配置 base_url")

    return EnvironmentConfig(
        name=environment_name,
        base_url=base_url,
        headers=values.get("headers", {}) or {},
        variables=values.get("variables", {}) or {},
    )

