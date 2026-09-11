from pathlib import Path

from ai.prompt_builder import build_messages
from ai.skill_loader import DEFAULT_SKILLS, load_skills
from core.openapi_importer import OpenApiImporter


OPENAPI_FILE = Path(__file__).parents[1] / "examples" / "openapi" / "demo_openapi.yaml"


def test_all_api_test_skills_are_loaded():
    skills = load_skills()

    for skill_name in DEFAULT_SKILLS:
        assert skill_name.removesuffix(".md") in skills


def test_prompt_contains_api_test_skills():
    imported = OpenApiImporter.from_file(OPENAPI_FILE).parse()
    messages = build_messages(imported)

    system_prompt = messages[0]["content"]
    assert "OpenAPI 分析 Skill" in system_prompt
    assert "接口测试场景 Skill" in system_prompt
    assert "接口安全测试场景 Skill" in system_prompt
    assert "接口断言 Skill" in system_prompt
    assert "接口依赖 Skill" in system_prompt
    assert "AI 输出契约 Skill" in system_prompt
    assert "过期 Token" in system_prompt
    assert "SQL 注入" in system_prompt
    assert "并发测试、容量测试和压力测试不属于" in system_prompt
