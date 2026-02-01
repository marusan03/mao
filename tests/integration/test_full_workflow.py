"""Test full workflow integration"""
import pytest
from click.testing import CliRunner
from pathlib import Path

from mao.cli import main
from mao.orchestrator.project_loader import ProjectLoader
from mao.config import ConfigLoader


class TestFullWorkflow:
    """Test complete workflows"""

    def test_init_and_config_workflow(self, temp_project_dir):
        """Test initializing project and viewing config"""
        runner = CliRunner()

        # Step 1: Initialize project
        result = runner.invoke(main, ["init", "--project-dir", str(temp_project_dir)])
        assert result.exit_code == 0

        # Step 2: Verify .mao directory structure
        mao_dir = temp_project_dir / ".mao"
        assert mao_dir.exists()
        assert (mao_dir / "config.yaml").exists()
        assert (mao_dir / "coding_standards").exists()
        assert (mao_dir / "roles").exists()
        assert (mao_dir / "context").exists()
        assert (mao_dir / "context" / "architecture.md").exists()

        # Step 3: Load config programmatically
        loader = ProjectLoader(temp_project_dir)
        config = loader.load()
        assert config is not None
        assert config.project_name == "my-project"

    def test_language_and_standards_workflow(self):
        """Test language configuration workflow"""
        # Step 1: List available languages
        runner = CliRunner()
        result = runner.invoke(main, ["languages"])
        assert result.exit_code == 0

        # Step 2: Load language config programmatically
        loader = ConfigLoader()
        languages = loader.list_available_languages()
        assert "python" in languages

        # Step 3: Get specific language details
        python_config = loader.load_language_config("python")
        assert python_config is not None
        assert python_config.formatter is not None

    def test_skills_workflow(self, mao_project_dir):
        """Test skills management workflow"""
        runner = CliRunner()

        # Step 1: List skills (should be empty initially)
        result = runner.invoke(main, ["skills", "list"], obj={"cwd": str(mao_project_dir)})
        assert result.exit_code == 0

        # Step 2: List proposals (should be empty)
        result = runner.invoke(main, ["skills", "proposals"], obj={"cwd": str(mao_project_dir)})
        assert result.exit_code == 0

    def test_project_initialization_creates_gitignore(self, temp_project_dir):
        """Test that init creates/updates .gitignore"""
        runner = CliRunner()
        result = runner.invoke(main, ["init", "--project-dir", str(temp_project_dir)])
        assert result.exit_code == 0

        # Check .gitignore
        gitignore = temp_project_dir / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert ".mao/state.db" in content
        assert ".mao/*.log" in content

    def test_multiple_init_with_force(self, temp_project_dir):
        """Test multiple initialization with force flag"""
        runner = CliRunner()

        # First init
        result1 = runner.invoke(main, ["init", "--project-dir", str(temp_project_dir)])
        assert result1.exit_code == 0

        # Modify config
        config_file = temp_project_dir / ".mao" / "config.yaml"
        config_file.write_text("project_name: modified")

        # Second init without force should fail
        result2 = runner.invoke(main, ["init", "--project-dir", str(temp_project_dir)])
        assert result2.exit_code == 1

        # Config should still be modified
        assert "modified" in config_file.read_text()

        # Third init with force should succeed and reset config
        result3 = runner.invoke(main, ["init", "--project-dir", str(temp_project_dir), "--force"])
        assert result3.exit_code == 0

        # Config should be reset
        assert "my-project" in config_file.read_text()
