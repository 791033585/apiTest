import pytest

from common.variable_resolver import VariableResolver


def test_resolves_nested_values_and_preserves_exact_value_type():
    resolver = VariableResolver({"TOKEN": "demo-token", "USER_ID": 1})

    assert resolver.resolve({"Authorization": "Bearer {{TOKEN}}", "id": "{{USER_ID}}"}) == {
        "Authorization": "Bearer demo-token",
        "id": 1,
    }


def test_missing_variable_is_explicit():
    with pytest.raises(KeyError, match="变量未定义"):
        VariableResolver({}).resolve("{{MISSING}}")

