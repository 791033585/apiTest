import re
from collections.abc import Mapping
from typing import Any


VARIABLE_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][\w.-]*)\s*\}\}")


class VariableResolver:
    """Replace {{NAME}} placeholders in request data."""

    def __init__(self, variables: Mapping[str, Any] | None = None):
        self.variables = dict(variables or {})

    def resolve(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {key: self.resolve(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.resolve(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.resolve(item) for item in value)
        if not isinstance(value, str):
            return value

        exact = VARIABLE_PATTERN.fullmatch(value.strip())
        if exact:
            name = exact.group(1)
            if name not in self.variables:
                raise KeyError(f"变量未定义: {name}")
            return self.variables[name]

        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in self.variables:
                raise KeyError(f"变量未定义: {name}")
            return str(self.variables[name])

        return VARIABLE_PATTERN.sub(replace, value)

