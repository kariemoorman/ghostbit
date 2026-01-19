#!/usr/bin/env python3
import pytest
from pathlib import Path
import ghostbit.audiostego.skills as skills_module
from ghostbit.audiostego.skills import (
    Skill,
    SkillLoader,
    load_skill,
    list_skills,
    get_llm_context,
    SKILLS_DIR,
)


class TestSkill:
    """Test suite for Skill class"""

    @pytest.fixture
    def sample_skill_content(self) -> str:
        """Sample skill markdown content"""
        # No leading whitespace!
        return """# Test Skill

This is a test skill for unit testing.

## Overview

This section contains an overview of the skill.

## Installation

Install the required packages:
````bash
pip install test-package
````

## Usage

Here's how to use this skill:
````python
def example():
    print("Hello, World!")
````

## Advanced Features

### Subsection 1

Some advanced content here.

### Subsection 2

More advanced content.

## Examples
````python
# Example 1
result = do_something()
````
````javascript
// Example 2
console.log("test");
````
"""

    @pytest.fixture
    def temp_skill_dir(self, tmp_path: Path, sample_skill_content: str) -> Path:
        """Create a temporary skill directory"""
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(sample_skill_content)
        return skill_dir

    def test_skill_initialization(
        self, temp_skill_dir: Path, sample_skill_content: str
    ) -> None:
        """Test Skill object initialization"""
        skill = Skill("test_skill", temp_skill_dir)

        assert skill.name == "test_skill"
        assert skill.path == temp_skill_dir
        assert skill.content == sample_skill_content
        assert skill.title == "Test Skill"
        assert "test skill for unit testing" in skill.description.lower()

    def test_skill_metadata_parsing(self, temp_skill_dir: Path) -> None:
        """Test metadata parsing from skill markdown"""
        skill = Skill("test_skill", temp_skill_dir)

        assert skill.title == "Test Skill"
        assert skill.description
        assert len(skill.description) > 0

    def test_skill_metadata_no_title(self, tmp_path: Path) -> None:
        """Test metadata parsing when no title is present"""
        skill_dir = tmp_path / "no_title_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("No title here\n\nJust content")

        skill = Skill("no_title_skill", skill_dir)
        assert skill.title == "no_title_skill"

    def test_get_section(self, temp_skill_dir: Path) -> None:
        """Test extracting a specific section"""
        skill = Skill("test_skill", temp_skill_dir)

        overview = skill.get_section("Overview")
        assert "overview of the skill" in overview.lower()

        installation = skill.get_section("Installation")
        assert "pip install" in installation.lower()

        usage = skill.get_section("Usage")
        assert "how to use" in usage.lower()

    def test_get_section_not_found(self, temp_skill_dir: Path) -> None:
        """Test getting a section that doesn't exist"""
        skill = Skill("test_skill", temp_skill_dir)

        nonexistent = skill.get_section("Nonexistent Section")
        assert nonexistent == ""

    def test_get_section_with_subsections(self, temp_skill_dir: Path) -> None:
        """Test extracting section with subsections"""
        skill = Skill("test_skill", temp_skill_dir)

        advanced = skill.get_section("Advanced Features")
        assert "Subsection 1" in advanced
        assert "Subsection 2" in advanced
        assert "advanced content" in advanced.lower()

    def test_get_all_sections(self, temp_skill_dir: Path) -> None:
        """Test getting all sections as dictionary"""
        skill = Skill("test_skill", temp_skill_dir)

        sections = skill.get_all_sections()

        assert isinstance(sections, dict)
        assert "Overview" in sections
        assert "Installation" in sections
        assert "Usage" in sections
        assert "Advanced Features" in sections
        assert "Examples" in sections
        assert "overview" in sections["Overview"].lower()
        assert "pip install" in sections["Installation"].lower()

    def test_get_examples(self, temp_skill_dir: Path) -> None:
        """Test extracting code examples"""
        skill = Skill("test_skill", temp_skill_dir)

        examples = skill.get_examples()

        assert isinstance(examples, list)
        assert len(examples) == 4

        bash_examples = [ex for ex in examples if ex["language"] == "bash"]
        assert len(bash_examples) == 1
        assert "pip install" in bash_examples[0]["code"]

        python_examples = [ex for ex in examples if ex["language"] == "python"]
        assert len(python_examples) == 2

        js_examples = [ex for ex in examples if ex["language"] == "javascript"]
        assert len(js_examples) == 1
        assert "console.log" in js_examples[0]["code"]

    def test_get_examples_no_language_specified(self, tmp_path: Path) -> None:
        """Test extracting examples when no language is specified"""
        skill_dir = tmp_path / "no_lang_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# Test\n\n```\ncode without language\n```")

        skill = Skill("no_lang_skill", skill_dir)
        examples = skill.get_examples()

        assert len(examples) == 1
        assert examples[0]["language"] == "python"
        assert examples[0]["code"] == "code without language"

    def test_skill_str_representation(self, temp_skill_dir: Path) -> None:
        """Test string representation of Skill"""
        skill = Skill("test_skill", temp_skill_dir)

        skill_str = str(skill)
        assert "test_skill" in skill_str
        assert "Test Skill" in skill_str


