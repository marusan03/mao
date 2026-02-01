"""Test TaskDispatcher"""
import pytest

from mao.orchestrator.task_dispatcher import TaskDispatcher


class TestTaskDispatcher:
    """Test TaskDispatcher functionality"""

    def test_dispatcher_initialization(self):
        """Test TaskDispatcher initialization"""
        dispatcher = TaskDispatcher()
        assert dispatcher is not None
        assert hasattr(dispatcher, "roles")

    def test_load_roles(self):
        """Test loading agent roles"""
        dispatcher = TaskDispatcher()
        assert len(dispatcher.roles) > 0
        # Should have various roles defined
        assert any(role in dispatcher.roles for role in ["tester", "coder_backend", "planner"])

    def test_role_structure(self):
        """Test role configuration structure"""
        dispatcher = TaskDispatcher()
        for role_name, role_config in dispatcher.roles.items():
            assert "display_name" in role_config
            assert "responsibilities" in role_config
            assert isinstance(role_config["responsibilities"], list)

    def test_build_agent_prompt(self):
        """Test building agent prompt"""
        dispatcher = TaskDispatcher()
        # Test if dispatcher can build a prompt for a role
        task = {
            "id": "test-task-1",
            "description": "Write unit tests for the login function"
        }
        prompt = dispatcher.build_agent_prompt("tester", task)
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0
