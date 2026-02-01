"""
Tests for UI widgets
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from rich.text import Text

from mao.ui.widgets.header import HeaderWidget
from mao.ui.widgets.agent_list import AgentListWidget
from mao.ui.widgets.log_viewer_simple import SimpleLogViewer
from mao.ui.widgets.manager_chat import (
    ManagerChatWidget,
    ChatMessage,
    ManagerChatInput,
    ManagerChatPanel,
)


class TestHeaderWidget:
    """HeaderWidget のテスト"""

    def test_initialization(self):
        """初期化テスト"""
        widget = HeaderWidget()
        assert widget.task_description == ""
        assert widget.active_count == 0
        assert widget.total_count == 0

    def test_update_task_info(self):
        """タスク情報更新テスト"""
        widget = HeaderWidget()

        # update()をモックして表示更新を回避
        with patch.object(widget, 'update'):
            widget.update_task_info("テストタスク", active_count=3, total_count=5)

        assert widget.task_description == "テストタスク"
        assert widget.active_count == 3
        assert widget.total_count == 5

    def test_update_only_task_description(self):
        """タスク説明のみ更新"""
        widget = HeaderWidget()

        with patch.object(widget, 'update'):
            widget.update_task_info("新しいタスク")

        assert widget.task_description == "新しいタスク"
        assert widget.active_count == 0
        assert widget.total_count == 0


class TestAgentListWidget:
    """AgentListWidget のテスト"""

    def test_initialization(self):
        """初期化テスト"""
        widget = AgentListWidget()
        assert len(widget.agents) == 0
        assert widget.selected_index == 0

    def test_update_agent(self):
        """エージェント更新テスト"""
        widget = AgentListWidget()

        with patch.object(widget, 'update'):
            widget.update_agent(
                agent_id="agent-1",
                status="running",
                task="タスク実行中",
                tokens=1000,
                role="worker-1",
            )

        assert "agent-1" in widget.agents
        assert widget.agents["agent-1"]["status"] == "running"
        assert widget.agents["agent-1"]["task"] == "タスク実行中"
        assert widget.agents["agent-1"]["tokens"] == 1000
        assert widget.agents["agent-1"]["role"] == "worker-1"

    def test_update_multiple_agents(self):
        """複数エージェント更新テスト"""
        widget = AgentListWidget()

        with patch.object(widget, 'update'):
            widget.update_agent("agent-1", "running", role="worker-1")
            widget.update_agent("agent-2", "completed", role="worker-2")
            widget.update_agent("agent-3", "waiting", role="worker-3")

        assert len(widget.agents) == 3
        assert widget.agents["agent-1"]["status"] == "running"
        assert widget.agents["agent-2"]["status"] == "completed"
        assert widget.agents["agent-3"]["status"] == "waiting"

    def test_remove_agent(self):
        """エージェント削除テスト"""
        widget = AgentListWidget()

        with patch.object(widget, 'update'):
            widget.update_agent("agent-1", "running")
            widget.update_agent("agent-2", "completed")
            widget.remove_agent("agent-1")

        assert "agent-1" not in widget.agents
        assert "agent-2" in widget.agents
        assert len(widget.agents) == 1

    def test_remove_nonexistent_agent(self):
        """存在しないエージェント削除テスト"""
        widget = AgentListWidget()

        with patch.object(widget, 'update'):
            widget.update_agent("agent-1", "running")
            widget.remove_agent("nonexistent")

        assert len(widget.agents) == 1

    def test_get_selected_agent(self):
        """選択エージェント取得テスト"""
        widget = AgentListWidget()

        with patch.object(widget, 'update'):
            widget.update_agent("agent-1", "running")
            widget.update_agent("agent-2", "completed")

        selected = widget.get_selected_agent()
        assert selected == "agent-1"

    def test_get_selected_agent_empty(self):
        """エージェントなしで選択取得テスト"""
        widget = AgentListWidget()
        selected = widget.get_selected_agent()
        assert selected == ""

    def test_select_next(self):
        """次のエージェント選択テスト"""
        widget = AgentListWidget()

        with patch.object(widget, 'update'):
            widget.update_agent("agent-1", "running")
            widget.update_agent("agent-2", "completed")
            widget.update_agent("agent-3", "waiting")

            assert widget.get_selected_agent() == "agent-1"

            widget.select_next()
            assert widget.get_selected_agent() == "agent-2"

            widget.select_next()
            assert widget.get_selected_agent() == "agent-3"

            widget.select_next()
            assert widget.get_selected_agent() == "agent-1"

    def test_select_prev(self):
        """前のエージェント選択テスト"""
        widget = AgentListWidget()

        with patch.object(widget, 'update'):
            widget.update_agent("agent-1", "running")
            widget.update_agent("agent-2", "completed")
            widget.update_agent("agent-3", "waiting")

            assert widget.get_selected_agent() == "agent-1"

            widget.select_prev()
            assert widget.get_selected_agent() == "agent-3"

            widget.select_prev()
            assert widget.get_selected_agent() == "agent-2"

    def test_normalize_status(self):
        """ステータス正規化テスト"""
        widget = AgentListWidget()

        assert widget._normalize_status("completed") == "completed"
        assert widget._normalize_status("ACTIVE") == "completed"
        assert widget._normalize_status("running") == "running"
        assert widget._normalize_status("THINKING") == "running"
        assert widget._normalize_status("error") == "error"
        assert widget._normalize_status("failed") == "error"
        assert widget._normalize_status("waiting") == "waiting"
        assert widget._normalize_status("IDLE") == "waiting"

    def test_get_status_text(self):
        """ステータステキスト取得テスト"""
        widget = AgentListWidget()

        assert widget._get_status_text("completed") == "Completed"
        assert widget._get_status_text("ACTIVE") == "Completed"
        assert widget._get_status_text("running") == "Running..."
        assert widget._get_status_text("THINKING") == "Running..."
        assert widget._get_status_text("error") == "Error"
        assert widget._get_status_text("ERROR") == "Error"
        assert widget._get_status_text("waiting") == "Waiting"


class TestSimpleLogViewer:
    """SimpleLogViewer のテスト"""

    def test_initialization(self):
        """初期化テスト"""
        widget = SimpleLogViewer(max_lines=50)
        assert len(widget.logs) == 0
        assert widget.current_agent == ""
        assert widget.max_lines == 50
        assert widget.auto_scroll is True

    def test_add_log(self):
        """ログ追加テスト"""
        widget = SimpleLogViewer()

        with patch.object(widget, 'update'), patch.object(widget, 'scroll_end'):
            widget.add_log("テストメッセージ", agent_id="agent-1", level="INFO")

        assert len(widget.logs) == 1
        log_entry = widget.logs[0]
        assert "INFO" in log_entry
        assert "[agent-1]" in log_entry
        assert "テストメッセージ" in log_entry

    def test_add_multiple_logs(self):
        """複数ログ追加テスト"""
        widget = SimpleLogViewer()

        with patch.object(widget, 'update'), patch.object(widget, 'scroll_end'):
            widget.add_log("ログ1", level="INFO")
            widget.add_log("ログ2", level="DEBUG")
            widget.add_log("ログ3", level="ERROR")

        assert len(widget.logs) == 3

    def test_max_lines_limit(self):
        """最大行数制限テスト"""
        widget = SimpleLogViewer(max_lines=5)

        with patch.object(widget, 'update'), patch.object(widget, 'scroll_end'):
            for i in range(10):
                widget.add_log(f"ログ{i}")

        assert len(widget.logs) == 5
        assert "ログ9" in widget.logs[-1]

    def test_clear_logs(self):
        """ログクリアテスト"""
        widget = SimpleLogViewer()

        with patch.object(widget, 'update'), patch.object(widget, 'scroll_end'):
            widget.add_log("ログ1")
            widget.add_log("ログ2")
            widget.add_log("ログ3")

            assert len(widget.logs) == 3

            widget.clear_logs()
            assert len(widget.logs) == 0

    def test_set_current_agent(self):
        """表示エージェント設定テスト"""
        widget = SimpleLogViewer()

        with patch.object(widget, 'update'):
            widget.set_current_agent("agent-1")

        assert widget.current_agent == "agent-1"

    def test_add_log_with_agent_filter(self):
        """エージェントフィルタ付きログ追加テスト"""
        widget = SimpleLogViewer()

        with patch.object(widget, 'update'), patch.object(widget, 'scroll_end'):
            widget.set_current_agent("agent-1")
            widget.add_log("メッセージ1", agent_id="agent-1")
            widget.add_log("メッセージ2", agent_id="agent-2")

        assert len(widget.logs) == 2

    def test_colorize_log(self):
        """ログ色付けテスト"""
        widget = SimpleLogViewer()

        log_entry = "12:00:00 | INFO  | テストメッセージ"
        colored = widget._colorize_log(log_entry)
        assert isinstance(colored, Text)

        log_entry = "12:00:00 | ERROR | エラーメッセージ"
        colored = widget._colorize_log(log_entry)
        assert isinstance(colored, Text)

    def test_log_levels(self):
        """各ログレベルのテスト"""
        widget = SimpleLogViewer()

        with patch.object(widget, 'update'), patch.object(widget, 'scroll_end'):
            for level in ["INFO", "DEBUG", "WARN", "ERROR", "TOOL", "THINKING", "ACTION", "RESULT"]:
                widget.add_log(f"{level}メッセージ", level=level)

        assert len(widget.logs) == 8


class TestChatMessage:
    """ChatMessage のテスト"""

    def test_user_message_format(self):
        """ユーザーメッセージフォーマットテスト"""
        msg = ChatMessage("user", "こんにちは")
        formatted = msg.format()

        assert isinstance(formatted, Text)
        plain_text = formatted.plain
        assert "You" in plain_text
        assert "こんにちは" in plain_text

    def test_manager_message_format(self):
        """マネージャーメッセージフォーマットテスト"""
        msg = ChatMessage("manager", "了解しました")
        formatted = msg.format()

        plain_text = formatted.plain
        assert "Manager" in plain_text
        assert "了解しました" in plain_text

    def test_system_message_format(self):
        """システムメッセージフォーマットテスト"""
        msg = ChatMessage("system", "タスク完了")
        formatted = msg.format()

        plain_text = formatted.plain
        assert "System" in plain_text
        assert "タスク完了" in plain_text

    def test_message_with_custom_timestamp(self):
        """カスタムタイムスタンプのテスト"""
        import datetime
        timestamp = datetime.datetime(2025, 1, 1, 12, 0, 0)
        msg = ChatMessage("user", "テスト", timestamp=timestamp)

        assert msg.timestamp == timestamp


class TestManagerChatWidget:
    """ManagerChatWidget のテスト"""

    def test_initialization(self):
        """初期化テスト"""
        widget = ManagerChatWidget(max_messages=30)
        assert len(widget.messages) == 0
        assert widget.on_send_callback is None

    def test_add_user_message(self):
        """ユーザーメッセージ追加テスト"""
        widget = ManagerChatWidget()

        with patch.object(widget, 'update'):
            widget.add_user_message("こんにちは")

        assert len(widget.messages) == 1
        assert widget.messages[0].sender == "user"
        assert widget.messages[0].message == "こんにちは"

    def test_add_manager_message(self):
        """マネージャーメッセージ追加テスト"""
        widget = ManagerChatWidget()

        with patch.object(widget, 'update'):
            widget.add_manager_message("タスクを開始します")

        assert len(widget.messages) == 1
        assert widget.messages[0].sender == "manager"
        assert widget.messages[0].message == "タスクを開始します"

    def test_add_system_message(self):
        """システムメッセージ追加テスト"""
        widget = ManagerChatWidget()

        with patch.object(widget, 'update'):
            widget.add_system_message("接続しました")

        assert len(widget.messages) == 1
        assert widget.messages[0].sender == "system"
        assert widget.messages[0].message == "接続しました"

    def test_multiple_messages(self):
        """複数メッセージ追加テスト"""
        widget = ManagerChatWidget()

        with patch.object(widget, 'update'):
            widget.add_user_message("タスク1")
            widget.add_manager_message("了解")
            widget.add_user_message("タスク2")
            widget.add_manager_message("実行中")

        assert len(widget.messages) == 4
        assert widget.messages[0].sender == "user"
        assert widget.messages[1].sender == "manager"
        assert widget.messages[2].sender == "user"
        assert widget.messages[3].sender == "manager"

    def test_max_messages_limit(self):
        """最大メッセージ数制限テスト"""
        widget = ManagerChatWidget(max_messages=5)

        with patch.object(widget, 'update'):
            for i in range(10):
                widget.add_user_message(f"メッセージ{i}")

        assert len(widget.messages) == 5
        assert widget.messages[-1].message == "メッセージ9"

    def test_set_send_callback(self):
        """送信コールバック設定テスト"""
        widget = ManagerChatWidget()
        callback = Mock()

        widget.set_send_callback(callback)
        assert widget.on_send_callback == callback


class TestManagerChatInput:
    """ManagerChatInput のテスト"""

    def test_initialization(self):
        """初期化テスト"""
        widget = ManagerChatInput()
        assert widget.on_submit_callback is None
        assert widget.placeholder is not None

    def test_set_submit_callback(self):
        """送信コールバック設定テスト"""
        widget = ManagerChatInput()
        callback = Mock()

        widget.set_submit_callback(callback)
        assert widget.on_submit_callback == callback

    def test_on_input_submitted(self):
        """入力送信テスト"""
        widget = ManagerChatInput()
        callback = Mock()
        widget.set_submit_callback(callback)

        class MockEvent:
            value = "テストメッセージ"

        event = MockEvent()
        widget.on_input_submitted(event)

        callback.assert_called_once_with("テストメッセージ")
        assert widget.value == ""

    def test_on_input_submitted_empty(self):
        """空入力送信テスト"""
        widget = ManagerChatInput()
        callback = Mock()
        widget.set_submit_callback(callback)

        class MockEvent:
            value = "   "

        event = MockEvent()
        widget.on_input_submitted(event)

        callback.assert_not_called()


class TestManagerChatPanel:
    """ManagerChatPanel のテスト"""

    def test_initialization(self):
        """初期化テスト"""
        panel = ManagerChatPanel()
        assert panel.chat_widget is not None
        assert panel.input_widget is not None

    def test_add_manager_message(self):
        """マネージャーメッセージ追加テスト"""
        panel = ManagerChatPanel()

        with patch.object(panel.chat_widget, 'update'):
            panel.add_manager_message("テストメッセージ")

        assert len(panel.chat_widget.messages) == 1
        assert panel.chat_widget.messages[0].sender == "manager"

    def test_add_system_message(self):
        """システムメッセージ追加テスト"""
        panel = ManagerChatPanel()

        with patch.object(panel.chat_widget, 'update'):
            panel.add_system_message("システムメッセージ")

        assert len(panel.chat_widget.messages) == 1
        assert panel.chat_widget.messages[0].sender == "system"

    def test_set_send_callback(self):
        """送信コールバック設定テスト"""
        panel = ManagerChatPanel()
        callback = Mock()

        panel.set_send_callback(callback)

        class MockEvent:
            value = "テストメッセージ"

        with patch.object(panel.chat_widget, 'update'):
            event = MockEvent()
            panel.input_widget.on_input_submitted(event)

        callback.assert_called_once_with("テストメッセージ")
        assert len(panel.chat_widget.messages) == 1
        assert panel.chat_widget.messages[0].sender == "user"
        assert panel.chat_widget.messages[0].message == "テストメッセージ"