class TestSkillLoader:
    """Test suite for SkillLoader class"""

    @pytest.fixture
    def temp_skills_dir(self, tmp_path: Path) -> Path:
        """Create temporary skills directory with multiple skills"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        skill1_dir = skills_dir / "skill1"
        skill1_dir.mkdir()
        (skill1_dir / "SKILL.md").write_text("# Skill 1\n\nFirst skill")

        skill2_dir = skills_dir / "skill2"
        skill2_dir.mkdir()
        (skill2_dir / "SKILL.md").write_text("# Skill 2\n\nSecond skill")

        invalid_dir = skills_dir / "invalid"
        invalid_dir.mkdir()

        hidden_dir = skills_dir / "_hidden"
        hidden_dir.mkdir()
        (hidden_dir / "SKILL.md").write_text("# Hidden\n\nHidden skill")

        return skills_dir

    @pytest.fixture
    def skill_loader(self, temp_skills_dir: Path, monkeypatch) -> SkillLoader:
        """Create SkillLoader with temp directory"""
        loader = SkillLoader()
        monkeypatch.setattr(loader, "skills_dir", temp_skills_dir)
        return loader

    def test_skill_loader_initialization(self) -> None:
        """Test SkillLoader initialization"""
        loader = SkillLoader()
        assert loader.skills_dir == SKILLS_DIR
        assert loader.skills_dir.exists()

    def test_list_skills(self, skill_loader: SkillLoader) -> None:
        """Test listing available skills"""
        skills = skill_loader.list_skills()

        assert isinstance(skills, list)
        assert len(skills) == 2
        assert "skill1" in skills
        assert "skill2" in skills
        assert "invalid" not in skills
        assert "_hidden" not in skills
        assert skills == sorted(skills)

    def test_load_skill(self, skill_loader: SkillLoader) -> None:
        """Test loading a specific skill"""
        skill = skill_loader.load_skill("skill1")

        assert isinstance(skill, Skill)
        assert skill.name == "skill1"
        assert skill.title == "Skill 1"
        assert "First skill" in skill.content

    def test_load_skill_not_found(self, skill_loader: SkillLoader) -> None:
        """Test loading a skill that doesn't exist"""
        with pytest.raises(ValueError) as exc_info:
            skill_loader.load_skill("nonexistent")

        assert "not found" in str(exc_info.value).lower()
        assert "skill1" in str(exc_info.value)

    def test_load_skill_missing_skill_file(
        self, skill_loader: SkillLoader, tmp_path: Path
    ) -> None:
        """Test loading a skill directory without SKILL.md"""
        invalid_dir = skill_loader.skills_dir / "no_skill_md"
        invalid_dir.mkdir()

        with pytest.raises(ValueError) as exc_info:
            skill_loader.load_skill("no_skill_md")

        assert "SKILL.md not found" in str(exc_info.value)

    def test_get_all_skills(self, skill_loader: SkillLoader) -> None:
        """Test getting all skills"""
        skills = skill_loader.get_all_skills()

        assert isinstance(skills, list)
        assert len(skills) == 2
        assert all(isinstance(s, Skill) for s in skills)
        assert {s.name for s in skills} == {"skill1", "skill2"}

    def test_get_llm_context_all_skills(self, skill_loader: SkillLoader) -> None:
        """Test getting LLM context for all skills"""
        context = skill_loader.get_llm_context()

        assert isinstance(context, str)
        assert "AudioStego Skills Documentation" in context
        assert "Skill 1" in context
        assert "Skill 2" in context
        assert "First skill" in context
        assert "Second skill" in context
        assert "---" in context

    def test_get_llm_context_specific_skills(self, skill_loader: SkillLoader) -> None:
        """Test getting LLM context for specific skills"""
        context = skill_loader.get_llm_context(skill_names=["skill1"])

        assert "Skill 1" in context
        assert "First skill" in context
        assert "Skill 2" not in context
        assert "Second skill" not in context

    def test_get_llm_context_multiple_specific_skills(
        self, skill_loader: SkillLoader
    ) -> None:
        """Test getting LLM context for multiple specific skills"""
        context = skill_loader.get_llm_context(skill_names=["skill1", "skill2"])

        assert "Skill 1" in context
        assert "Skill 2" in context
        assert "First skill" in context
        assert "Second skill" in context

    def test_get_llm_context_invalid_skill(self, skill_loader: SkillLoader) -> None:
        """Test getting LLM context with invalid skill name"""
        with pytest.raises(ValueError):
            skill_loader.get_llm_context(skill_names=["nonexistent"])


