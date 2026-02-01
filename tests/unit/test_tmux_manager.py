"""Test TmuxManager"""
import pytest
import subprocess

from mao.orchestrator.tmux_manager import TmuxManager


class TestTmuxManager:
    """Test TmuxManager functionality"""

    def test_manager_initialization(self):
        """Test TmuxManager initialization"""
        manager = TmuxManager()
        assert manager is not None
        assert manager.session_name == "mao"
        assert manager.use_grid_layout is False

    def test_manager_initialization_with_grid(self):
        """Test TmuxManager initialization with grid layout"""
        manager = TmuxManager(use_grid_layout=True)
        assert manager.use_grid_layout is True

    def test_is_tmux_available(self):
        """Test checking if tmux is available"""
        manager = TmuxManager()
        # Should return True or False, not raise exception
        result = manager.is_tmux_available()
        assert isinstance(result, bool)

    @pytest.mark.skipif(
        not TmuxManager().is_tmux_available(),
        reason="tmux not available"
    )
    def test_session_exists(self):
        """Test checking if session exists"""
        manager = TmuxManager(session_name="test-mao-pytest")
        # Should return False for non-existent session
        assert manager.session_exists() is False

    @pytest.mark.skipif(
        not TmuxManager().is_tmux_available(),
        reason="tmux not available"
    )
    def test_create_and_destroy_session(self):
        """Test creating and destroying session"""
        manager = TmuxManager(session_name="test-mao-pytest")

        # Clean up any existing session
        manager.destroy_session()

        # Create session
        result = manager.create_session()
        assert result is True
        assert manager.session_exists() is True

        # Destroy session
        manager.destroy_session()
        assert manager.session_exists() is False

    @pytest.mark.skipif(
        not TmuxManager().is_tmux_available(),
        reason="tmux not available"
    )
    def test_create_grid_session(self):
        """Test creating 3x3 grid session"""
        manager = TmuxManager(session_name="test-mao-grid", use_grid_layout=True)

        # Clean up any existing session
        manager.destroy_session()

        # Create grid session
        result = manager.create_session_with_grid()
        assert result is True

        # Check that 9 panes were created
        panes_output = subprocess.run(
            ["tmux", "list-panes", "-t", "test-mao-grid:0"],
            capture_output=True,
            text=True
        )
        pane_count = len(panes_output.stdout.strip().split('\n'))
        assert pane_count == 9, f"Expected 9 panes, got {pane_count}"

        # Check grid_panes dictionary
        assert len(manager.grid_panes) == 9
        assert "manager" in manager.grid_panes
        assert "worker-1" in manager.grid_panes
        assert "worker-8" in manager.grid_panes

        # Clean up
        manager.destroy_session()

    @pytest.mark.skipif(
        not TmuxManager().is_tmux_available(),
        reason="tmux not available"
    )
    def test_session_already_exists(self):
        """Test creating session when it already exists"""
        manager = TmuxManager(session_name="test-mao-exist")

        # Clean up
        manager.destroy_session()

        # Create first time
        manager.create_session()

        # Create second time (should still return True)
        result = manager.create_session()
        assert result is True

        # Clean up
        manager.destroy_session()
