"""
Comprehensive tests for ClaudeCodeExecutor
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from mao.orchestrator.claude_code_executor import ClaudeCodeExecutor, AgentProcess


class TestClaudeCodeExecutorInitialization:
    """初期化とセットアップのテスト"""

    def test_initialization_with_claude_code_available(self):
        """claude-codeが利用可能な場合の初期化"""
        with patch("shutil.which", return_value="/usr/local/bin/claude-code"):
            executor = ClaudeCodeExecutor()
            assert executor.claude_code_path == "/usr/local/bin/claude-code"
            assert executor.allow_unsafe_operations is False

    def test_initialization_with_claude_available(self):
        """claudeコマンドが利用可能な場合の初期化"""
        with patch("shutil.which") as mock_which:
            # claude-code は見つからないが、claude は見つかる
            mock_which.side_effect = lambda cmd: "/usr/local/bin/claude" if cmd == "claude" else None
            executor = ClaudeCodeExecutor()
            assert executor.claude_code_path == "/usr/local/bin/claude"

    def test_initialization_without_claude_code(self):
        """claude-codeが利用不可の場合の初期化"""
        with patch("shutil.which", return_value=None):
            with pytest.raises(ValueError, match="claude-code command not found"):
                ClaudeCodeExecutor()

    def test_initialization_with_unsafe_operations(self):
        """unsafe操作を許可して初期化"""
        with patch("shutil.which", return_value="/usr/local/bin/claude-code"):
            executor = ClaudeCodeExecutor(allow_unsafe_operations=True)
            assert executor.allow_unsafe_operations is True

    def test_is_available_method(self):
        """is_available() メソッドのテスト"""
        with patch("shutil.which", return_value="/usr/local/bin/claude-code"):
            executor = ClaudeCodeExecutor()
            assert executor.is_available() is True


class TestExecuteAgentValidation:
    """execute_agent() のバリデーションテスト"""

    @pytest.mark.asyncio
    async def test_empty_prompt_returns_error(self):
        """空のプロンプトでエラーを返す"""
        with patch("shutil.which", return_value="/usr/local/bin/claude-code"):
            executor = ClaudeCodeExecutor()

            result = await executor.execute_agent(prompt="")
            assert result["success"] is False
            assert "空です" in result["error"]

    @pytest.mark.asyncio
    async def test_whitespace_only_prompt_returns_error(self):
        """空白のみのプロンプトでエラーを返す"""
        with patch("shutil.which", return_value="/usr/local/bin/claude-code"):
            executor = ClaudeCodeExecutor()

            result = await executor.execute_agent(prompt="   \n\t  ")
            assert result["success"] is False
            assert "空です" in result["error"]


class TestExecuteAgentSuccess:
    """execute_agent() の正常系テスト"""

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """正常な実行"""
        with patch("shutil.which", return_value="/usr/local/bin/claude-code"):
            executor = ClaudeCodeExecutor()

            # モックプロセスを作成
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdin = AsyncMock()
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()

            # stdoutから応答を返す
            async def mock_readline_stdout():
                for line in [b"This is a response\n", b""]:
                    yield line

            async def mock_readline_stderr():
                yield b""

            mock_process.stdout.readline = mock_readline_stdout().__anext__
            mock_process.stderr.readline = mock_readline_stderr().__anext__
            mock_process.wait = AsyncMock()

            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await executor.execute_agent(
                    prompt="test prompt",
                    model="sonnet",
                )

                assert result["success"] is True
                assert "response" in result
                assert "This is a response" in result["response"]
                assert result["model"] == "sonnet"
                assert "usage" in result

    @pytest.mark.asyncio
    async def test_execution_with_system_prompt(self):
        """システムプロンプト付きの実行"""
        with patch("shutil.which", return_value="/usr/local/bin/claude-code"):
            executor = ClaudeCodeExecutor()

            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdin = AsyncMock()
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()

            async def mock_readline_stdout():
                yield b"Response\n"
                yield b""

            async def mock_readline_stderr():
                yield b""

            mock_process.stdout.readline = mock_readline_stdout().__anext__
            mock_process.stderr.readline = mock_readline_stderr().__anext__
            mock_process.wait = AsyncMock()

            with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
                result = await executor.execute_agent(
                    prompt="test",
                    model="opus",
                    system="You are a helpful assistant",
                )

                assert result["success"] is True
                # システムプロンプトが引数に含まれることを確認
                call_args = mock_exec.call_args[0]
                assert "--append-system-prompt" in call_args

    @pytest.mark.asyncio
    async def test_execution_with_work_dir(self):
        """作業ディレクトリ指定の実行"""
        with patch("shutil.which", return_value="/usr/local/bin/claude-code"):
            executor = ClaudeCodeExecutor()

            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdin = AsyncMock()
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()

            async def mock_readline_stdout():
                yield b"Response\n"
                yield b""

            async def mock_readline_stderr():
                yield b""

            mock_process.stdout.readline = mock_readline_stdout().__anext__
            mock_process.stderr.readline = mock_readline_stderr().__anext__
            mock_process.wait = AsyncMock()

            work_dir = Path("/tmp/test_dir")

            with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
                result = await executor.execute_agent(
                    prompt="test",
                    model="haiku",
                    work_dir=work_dir,
                )

                assert result["success"] is True
                # 作業ディレクトリが引数に含まれることを確認
                call_args = mock_exec.call_args[0]
                assert "--add-dir" in call_args

    @pytest.mark.asyncio
    async def test_execution_with_log_callback(self):
        """ログコールバック付きの実行"""
        with patch("shutil.which", return_value="/usr/local/bin/claude-code"):
            executor = ClaudeCodeExecutor()

            callback_logs = []

            def log_callback(message):
                callback_logs.append(message)

            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdin = AsyncMock()
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()

            async def mock_readline_stdout():
                yield b"Line 1\n"
                yield b"Line 2\n"
                yield b""

            async def mock_readline_stderr():
                yield b"Error line\n"
                yield b""

            mock_process.stdout.readline = mock_readline_stdout().__anext__
            mock_process.stderr.readline = mock_readline_stderr().__anext__
            mock_process.wait = AsyncMock()

            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await executor.execute_agent(
                    prompt="test",
                    model="sonnet",
                    log_callback=log_callback,
                )

                assert result["success"] is True
                # コールバックが呼ばれたことを確認
                assert len(callback_logs) > 0
                assert any("Line 1" in log for log in callback_logs)
                assert any("Error line" in log for log in callback_logs)


class TestExecuteAgentFailure:
    """execute_agent() のエラーケーステスト"""

    @pytest.mark.asyncio
    async def test_execution_with_non_zero_exit_code(self):
        """非ゼロ終了コードでの実行"""
        with patch("shutil.which", return_value="/usr/local/bin/claude-code"):
            executor = ClaudeCodeExecutor()

            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.stdin = AsyncMock()
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()

            async def mock_readline_stdout():
                yield b""

            async def mock_readline_stderr():
                yield b"Error occurred\n"
                yield b""

            mock_process.stdout.readline = mock_readline_stdout().__anext__
            mock_process.stderr.readline = mock_readline_stderr().__anext__
            mock_process.wait = AsyncMock()

            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await executor.execute_agent(
                    prompt="test",
                    model="sonnet",
                )

                assert result["success"] is False
                assert "Error occurred" in result["error"]


class TestExecuteAgentStreaming:
    """execute_agent_streaming() のテスト"""

    @pytest.mark.asyncio
    async def test_streaming_execution_success(self):
        """ストリーミング実行の成功"""
        with patch("shutil.which", return_value="/usr/local/bin/claude-code"):
            executor = ClaudeCodeExecutor()

            # execute_agent をモック
            async def mock_execute_agent(*args, **kwargs):
                return {
                    "success": True,
                    "response": "Test response",
                    "usage": {"input_tokens": 10, "output_tokens": 20},
                    "stop_reason": "end_turn",
                }

            with patch.object(executor, "execute_agent", side_effect=mock_execute_agent):
                events = []
                async for event in executor.execute_agent_streaming(
                    prompt="test",
                    model="sonnet",
                ):
                    events.append(event)

                # イベントを確認
                assert len(events) == 3
                assert events[0]["type"] == "message_start"
                assert events[1]["type"] == "content"
                assert events[1]["content"] == "Test response"
                assert events[2]["type"] == "message_stop"
                assert events[2]["usage"]["input_tokens"] == 10

    @pytest.mark.asyncio
    async def test_streaming_execution_error(self):
        """ストリーミング実行のエラー"""
        with patch("shutil.which", return_value="/usr/local/bin/claude-code"):
            executor = ClaudeCodeExecutor()

            # execute_agent をモック（エラーを返す）
            async def mock_execute_agent(*args, **kwargs):
                return {
                    "success": False,
                    "error": "Test error",
                }

            with patch.object(executor, "execute_agent", side_effect=mock_execute_agent):
                events = []
                async for event in executor.execute_agent_streaming(
                    prompt="test",
                    model="sonnet",
                ):
                    events.append(event)

                # エラーイベントを確認
                assert len(events) == 1
                assert events[0]["type"] == "error"
                assert events[0]["error"] == "Test error"


class TestAgentProcess:
    """AgentProcess のテスト"""

    @pytest.mark.asyncio
    async def test_agent_process_start(self):
        """エージェントプロセスの開始"""
        logger = Mock()
        executor = Mock()
        executor.execute_agent = AsyncMock(return_value={
            "success": True,
            "response": "Done",
        })

        process = AgentProcess(
            agent_id="test-1",
            role_name="test",
            prompt="test prompt",
            model="sonnet",
            logger=logger,
            executor=executor,
        )

        result = await process.start()

        assert result["success"] is True
        assert result["response"] == "Done"
        executor.execute_agent.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_process_with_work_dir(self):
        """作業ディレクトリ指定のエージェントプロセス"""
        logger = Mock()
        executor = Mock()
        executor.execute_agent = AsyncMock(return_value={
            "success": True,
            "response": "Done",
        })

        work_dir = Path("/tmp/test")

        process = AgentProcess(
            agent_id="test-2",
            role_name="test",
            prompt="test prompt",
            model="opus",
            logger=logger,
            executor=executor,
            work_dir=work_dir,
        )

        result = await process.start()

        assert result["success"] is True
        # work_dir が渡されたことを確認
        call_kwargs = executor.execute_agent.call_args[1]
        assert call_kwargs["work_dir"] == work_dir

    def test_agent_process_is_running(self):
        """is_running() メソッドのテスト"""
        logger = Mock()
        executor = Mock()

        process = AgentProcess(
            agent_id="test-3",
            role_name="test",
            prompt="test prompt",
            model="haiku",
            logger=logger,
            executor=executor,
        )

        # タスクが未設定の場合
        assert process.is_running() is False

    def test_agent_process_get_result(self):
        """get_result() メソッドのテスト"""
        logger = Mock()
        executor = Mock()

        process = AgentProcess(
            agent_id="test-4",
            role_name="test",
            prompt="test prompt",
            model="sonnet",
            logger=logger,
            executor=executor,
        )

        # 結果が未設定の場合
        assert process.get_result() is None


class TestUnsafeOperations:
    """unsafe操作のテスト"""

    @pytest.mark.asyncio
    async def test_unsafe_mode_adds_flag(self):
        """unsafeモードでフラグが追加される"""
        with patch("shutil.which", return_value="/usr/local/bin/claude-code"):
            executor = ClaudeCodeExecutor(allow_unsafe_operations=True)

            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdin = AsyncMock()
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()

            async def mock_readline_stdout():
                yield b"Response\n"
                yield b""

            async def mock_readline_stderr():
                yield b""

            mock_process.stdout.readline = mock_readline_stdout().__anext__
            mock_process.stderr.readline = mock_readline_stderr().__anext__
            mock_process.wait = AsyncMock()

            with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
                await executor.execute_agent(
                    prompt="test",
                    model="sonnet",
                )

                # --dangerously-skip-permissions が含まれることを確認
                call_args = mock_exec.call_args[0]
                assert "--dangerously-skip-permissions" in call_args

    @pytest.mark.asyncio
    async def test_safe_mode_does_not_add_flag(self):
        """safeモードでフラグが追加されない"""
        with patch("shutil.which", return_value="/usr/local/bin/claude-code"):
            executor = ClaudeCodeExecutor(allow_unsafe_operations=False)

            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdin = AsyncMock()
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()

            async def mock_readline_stdout():
                yield b"Response\n"
                yield b""

            async def mock_readline_stderr():
                yield b""

            mock_process.stdout.readline = mock_readline_stdout().__anext__
            mock_process.stderr.readline = mock_readline_stderr().__anext__
            mock_process.wait = AsyncMock()

            with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
                await executor.execute_agent(
                    prompt="test",
                    model="sonnet",
                )

                # --dangerously-skip-permissions が含まれないことを確認
                call_args = mock_exec.call_args[0]
                assert "--dangerously-skip-permissions" not in call_args