class TestModuleFunctions:
    """Test suite for module-level convenience functions"""

    @pytest.fixture
    def temp_skills_dir(self, tmp_path: Path, monkeypatch) -> Path:
        """Create temporary skills directory"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        skill_dir = skills_dir / "test_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test\n\nTest skill")

        monkeypatch.setattr(skills_module, "SKILLS_DIR", skills_dir)
        return skills_dir

    def test_load_skill_function(self, temp_skills_dir: Path) -> None:
        """Test module-level load_skill function"""
        skill = load_skill("test_skill")

        assert isinstance(skill, Skill)
        assert skill.name == "test_skill"

    def test_list_skills_function(self, temp_skills_dir: Path) -> None:
        """Test module-level list_skills function"""
        skills = list_skills()

        assert isinstance(skills, list)
        assert "test_skill" in skills

    def test_get_llm_context_function(self, temp_skills_dir: Path) -> None:
        """Test module-level get_llm_context function"""
        context = get_llm_context()

        assert isinstance(context, str)
        assert "AudioStego Skills Documentation" in context
        assert "Test skill" in context

    def test_get_llm_context_function_specific_skills(
        self, temp_skills_dir: Path
    ) -> None:
        """Test module-level get_llm_context with specific skills"""
        context = get_llm_context(skill_names=["test_skill"])

        assert "Test skill" in context


@pytest.mark.integration
class TestSkillsIntegration:
    """Integration tests for skills system"""

    def test_real_skills_directory_exists(self) -> None:
        """Test that the real skills directory exists"""
        assert SKILLS_DIR.exists()
        assert SKILLS_DIR.is_dir()

    def test_can_list_real_skills(self) -> None:
        """Test listing skills from actual skills directory"""
        loader = SkillLoader()
        skills = loader.list_skills()

        assert isinstance(skills, list)

    def test_load_real_skill_if_exists(self) -> None:
        """Test loading a real skill if any exist"""
        loader = SkillLoader()
        skills = loader.list_skills()

        if skills:
            skill = loader.load_skill(skills[0])
            assert isinstance(skill, Skill)
            assert skill.name == skills[0]
            assert skill.content
            assert skill.title

    def test_get_llm_context_from_real_skills(self) -> None:
        """Test getting LLM context from real skills"""
        context = get_llm_context()

        assert isinstance(context, str)
        assert "AudioStego Skills Documentation" in context


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_skill_with_empty_content(self, tmp_path: Path) -> None:
        """Test skill with empty SKILL.md"""
        skill_dir = tmp_path / "empty_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("")

        skill = Skill("empty_skill", skill_dir)
        assert skill.content == ""
        assert skill.title == "empty_skill"
        assert skill.description == ""

    def test_skill_with_only_code_blocks(self, tmp_path: Path) -> None:
        """Test skill with only code blocks"""
        skill_dir = tmp_path / "code_only_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""```python
print("hello")
```
```bash
echo "world"
````""")

        skill = Skill("code_only_skill", skill_dir)
        examples = skill.get_examples()
        assert len(examples) == 2

    def test_skill_get_section_basic(self, tmp_path: Path) -> None:
        """Test basic section extraction"""
        skill_dir = tmp_path / "section_skill"
        skill_dir.mkdir()
        content = """# My Skill

## Introduction

This is the introduction text.
It has multiple lines.

## Usage

Here's how to use it:
- Step 1
- Step 2

## Advanced

Advanced content here.
"""
        (skill_dir / "SKILL.md").write_text(content)

        skill = Skill("section_skill", skill_dir)

        intro = skill.get_section("Introduction")
        assert "introduction text" in intro.lower()
        assert "multiple lines" in intro.lower()

        usage = skill.get_section("Usage")
        assert "how to use" in usage.lower()
        assert "Step 1" in usage

        advanced = skill.get_section("Advanced")
        assert "Advanced content" in advanced

    def test_skill_code_examples_extraction(self, tmp_path: Path) -> None:
        """Test that code examples are extracted correctly"""
        skill_dir = tmp_path / "code_skill"
        skill_dir.mkdir()
        content = """# Code Examples
## Python Example
```python
def hello():
    print("world")
```

## Bash Example
```bash
echo "test"
```
"""
        (skill_dir / "SKILL.md").write_text(content)

        skill = Skill("code_skill", skill_dir)
        examples = skill.get_examples()

        assert len(examples) == 2

        python_ex = [ex for ex in examples if ex["language"] == "python"]
        assert len(python_ex) == 1
        assert "def hello" in python_ex[0]["code"]

        bash_ex = [ex for ex in examples if ex["language"] == "bash"]
        assert len(bash_ex) == 1
        assert "echo" in bash_ex[0]["code"]

    def test_skill_section_with_code_blocks(self, tmp_path: Path) -> None:
        """Test extracting section that contains code blocks"""
        skill_dir = tmp_path / "mixed_skill"
        skill_dir.mkdir()
        content = """# Mixed Content

## Installation

Install the package:
```bash
pip install mypackage
```

That's all you need!

## Next Section

Different content here.
"""
        (skill_dir / "SKILL.md").write_text(content)

        skill = Skill("mixed_skill", skill_dir)

        install = skill.get_section("Installation")

        assert "Install the package" in install
        assert "pip install" in install or "```bash" in install
        assert "That's all" in install

    def test_get_all_sections_empty_skill(self, tmp_path: Path) -> None:
        """Test getting all sections from skill without sections"""
        skill_dir = tmp_path / "no_sections_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Title\n\nJust content, no sections")

        skill = Skill("no_sections_skill", skill_dir)
        sections = skill.get_all_sections()
        assert isinstance(sections, dict)
        assert len(sections) == 0

    def test_special_characters_in_skill_name(self, tmp_path: Path) -> None:
        """Test skill with special characters in directory name"""
        skill_dir = tmp_path / "skill-with-dashes"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill With Dashes\n\nContent")

        skill = Skill("skill-with-dashes", skill_dir)
        assert skill.name == "skill-with-dashes"
        assert skill.title == "Skill With Dashes"

    def test_unicode_in_skill_content(self, tmp_path: Path) -> None:
        """Test skill with unicode characters"""
        skill_dir = tmp_path / "unicode_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# 技能\n\n日本語コンテンツ 🎵")

        skill = Skill("unicode_skill", skill_dir)
        assert "技能" in skill.title
        assert "日本語" in skill.content
        assert "🎵" in skill.content
