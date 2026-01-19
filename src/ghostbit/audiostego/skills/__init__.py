# src/audiostego/skills/__init__.py
"""Skills System for LLM integration"""

import re
from pathlib import Path
from typing import List, Dict, Optional

SKILLS_DIR = Path(__file__).parent


class Skill:
    """Represents a skill with documentation"""

    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.content = (path / "SKILL.md").read_text()
        self._parse_metadata()

    def _parse_metadata(self) -> None:
        """Parse metadata from skill markdown"""
        title_match = re.search(r"^# (.+)$", self.content, re.MULTILINE)
        self.title = title_match.group(1) if title_match else self.name

        lines = self.content.split("\n")
        self.description = ""
        in_desc = False
        for line in lines:
            if line.startswith("# "):
                in_desc = True
                continue
            if in_desc and line.strip() and not line.startswith("#"):
                self.description = line.strip()
                break

    def get_section(self, section_name: str) -> str:
        """Extract a specific section from the skill"""
        lines = self.content.split("\n")
        in_section = False
        section_content: list[str] = []
        section_level = 0

        for line in lines:
            if re.match(rf"^##+ {section_name}", line):
                in_section = True
                match = re.match(r"^(#+)", line)
                if match:
                    section_level = len(match.group(1))
                else:
                    section_level = 0
                continue

            if in_section and re.match(r"^#+", line):
                match = re.match(r"^(#+)", line)
                if match:
                    current_level = len(match.group(1))
                else:
                    current_level = 0
                if current_level <= section_level:
                    break

            if in_section:
                section_content.append(line)

        return "\n".join(section_content).strip()

    def get_all_sections(self) -> Dict[str, str]:
        """Get all sections as a dictionary"""
        sections = {}
        lines = self.content.split("\n")
        current_section = None
        section_content: list[str] = []

        for line in lines:
            if line.startswith("## "):
                if current_section:
                    sections[current_section] = "\n".join(section_content).strip()
                current_section = line[3:].strip()
                section_content = []
            elif current_section:
                section_content.append(line)

        if current_section:
            sections[current_section] = "\n".join(section_content).strip()

        return sections

    def get_examples(self) -> List[Dict[str, str]]:
        """Extract code examples from the skill"""
        examples = []

        pattern = r"```(\w+)?\n(.*?)```"
        matches = re.findall(pattern, self.content, re.DOTALL)

        for lang, code in matches:
            examples.append({"language": lang or "python", "code": code.strip()})

        return examples

    def __str__(self) -> str:
        return f"Skill(name='{self.name}', title='{self.title}')"


class SkillLoader:
    """Load and manage skills"""

    def __init__(self) -> None:
        self.skills_dir = SKILLS_DIR

    def list_skills(self) -> List[str]:
        """List all available skill names"""
        skills = []
        for item in self.skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                skill_file = item / "SKILL.md"
                if skill_file.exists():
                    skills.append(item.name)
        return sorted(skills)

    def load_skill(self, name: str) -> Skill:
        """Load a specific skill by name"""
        skill_path = self.skills_dir / name

        if not skill_path.exists():
            raise ValueError(
                f"Skill '{name}' not found. "
                f"Available: {', '.join(self.list_skills())}"
            )

        skill_file = skill_path / "SKILL.md"
        if not skill_file.exists():
            raise ValueError(f"SKILL.md not found in skill '{name}'")

        return Skill(name, skill_path)

    def get_all_skills(self) -> List[Skill]:
        """Get all available skills"""
        return [self.load_skill(name) for name in self.list_skills()]

    def get_llm_context(self, skill_names: Optional[List[str]] = None) -> str:
        """
        Get formatted context for LLM consumption.

        Args:
            skill_names: List of specific skills to include, or None for all

        Returns:
            Formatted markdown string with all skill content
        """
        if skill_names is None:
            skills = self.get_all_skills()
        else:
            skills = [self.load_skill(name) for name in skill_names]

        context = "# AudioStego Skills Documentation\n\n"
        context += "This documentation provides guidance for using AudioStego.\n\n"

        for skill in skills:
            context += "\n---\n\n"
            context += skill.content
            context += "\n\n"

        return context


def load_skill(name: str) -> Skill:
    """Load a skill by name"""
    loader = SkillLoader()
    return loader.load_skill(name)


def list_skills() -> List[str]:
    """List all available skills"""
    loader = SkillLoader()
    return loader.list_skills()


def get_llm_context(skill_names: Optional[List[str]] = None) -> str:
    """Get formatted context for LLM"""
    loader = SkillLoader()
    return loader.get_llm_context(skill_names)


__all__ = [
    "Skill",
    "SkillLoader",
    "load_skill",
    "list_skills",
    "get_llm_context",
    "SKILLS_DIR",
]
