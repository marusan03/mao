"""Tests for skill formatter"""
import pytest
from mao.orchestrator.skill_formatter import SkillFormatter
from mao.orchestrator.skill_manager import SkillDefinition


class TestSkillFormatter:
    """SkillFormatterのテスト"""

    def setup_method(self):
        """各テストの前に実行"""
        self.formatter = SkillFormatter()

    def test_format_skill_with_parameters(self):
        """パラメータ付きスキルのフォーマット"""
        skill_data = {
            "name": "test-skill",
            "description": "A test skill for testing",
            "parameters": [
                {
                    "name": "param1",
                    "type": "string",
                    "required": True,
                    "description": "First parameter",
                },
                {
                    "name": "param2",
                    "type": "string",
                    "required": False,
                    "default": "default_value",
                    "description": "Second parameter",
                },
            ],
        }
        skill = SkillDefinition(skill_data)

        result = self.formatter.format_skill_for_prompt(skill)

        assert "### /test-skill" in result
        assert "A test skill for testing" in result
        assert "param1" in result
        assert "param2" in result
        assert "Yes" in result  # required
        assert "default_value" in result

    def test_format_skill_with_choices(self):
        """choices付きパラメータのフォーマット"""
        skill_data = {
            "name": "role-skill",
            "description": "A skill with choices",
            "parameters": [
                {
                    "name": "role",
                    "type": "string",
                    "required": True,
                    "description": "Role to assign",
                    "choices": ["coder_backend", "reviewer", "tester"],
                },
            ],
        }
        skill = SkillDefinition(skill_data)

        result = self.formatter.format_skill_for_prompt(skill)

        assert "coder_backend" in result
        assert "reviewer" in result
        assert "tester" in result
        assert "Valid values" in result

    def test_summarize_sqlite_insert_script(self):
        """SQLite INSERTスクリプトの要約"""
        script = """
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO agents VALUES (?)", (agent_id,))
        conn.commit()
        """

        result = self.formatter._summarize_script(script)

        assert "SQLite INSERT" in result

    def test_summarize_sqlite_update_script(self):
        """SQLite UPDATEスクリプトの要約"""
        script = """
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE agents SET status = ? WHERE id = ?", (status, id))
        """

        result = self.formatter._summarize_script(script)

        assert "SQLite UPDATE" in result

    def test_summarize_file_write_script(self):
        """ファイル書き込みスクリプトの要約"""
        script = """
        import json
        with open(file_path, 'w') as f:
            json.dump(data, f)
        """

        result = self.formatter._summarize_script(script)

        assert "File write" in result

    def test_summarize_git_script(self):
        """Gitスクリプトの要約"""
        script = """
        import subprocess
        subprocess.run(["git ", "add", "."])
        subprocess.run(["git ", "commit", "-m", "test"])
        """

        result = self.formatter._summarize_script(script)

        assert "Git operations" in result

    def test_format_all_skills(self):
        """全スキルのフォーマット"""
        skills = [
            SkillDefinition({"name": "skill1", "description": "First skill"}),
            SkillDefinition({"name": "skill2", "description": "Second skill"}),
        ]

        result = self.formatter.format_all_skills(skills)

        assert "## Available Skills" in result
        assert "### /skill1" in result
        assert "### /skill2" in result
        assert "First skill" in result
        assert "Second skill" in result

    def test_format_all_skills_empty(self):
        """空のスキルリスト"""
        result = self.formatter.format_all_skills([])

        assert result == ""

    def test_format_skill_with_examples(self):
        """examples付きスキルのフォーマット"""
        skill_data = {
            "name": "example-skill",
            "description": "A skill with examples",
            "metadata": {
                "examples": [
                    {"command": "/example-skill --flag value"},
                    {"command": "/example-skill --other"},
                ]
            },
        }
        skill = SkillDefinition(skill_data)

        result = self.formatter.format_skill_for_prompt(skill)

        assert "**Examples**" in result
        assert "/example-skill --flag value" in result
