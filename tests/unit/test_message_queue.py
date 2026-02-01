"""
Tests for MessageQueue
"""
import pytest
import asyncio
from pathlib import Path
from mao.orchestrator.message_queue import (
    MessageQueue,
    Message,
    MessageType,
    MessagePriority,
)


class TestMessage:
    """Message のテスト"""

    def test_message_initialization(self):
        """Message の初期化"""
        message = Message(
            message_id="msg-001",
            message_type=MessageType.TASK_STARTED,
            sender="worker-1",
            receiver="manager",
            content="Task started",
            priority=MessagePriority.HIGH,
        )

        assert message.message_id == "msg-001"
        assert message.message_type == MessageType.TASK_STARTED
        assert message.sender == "worker-1"
        assert message.receiver == "manager"
        assert message.content == "Task started"
        assert message.priority == MessagePriority.HIGH
        assert message.timestamp != ""
        assert message.metadata == {}

    def test_message_to_dict(self):
        """to_dict() メソッドのテスト"""
        message = Message(
            message_id="msg-002",
            message_type=MessageType.TASK_COMPLETED,
            sender="worker-2",
            receiver="manager",
            content="Task completed",
            priority=MessagePriority.MEDIUM,
            metadata={"result": "success"},
        )

        data = message.to_dict()

        assert data["message_id"] == "msg-002"
        assert data["message_type"] == "task_completed"
        assert data["sender"] == "worker-2"
        assert data["receiver"] == "manager"
        assert data["content"] == "Task completed"
        assert data["priority"] == "medium"
        assert data["metadata"] == {"result": "success"}

    def test_message_from_dict(self):
        """from_dict() メソッドのテスト"""
        data = {
            "message_id": "msg-003",
            "message_type": "task_failed",
            "sender": "worker-3",
            "receiver": "manager",
            "content": "Task failed",
            "priority": "urgent",
            "timestamp": "2026-02-01T10:00:00",
            "metadata": {"error": "timeout"},
        }

        message = Message.from_dict(data)

        assert message.message_id == "msg-003"
        assert message.message_type == MessageType.TASK_FAILED
        assert message.sender == "worker-3"
        assert message.receiver == "manager"
        assert message.content == "Task failed"
        assert message.priority == MessagePriority.URGENT


