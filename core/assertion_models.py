from dataclasses import dataclass
from typing import Any


@dataclass
class AssertionRule:
    target: str
    path: str = ""
    operator: str = "eq"
    expected: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "path": self.path,
            "operator": self.operator,
            "expected": self.expected,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AssertionRule":
        if not isinstance(value, dict):
            raise ValueError("断言规则必须是对象")
        target = str(value.get("target", "json"))
        path = str(value.get("path", ""))
        operator = str(value.get("operator", "eq"))
        if target == "status_code" and not path:
            path = "status_code"
        return cls(target=target, path=path, operator=operator, expected=value.get("expected"))


@dataclass
class ExtractRule:
    name: str
    path: str
    source: str = "json"

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "source": self.source, "path": self.path}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ExtractRule":
        if not isinstance(value, dict):
            raise ValueError("提取规则必须是对象")
        name = str(value.get("name", "")).strip()
        path = str(value.get("path", "")).strip()
        if not name or not path:
            raise ValueError("提取规则必须包含 name 和 path")
        return cls(name=name, path=path, source=str(value.get("source", "json")))

