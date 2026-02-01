"""
Integration tests for Interactive Mode
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from mao.ui.dashboard_interactive import InteractiveDashboard
from mao.orchestrator.project_loader import ProjectConfig, ProjectLoader


class TestInteractiveDashboardInitialization:
    """InteractiveDashboard の初期化テスト"""

    def test_dashboard_initialization(self, tmp_path):
        """ダッシュボードの基本初期化"""
        config = ProjectConfig(
            project_name="test",
            default_language="python",
        )

        dashboard = InteractiveDashboard(
            project_path=tmp_path,
            config=config,
            initial_prompt="テストタスク",
            tmux_manager=None,
        )

        assert dashboard.project_path == tmp_path
        assert dashboard.config == config
        assert dashboard.initial_prompt == "テストタスク"
        assert dashboard.tmux_manager is None

    def test_dashboard_with_tmux_manager(self, tmp_path):
        """tmuxマネージャー付きダッシュボード初期化"""
        config = ProjectConfig(
            project_name="test",
            default_language="python",
        )

        mock_tmux = Mock()

        dashboard = InteractiveDashboard(
            project_path=tmp_path,
            config=config,
            initial_prompt="テストタスク",
            tmux_manager=mock_tmux,
        )

        assert dashboard.tmux_manager == mock_tmux


class TestManagerCommunication:
    """マネージャーとの通信テスト"""

    @pytest.mark.asyncio
    async def test_send_to_manager_success(self, tmp_path):
        """マネージャーへのメッセージ送信成功"""
        config = ProjectConfig(
            project_name="test",
            default_language="python",
        )

        dashboard = InteractiveDashboard(
            project_path=tmp_path,
            config=config,
            initial_prompt="テストタスク",
            tmux_manager=None,
        )

        # ClaudeCodeExecutor をモック
        mock_executor = AsyncMock()
        mock_executor.execute_agent = AsyncMock(return_value={
            "success": True,
            "response": "了解しました。タスクを開始します。",
        })

        dashboard.manager_executor = mock_executor

        # ManagerChatPanel をモック
        mock_chat_panel = Mock()
        mock_chat_panel.add_system_message = Mock()
        mock_chat_panel.add_manager_message = Mock()
        dashboard.manager_chat_panel = mock_chat_panel

        # メッセージを送信
        await dashboard.send_to_manager("認証システムを実装してください")

        # executorが呼ばれたことを確認
        mock_executor.execute_agent.assert_called_once()
        call_kwargs = mock_executor.execute_agent.call_args[1]
        assert "認証システムを実装してください" in call_kwargs["prompt"]

        # マネージャーの応答が表示されたことを確認
        mock_chat_panel.add_manager_message.assert_called_once_with(
            "了解しました。タスクを開始します。"
        )

    @pytest.mark.asyncio
    async def test_send_to_manager_error(self, tmp_path):
        """マネージャーへのメッセージ送信エラー"""
        config = ProjectConfig(
            project_name="test",
            default_language="python",
        )

        dashboard = InteractiveDashboard(
            project_path=tmp_path,
            config=config,
            initial_prompt="テストタスク",
            tmux_manager=None,
        )

        # エラーを返すexecutor
        mock_executor = AsyncMock()
        mock_executor.execute_agent = AsyncMock(return_value={
            "success": False,
            "error": "接続エラー",
        })

        dashboard.manager_executor = mock_executor

        # ManagerChatPanel をモック
        mock_chat_panel = Mock()
        mock_chat_panel.add_system_message = Mock()
        mock_chat_panel.add_manager_message = Mock()
        dashboard.manager_chat_panel = mock_chat_panel

        # メッセージを送信
        await dashboard.send_to_manager("テストメッセージ")

        # システムメッセージでエラーが表示されたことを確認
        mock_chat_panel.add_system_message.assert_called()
        call_args = mock_chat_panel.add_system_message.call_args[0][0]
        assert "エラー" in call_args or "接続エラー" in call_args


class TestProjectConfigIntegration:
    """ProjectConfigとの統合テスト"""

    def test_dashboard_uses_project_config(self, tmp_path):
        """ダッシュボードがプロジェクト設定を使用"""
        # プロジェクト設定を作成
        mao_dir = tmp_path / ".mao"
        mao_dir.mkdir()

        config_file = mao_dir / "config.yaml"
        config_file.write_text(
            """
project_name: test_project
default_language: python
agents:
  default_model: sonnet
