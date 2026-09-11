from pathlib import Path


SKILL_DIR = Path(__file__).parent / "skills"
DEFAULT_SKILLS = (
    "openapi_analysis.md",
    "api_test_scenarios.md",
    "security_scenarios.md",
    "assertions.md",
    "dependencies.md",
    "output_contract.md",
)


def load_skills(skill_names: tuple[str, ...] = DEFAULT_SKILLS) -> str:
    """按固定顺序加载接口测试规则，避免 Prompt 依赖文件系统排序。"""
    sections = []
    for skill_name in skill_names:
        skill_path = SKILL_DIR / skill_name
        if not skill_path.is_file():
            raise FileNotFoundError(f"Skill 文件不存在: {skill_path}")
        content = skill_path.read_text(encoding="utf-8").strip()
        sections.append(f"### {skill_path.stem}\n{content}")
    return "\n\n".join(sections)
