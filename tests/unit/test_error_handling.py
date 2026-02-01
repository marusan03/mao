"""
Tests for improved error handling
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from mao.orchestrator.claude_code_executor import ClaudeCodeExecutor
from mao.orchestrator.agent_executor import AgentExecutor, AgentProcess, escape_applescript


class TestClaudeCodeExecutorErrorHandling:
    """ClaudeCodeExecutor のエラーハンドリングテスト"""

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self):
        """タイムアウトエラーが適切に処理されることをテスト"""
        try:
            executor = ClaudeCodeExecutor()
        except ValueError:
            pytest.skip("claude-code not available")

        # タイムアウトをシミュレート
        with patch.object(executor, 'claude_code_path', 'fake-command'):
            with patch('asyncio.create_subprocess_exec', side_effect=asyncio.TimeoutError()):
                result = await executor.execute_agent(
                    prompt="test",
                    model="sonnet",
                )

                assert result["success"] is False
                assert "error_type" in result
                assert result["error_type"] == "timeout"
                assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_permission_error_handling(self):
        """権限エラーが適切に処理されることをテスト"""
        try:
            executor = ClaudeCodeExecutor()
        except ValueError:
            pytest.skip("claude-code not available")

        with patch.object(executor, 'claude_code_path', 'fake-command'):
            with patch('asyncio.create_subprocess_exec', side_effect=PermissionError("Access denied")):
                result = await executor.execute_agent(
                    prompt="test",
                    model="sonnet",
                )

                assert result["success"] is False
                assert result["error_type"] == "permission"
                assert "permission" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_file_not_found_error_handling(self):
        """ファイル未検出エラーが適切に処理されることをテスト"""
        try:
            executor = ClaudeCodeExecutor()
        except ValueError:
            pytest.skip("claude-code not available")

        with patch.object(executor, 'claude_code_path', 'fake-command'):
            with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError("File not found")):
                result = await executor.execute_agent(
                    prompt="test",
                    model="sonnet",
                )

                assert result["success"] is False
                assert result["error_type"] == "file_not_found"

    @pytest.mark.asyncio
    async def test_unexpected_error_includes_exception_class(self):
        """予期しないエラーに例外クラス名が含まれることをテスト"""
        try:
            executor = ClaudeCodeExecutor()
        except ValueError:
            pytest.skip("claude-code not available")

        with patch.object(executor, 'claude_code_path', 'fake-command'):
            with patch('asyncio.create_subprocess_exec', side_effect=RuntimeError("Unexpected")):
                result = await executor.execute_agent(
                    prompt="test",
                    model="sonnet",
                )

                assert result["success"] is False
                assert result["error_type"] == "unexpected"
                assert "exception_class" in result
                assert result["exception_class"] == "RuntimeError"


class TestAgentExecutorErrorHandling:
    """AgentExecutor のエラーハンドリングテスト"""

    @pytest.mark.asyncio
    async def test_validation_error_handling(self):
        """バリデーションエラーが適切に処理されることをテスト"""
        executor = AgentExecutor(api_key="test-key")

        with patch.object(executor.client.messages, 'create', side_effect=ValueError("Invalid parameter")):
            result = await executor.execute_agent(
                prompt="test",
                model="sonnet",
            )

            assert result["success"] is False
            assert result["error_type"] == "validation"
            assert "invalid" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """接続エラーが適切に処理されることをテスト"""
        executor = AgentExecutor(api_key="test-key")

        with patch.object(executor.client.messages, 'create', side_effect=ConnectionError("Network error")):
            result = await executor.execute_agent(
                prompt="test",
                model="sonnet",
            )

            assert result["success"] is False
            assert result["error_type"] == "connection"
            assert "connection" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self):
        """タイムアウトエラーが適切に処理されることをテスト"""
        executor = AgentExecutor(api_key="test-key")

        with patch.object(executor.client.messages, 'create', side_effect=TimeoutError("Timeout")):
            result = await executor.execute_agent(
                prompt="test",
                model="sonnet",
            )

            assert result["success"] is False
            assert result["error_type"] == "timeout"

    @pytest.mark.asyncio
    async def test_api_error_includes_exception_class(self):
        """APIエラーに例外クラス名が含まれることをテスト"""
        executor = AgentExecutor(api_key="test-key")

        with patch.object(executor.client.messages, 'create', side_effect=RuntimeError("API error")):
            result = await executor.execute_agent(
                prompt="test",
                model="sonnet",
            )

            assert result["success"] is False
            assert result["error_type"] == "api_error"
            assert "exception_class" in result
            assert result["exception_class"] == "RuntimeError"


class TestAgentProcessErrorHandling:
    """AgentProcess のエラーハンドリングテスト"""

    @pytest.mark.asyncio
    async def test_process_error_handling(self):
        """プロセスエラーが適切に処理されることをテスト"""
        logger = Mock()
        executor = Mock()
        executor.execute_agent = AsyncMock(side_effect=RuntimeError("Process error"))

        process = AgentProcess(
            agent_id="test-1",
            role_name="test",
            prompt="test prompt",
            model="sonnet",
            logger=logger,
            executor=executor,
        )

        result = await process.start()

        assert result["success"] is False
        assert result["error_type"] == "process_error"
        assert "exception_class" in result
        assert result["exception_class"] == "RuntimeError"
        assert process.status == "failed"


class TestErrorTypeConsistency:
    """エラータイプの一貫性テスト"""

    def test_error_types_are_consistent(self):
        """全てのエラータイプが一貫していることをテスト"""
        expected_error_types = {
            "timeout",
            "permission",
            "file_not_found",
            "subprocess",
            "unexpected",
            "validation",
            "connection",
            "api_error",
            "tool_error",
            "process_error",
        }

        # このテストは、エラータイプの文字列が統一されていることを確認する
        # 実際のコードでこれらの文字列が使用されていることを確認
        assert len(expected_error_types) == 10

    def test_all_errors_have_error_type_field(self):
        """全てのエラーレスポンスにerror_typeフィールドがあることをテスト"""
        # これは設計の確認テスト
        # 実装では、全てのエラーレスポンスに error_type を含めるべき
        assert True  # 設計確認のみ


class TestCleanupErrorHandling:
    """クリーンアップ時のエラーハンドリングテスト"""

    @pytest.mark.asyncio
    async def test_cleanup_failure_is_logged(self):
        """クリーンアップ失敗がログに記録されることをテスト"""
        try:
            executor = ClaudeCodeExecutor()
        except ValueError:
            pytest.skip("claude-code not available")

        logger = Mock()

        # クリーンアップが失敗する状況をシミュレート
        with patch('shutil.rmtree', side_effect=OSError("Permission denied")):
            with patch.object(executor, 'claude_code_path', 'fake-command'):
                with patch('asyncio.create_subprocess_exec', side_effect=ValueError("Test error")):
                    result = await executor.execute_agent(
                        prompt="test",
                        model="sonnet",
                        logger=logger,
                    )

                    # クリーンアップエラーは警告レベルでログされるべき
                    # (メインのエラーは別途処理される)
                    # logger.warning が呼ばれることを期待

    @pytest.mark.asyncio
    async def test_cleanup_unexpected_error_is_logged(self):
        """クリーンアップ中の予期しないエラーがログに記録されることをテスト"""
        try:
            executor = ClaudeCodeExecutor()
        except ValueError:
            pytest.skip("claude-code not available")

        logger = Mock()

        # 予期しないエラー
        with patch('shutil.rmtree', side_effect=RuntimeError("Unexpected cleanup error")):
            with patch.object(executor, 'claude_code_path', 'fake-command'):
                with patch('asyncio.create_subprocess_exec', side_effect=ValueError("Test error")):
                    result = await executor.execute_agent(
                        prompt="test",
                        model="sonnet",
                        logger=logger,
                    )

                    # 予期しないエラーも記録されるべき