security:
  allow_unsafe_operations: false
"""
        )

        loader = ProjectLoader(tmp_path)
        config = loader.load()

        dashboard = InteractiveDashboard(
            project_path=tmp_path,
            config=config,
            initial_prompt="テストタスク",
            tmux_manager=None,
        )

        assert dashboard.config.project_name == "test_project"
        assert dashboard.config.security.allow_unsafe_operations is False

    def test_dashboard_with_defaults_config(self, tmp_path):
        """ダッシュボードがdefaults設定を使用"""
        mao_dir = tmp_path / ".mao"
        mao_dir.mkdir()

        config_file = mao_dir / "config.yaml"
        config_file.write_text(
            """
project_name: test_project
default_language: python
"""
        )

        loader = ProjectLoader(tmp_path)
        config = loader.load()

        dashboard = InteractiveDashboard(
            project_path=tmp_path,
            config=config,
            initial_prompt="テストタスク",
            tmux_manager=None,
        )

        # defaults設定が読み込まれていることを確認
        assert config.defaults is not None
        assert config.defaults.execution.max_tokens == 4096


class TestErrorHandling:
    """エラーハンドリングのテスト"""

    @pytest.mark.asyncio
    async def test_graceful_error_handling(self, tmp_path):
        """エラーが発生しても適切に処理"""
        config = ProjectConfig(
            project_name="test",
            default_language="python",
        )

        dashboard = InteractiveDashboard(
            project_path=tmp_path,
            config=config,
            initial_prompt="テストタスク",
            tmux_manager=None,
        )

        # 例外を投げるexecutor
        mock_executor = AsyncMock()
        mock_executor.execute_agent = AsyncMock(side_effect=Exception("予期しないエラー"))

        dashboard.manager_executor = mock_executor

        mock_chat_panel = Mock()
        mock_chat_panel.add_system_message = Mock()
        dashboard.manager_chat_panel = mock_chat_panel

        # エラーが発生しても例外は投げられない
        await dashboard.send_to_manager("テストメッセージ")

        # エラーメッセージが表示されたことを確認
        mock_chat_panel.add_system_message.assert_called()

    @pytest.mark.asyncio
    async def test_empty_response_handling(self, tmp_path):
        """空の応答の処理"""
        config = ProjectConfig(
            project_name="test",
            default_language="python",
        )

        dashboard = InteractiveDashboard(
            project_path=tmp_path,
            config=config,
            initial_prompt="テストタスク",
            tmux_manager=None,
        )

        # 空の応答を返すexecutor
        mock_executor = AsyncMock()
        mock_executor.execute_agent = AsyncMock(return_value={
            "success": True,
            "response": "",
        })

        dashboard.manager_executor = mock_executor

        mock_chat_panel = Mock()
        mock_chat_panel.add_system_message = Mock()
        mock_chat_panel.add_manager_message = Mock()
        dashboard.manager_chat_panel = mock_chat_panel

        # メッセージを送信
        await dashboard.send_to_manager("テストメッセージ")

        # 空の応答でもエラーにならない
        # (add_manager_messageまたはadd_system_messageが呼ばれる)
        assert (
            mock_chat_panel.add_manager_message.called
            or mock_chat_panel.add_system_message.called
        )




class TestSecurityConfiguration:
    """セキュリティ設定の統合テスト"""

    def test_safe_mode_by_default(self, tmp_path):
        """デフォルトは安全モード"""
        config = ProjectConfig(
            project_name="test",
            default_language="python",
        )

        dashboard = InteractiveDashboard(
            project_path=tmp_path,
            config=config,
            initial_prompt="テストタスク",
            tmux_manager=None,
        )

        # デフォルトではセキュリティ設定がFalse
        assert config.security.allow_unsafe_operations is False

    def test_unsafe_mode_from_config(self, tmp_path):
        """設定ファイルからunsafeモードを読み込み"""
        mao_dir = tmp_path / ".mao"
        mao_dir.mkdir()

        config_file = mao_dir / "config.yaml"
        config_file.write_text(
            """
project_name: test_project
default_language: python
security:
  allow_unsafe_operations: true
"""
        )

        loader = ProjectLoader(tmp_path)
        config = loader.load()

        dashboard = InteractiveDashboard(
            project_path=tmp_path,
            config=config,
            initial_prompt="テストタスク",
            tmux_manager=None,
        )

        # 設定が反映されている
        assert config.security.allow_unsafe_operations is True
