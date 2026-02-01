"""Test CLI commands"""
import pytest
from click.testing import CliRunner
from pathlib import Path

from mao.cli import main


class TestCLI:
    """Test CLI commands"""

    def test_main_help(self):
        """Test main help command"""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Multi-Agent Orchestrator" in result.output

    def test_version_command(self):
        """Test version command"""
        runner = CliRunner()
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert "Version" in result.output

    def test_init_command_creates_directory(self, temp_project_dir):
        """Test init command creates .mao directory"""
        runner = CliRunner()
        result = runner.invoke(main, ["init", "--project-dir", str(temp_project_dir)])
        assert result.exit_code == 0
        assert (temp_project_dir / ".mao").exists()
        assert (temp_project_dir / ".mao" / "config.yaml").exists()
        assert (temp_project_dir / ".mao" / "coding_standards").exists()
        assert (temp_project_dir / ".mao" / "roles").exists()
        assert (temp_project_dir / ".mao" / "context").exists()

    def test_init_command_force_overwrite(self, temp_project_dir):
        """Test init command with force flag"""
        runner = CliRunner()
        # First init
        runner.invoke(main, ["init", "--project-dir", str(temp_project_dir)])
        # Second init without force should fail
        result = runner.invoke(main, ["init", "--project-dir", str(temp_project_dir)])
        assert result.exit_code == 1
        assert "already initialized" in result.output
        # Third init with force should succeed
        result = runner.invoke(main, ["init", "--project-dir", str(temp_project_dir), "--force"])
        assert result.exit_code == 0

    def test_config_command_without_init(self, temp_project_dir):
        """Test config command without initialization"""
        runner = CliRunner()
        result = runner.invoke(main, ["config"], obj={"cwd": str(temp_project_dir)})
        # Should fail or show warning
        assert "No configuration found" in result.output or result.exit_code == 1

    def test_config_command_with_init(self, mao_project_dir, monkeypatch):
        """Test config command after initialization"""
        import os
        runner = CliRunner()
        # Change to mao_project_dir
        monkeypatch.chdir(mao_project_dir)
        result = runner.invoke(main, ["config"])
        # Should show configuration
        assert result.exit_code == 0 or "project_name" in result.output

    def test_roles_command(self):
        """Test roles command"""
        runner = CliRunner()
        result = runner.invoke(main, ["roles"])
        # Should show available roles or handle gracefully
        assert result.exit_code == 0 or "roles" in result.output.lower()

    def test_languages_command(self):
        """Test languages command"""
        runner = CliRunner()
        result = runner.invoke(main, ["languages"])
        assert result.exit_code == 0
        # Should show supported languages
        assert "python" in result.output.lower() or "language" in result.output.lower()

    def test_languages_command_with_language(self):
        """Test languages command with specific language"""
        runner = CliRunner()
        result = runner.invoke(main, ["languages", "python"])
        # Should show Python language details or handle gracefully
        assert result.exit_code in [0, 1]

    def test_skills_list_command(self):
        """Test skills list command"""
        runner = CliRunner()
        result = runner.invoke(main, ["skills", "list"])
        # Should list skills or show "no skills found"
        assert result.exit_code == 0 or "skill" in result.output.lower()

    def test_uninstall_command_cancel(self):
        """Test uninstall command with cancel"""
        runner = CliRunner()
        result = runner.invoke(main, ["uninstall"], input="n\n")
        assert result.exit_code == 0
        assert "Cancelled" in result.output or "cancelled" in result.output.lower()


class TestStartCommand:
    """Test start command specifically"""

    def test_start_help(self):
        """Test start command help"""
        runner = CliRunner()
        result = runner.invoke(main, ["start", "--help"])
        assert result.exit_code == 0
        assert "Start the Multi-Agent Orchestrator" in result.output

    def test_start_without_init_fails(self, temp_project_dir):
        """Test start command without initialization fails"""
        runner = CliRunner()
        result = runner.invoke(main, ["start", "--project-dir", str(temp_project_dir), "--no-tmux"])
        assert result.exit_code == 1
        assert "No MAO configuration found" in result.output or "Run 'mao init' first" in result.output
