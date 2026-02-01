"""End-to-end CLI command tests"""
import pytest
import subprocess
import tempfile
from pathlib import Path


class TestMAOCommands:
    """Test actual mao command execution"""

    @pytest.fixture
    def mao_bin(self):
        """Get path to mao executable"""
        # Try to find mao in venv
        venv_mao = Path(__file__).parent.parent.parent / "venv" / "bin" / "mao"
        if venv_mao.exists():
            return str(venv_mao)
        # Fall back to system mao
        return "mao"

    def test_mao_help(self, mao_bin):
        """Test mao --help command"""
        result = subprocess.run(
            [mao_bin, "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0
        assert "Multi-Agent Orchestrator" in result.stdout

    def test_mao_version(self, mao_bin):
        """Test mao version command"""
        result = subprocess.run(
            [mao_bin, "version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0
        assert "Version" in result.stdout

    def test_mao_version_flag(self, mao_bin):
        """Test mao --version flag"""
        result = subprocess.run(
            [mao_bin, "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0
        assert "Version" in result.stdout

    def test_mao_init(self, mao_bin):
        """Test mao init command"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [mao_bin, "init", "--project-dir", tmpdir],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert result.returncode == 0
            assert "Initialized" in result.stdout

            # Verify directory structure
            mao_dir = Path(tmpdir) / ".mao"
            assert mao_dir.exists()
            assert (mao_dir / "config.yaml").exists()

    def test_mao_config_without_init(self, mao_bin):
        """Test mao config without initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [mao_bin, "config"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir
            )
            # Should fail or show warning
            assert result.returncode != 0 or "No configuration found" in result.stdout

    def test_mao_languages(self, mao_bin):
        """Test mao languages command"""
        result = subprocess.run(
            [mao_bin, "languages"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0
        assert "python" in result.stdout.lower() or "language" in result.stdout.lower()

    def test_mao_roles(self, mao_bin):
        """Test mao roles command"""
        result = subprocess.run(
            [mao_bin, "roles"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0
        # Should show roles or handle gracefully

    def test_mao_skills_list(self, mao_bin):
        """Test mao skills list command"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize project first
            subprocess.run(
                [mao_bin, "init", "--project-dir", tmpdir],
                capture_output=True,
                timeout=10
            )

            result = subprocess.run(
                [mao_bin, "skills", "list"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir
            )
            assert result.returncode == 0

    def test_mao_start_without_init(self, mao_bin):
        """Test mao start without initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [mao_bin, "start", "--project-dir", tmpdir, "--no-tmux"],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert result.returncode != 0
            assert "No MAO configuration found" in result.stdout or "Run 'mao init' first" in result.stdout
