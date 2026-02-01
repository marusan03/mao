"""Test AgentExecutor"""
import pytest
import os

from mao.orchestrator.agent_executor import AgentExecutor


class TestAgentExecutor:
    """Test AgentExecutor functionality"""

    def test_executor_initialization_with_key(self, mock_anthropic_api_key):
        """Test AgentExecutor initialization with API key"""
        executor = AgentExecutor()
        assert executor is not None
        assert executor.api_key == "sk-ant-test-mock-key-12345"

    def test_executor_initialization_without_key(self, no_anthropic_api_key):
        """Test AgentExecutor initialization without API key"""
        executor = AgentExecutor()
        assert executor is not None
        assert executor.api_key is None

    def test_executor_initialization_with_explicit_key(self):
        """Test AgentExecutor initialization with explicit API key"""
        executor = AgentExecutor(api_key="sk-ant-explicit-key")
        assert executor.api_key == "sk-ant-explicit-key"

    @pytest.mark.asyncio
    async def test_execute_requires_api_key(self, no_anthropic_api_key):
        """Test execute method requires API key"""
        executor = AgentExecutor()
        # Should fail or handle gracefully without API key
        with pytest.raises((ValueError, AttributeError, Exception)):
            await executor.execute(
                prompt="Test prompt",
                role="general",
                model="claude-sonnet-4-20250514"
            )

    def test_send_mac_notification(self):
        """Test macOS notification (should not crash)"""
        from mao.orchestrator.agent_executor import send_mac_notification
        # Should not raise exception even if notification fails
        send_mac_notification("Test", "Test message", sound=False)