class TestMessageQueue:
    """MessageQueue のテスト"""

    @pytest.mark.asyncio
    async def test_initialization(self, tmp_path):
        """MessageQueue の初期化"""
        queue = MessageQueue(project_path=tmp_path)

        assert queue.project_path == tmp_path
        assert queue.messages_dir.exists()
        assert queue.processed_dir.exists()

    @pytest.mark.asyncio
    async def test_send_message(self, tmp_path):
        """メッセージ送信"""
        queue = MessageQueue(project_path=tmp_path)

        message_id = await queue.send_message(
            message_type=MessageType.TASK_STARTED,
            sender="worker-1",
            receiver="manager",
            content="Starting task A",
            priority=MessagePriority.HIGH,
            metadata={"task_id": "task-A"},
        )

        assert message_id.startswith("msg-")

        # メッセージファイルが作成されたことを確認
        message_file = queue.messages_dir / f"{message_id}.yaml"
        assert message_file.exists()

    @pytest.mark.asyncio
    async def test_get_messages(self, tmp_path):
        """メッセージ取得"""
        queue = MessageQueue(project_path=tmp_path)

        # 複数のメッセージを送信
        await queue.send_message(
            message_type=MessageType.TASK_STARTED,
            sender="worker-1",
            receiver="manager",
            content="Task 1",
        )
        await queue.send_message(
            message_type=MessageType.TASK_PROGRESS,
            sender="worker-1",
            receiver="manager",
            content="Progress 50%",
        )
        await queue.send_message(
            message_type=MessageType.TASK_COMPLETED,
            sender="worker-2",
            receiver="manager",
            content="Task 2 completed",
        )

        # 全メッセージを取得
        messages = await queue.get_messages()
        assert len(messages) == 3

        # 受信者でフィルタ
        manager_messages = await queue.get_messages(receiver="manager")
        assert len(manager_messages) == 3

        # メッセージタイプでフィルタ
        started_messages = await queue.get_messages(message_type=MessageType.TASK_STARTED)
        assert len(started_messages) == 1
        assert started_messages[0].content == "Task 1"

    @pytest.mark.asyncio
    async def test_message_priority_ordering(self, tmp_path):
        """メッセージ優先度順のソート"""
        queue = MessageQueue(project_path=tmp_path)

        # 優先度が異なるメッセージを送信
        await queue.send_message(
            message_type=MessageType.TASK_PROGRESS,
            sender="worker-1",
            receiver="manager",
            content="Low priority",
            priority=MessagePriority.LOW,
        )
        await queue.send_message(
            message_type=MessageType.TASK_FAILED,
            sender="worker-2",
            receiver="manager",
            content="Urgent",
            priority=MessagePriority.URGENT,
        )
        await queue.send_message(
            message_type=MessageType.TASK_STARTED,
            sender="worker-3",
            receiver="manager",
            content="Medium priority",
            priority=MessagePriority.MEDIUM,
        )

        messages = await queue.get_messages()

        # URGENTが最初、その後MEDIUM、最後にLOW
        assert messages[0].content == "Urgent"
        assert messages[1].content == "Medium priority"
        assert messages[2].content == "Low priority"

    @pytest.mark.asyncio
    async def test_mark_as_processed(self, tmp_path):
        """メッセージを処理済みとしてマーク"""
        queue = MessageQueue(project_path=tmp_path)

        message_id = await queue.send_message(
            message_type=MessageType.TASK_COMPLETED,
            sender="worker-1",
            receiver="manager",
            content="Done",
        )

        # 未処理メッセージを確認
        messages = await queue.get_messages()
        assert len(messages) == 1

        # 処理済みとしてマーク
        success = await queue.mark_as_processed(message_id)
        assert success is True

        # 未処理メッセージが減ったことを確認
        messages = await queue.get_messages()
        assert len(messages) == 0

        # processedディレクトリに移動したことを確認
        processed_file = queue.processed_dir / f"{message_id}.yaml"
        assert processed_file.exists()

    @pytest.mark.asyncio
    async def test_delete_message(self, tmp_path):
        """メッセージ削除"""
        queue = MessageQueue(project_path=tmp_path)

        message_id = await queue.send_message(
            message_type=MessageType.TASK_STARTED,
            sender="worker-1",
            receiver="manager",
            content="Test",
        )

        # 削除
        success = await queue.delete_message(message_id)
        assert success is True

        # メッセージが削除されたことを確認
        messages = await queue.get_messages()
        assert len(messages) == 0

    @pytest.mark.asyncio
    async def test_clear_all_messages(self, tmp_path):
        """全メッセージをクリア"""
        queue = MessageQueue(project_path=tmp_path)

        # 複数のメッセージを送信
        await queue.send_message(
            message_type=MessageType.TASK_STARTED,
            sender="worker-1",
            receiver="manager",
            content="Task 1",
        )
        msg_id = await queue.send_message(
            message_type=MessageType.TASK_COMPLETED,
            sender="worker-2",
            receiver="manager",
            content="Task 2",
        )

        # 1つを処理済みにする
        await queue.mark_as_processed(msg_id)

        # 全クリア
        await queue.clear_all_messages()

        # 両方のディレクトリが空になったことを確認
        messages = await queue.get_messages()
        assert len(messages) == 0

        stats = queue.get_stats()
        assert stats["unprocessed"] == 0
        assert stats["processed"] == 0

    @pytest.mark.asyncio
    async def test_register_handler(self, tmp_path):
        """ハンドラー登録とメッセージ処理"""
        queue = MessageQueue(project_path=tmp_path)

        # ハンドラーを記録するリスト
        handled_messages = []

        def handler(message: Message):
            handled_messages.append(message.content)

        # ハンドラーを登録
        queue.register_handler(MessageType.TASK_STARTED, handler)

        # メッセージを送信
        await queue.send_message(
            message_type=MessageType.TASK_STARTED,
            sender="worker-1",
            receiver="manager",
            content="Task started",
        )

        # メッセージを処理
        processed = await queue.process_messages(receiver="manager")
        assert processed == 1
        assert "Task started" in handled_messages

    @pytest.mark.asyncio
    async def test_async_handler(self, tmp_path):
        """非同期ハンドラーのテスト"""
        queue = MessageQueue(project_path=tmp_path)

        handled_messages = []

        async def async_handler(message: Message):
            await asyncio.sleep(0.01)  # 非同期処理をシミュレート
            handled_messages.append(message.content)

        queue.register_handler(MessageType.TASK_COMPLETED, async_handler)

        await queue.send_message(
            message_type=MessageType.TASK_COMPLETED,
            sender="worker-1",
            receiver="manager",
            content="Done",
        )

        processed = await queue.process_messages(receiver="manager")
        assert processed == 1
        assert "Done" in handled_messages

    @pytest.mark.asyncio
    async def test_get_stats(self, tmp_path):
        """統計情報の取得"""
        queue = MessageQueue(project_path=tmp_path)

        # メッセージを送信
        msg1 = await queue.send_message(
            message_type=MessageType.TASK_STARTED,
            sender="worker-1",
            receiver="manager",
            content="Task 1",
        )
        await queue.send_message(
            message_type=MessageType.TASK_STARTED,
            sender="worker-2",
            receiver="manager",
            content="Task 2",
        )

        # 1つを処理済みにする
        await queue.mark_as_processed(msg1)

        stats = queue.get_stats()
        assert stats["unprocessed"] == 1
        assert stats["processed"] == 1
        assert stats["total"] == 2
