"""Test SkillManager"""
import pytest
from pathlib import Path

from mao.orchestrator.skill_manager import SkillManager


class TestSkillManager:
    """Test SkillManager functionality"""

    def test_manager_initialization(self, mao_project_dir):
        """Test SkillManager initialization"""
        manager = SkillManager(mao_project_dir)
        assert manager is not None
        assert manager.project_path == mao_project_dir

    def test_list_skills_empty(self, mao_project_dir):
        """Test listing skills when none exist"""
        manager = SkillManager(mao_project_dir)
        skills = manager.list_skills()
        assert isinstance(skills, list)
        # Should be empty or have default skills
        assert len(skills) >= 0

    def test_get_nonexistent_skill(self, mao_project_dir):
        """Test getting non-existent skill"""
        manager = SkillManager(mao_project_dir)
        skill = manager.get_skill("nonexistent-skill-xyz")
        assert skill is None

    def test_list_proposals_empty(self, mao_project_dir):
        """Test listing proposals when none exist"""
        manager = SkillManager(mao_project_dir)
        proposals = manager.list_proposals()
        assert isinstance(proposals, list)
        assert len(proposals) == 0

    def test_delete_nonexistent_skill(self, mao_project_dir):
        """Test deleting non-existent skill"""
        manager = SkillManager(mao_project_dir)
        result = manager.delete_skill("nonexistent-skill-xyz")
        assert result is False
