"""
Message queue system for agent communication
"""
import yaml
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import logging


class MessageType(str, Enum):
    """メッセージタイプ"""

    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    QUESTION = "question"
    RESPONSE = "response"
    REASSIGN_REQUEST = "reassign_request"


class MessagePriority(str, Enum):
    """メッセージ優先度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Message:
    """メッセージ"""

    message_id: str
    message_type: MessageType
    sender: str  # worker-1, manager, etc.
    receiver: str  # manager, worker-1, etc.
    content: str
    priority: MessagePriority = MessagePriority.MEDIUM
    timestamp: str = ""
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """初期化後の処理"""
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """辞書に変換"""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value if isinstance(self.message_type, MessageType) else self.message_type,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "priority": self.priority.value if isinstance(self.priority, MessagePriority) else self.priority,
            "timestamp": self.timestamp,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """辞書から作成"""
        # Enumを変換
        if isinstance(data.get("message_type"), str):
            data["message_type"] = MessageType(data["message_type"])
        if isinstance(data.get("priority"), str):
            data["priority"] = MessagePriority(data["priority"])
        return cls(**data)


class MessageQueue:
    """YAMLベースのメッセージキュー"""

    def __init__(
        self,
        project_path: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Args:
            project_path: プロジェクトパス（.maoディレクトリの親）
            logger: ロガー
        """
        self.project_path = project_path or Path.cwd()
        self.logger = logger or logging.getLogger(__name__)

        # メッセージディレクトリ
        self.queue_dir = self.project_path / ".mao" / "queue"
        self.messages_dir = self.queue_dir / "messages"
        self.processed_dir = self.queue_dir / "processed"

        # ディレクトリ作成
        self.messages_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        # メッセージカウンター
        self._message_counter = 0
        self._lock = asyncio.Lock()

        # メッセージハンドラー
        self._handlers: Dict[str, List[Callable]] = {}

    def _generate_message_id(self) -> str:
        """メッセージIDを生成"""
        self._message_counter += 1
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"msg-{timestamp}-{self._message_counter:04d}"

    async def send_message(
        self,
        message_type: MessageType,
        sender: str,
        receiver: str,
        content: str,
        priority: MessagePriority = MessagePriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """メッセージを送信

        Args:
            message_type: メッセージタイプ
            sender: 送信者
            receiver: 受信者
            content: 内容
            priority: 優先度
            metadata: メタデータ

        Returns:
            メッセージID
        """
        async with self._lock:
            message_id = self._generate_message_id()

            message = Message(
                message_id=message_id,
                message_type=message_type,
                sender=sender,
                receiver=receiver,
                content=content,
                priority=priority,
                metadata=metadata,
            )

            # YAMLファイルに保存
            message_file = self.messages_dir / f"{message_id}.yaml"
            with open(message_file, "w") as f:
                yaml.dump(message.to_dict(), f, default_flow_style=False, allow_unicode=True)

            self.logger.info(f"Message sent: {message_id} ({sender} -> {receiver})")
            return message_id

    async def get_messages(
        self,
        receiver: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        priority: Optional[MessagePriority] = None,
    ) -> List[Message]:
        """メッセージを取得

        Args:
            receiver: 受信者（指定しない場合は全て）
            message_type: メッセージタイプでフィルタ
            priority: 優先度でフィルタ

        Returns:
            メッセージのリスト
        """
        messages = []

        for message_file in sorted(self.messages_dir.glob("*.yaml")):
            try:
                with open(message_file) as f:
                    data = yaml.safe_load(f)

                message = Message.from_dict(data)

                # フィルタ適用
                if receiver and message.receiver != receiver:
                    continue
                if message_type and message.message_type != message_type:
                    continue
                if priority and message.priority != priority:
                    continue

                messages.append(message)

            except Exception as e:
                self.logger.error(f"Failed to load message from {message_file}: {e}")

        # 優先度順、タイムスタンプ順にソート
        priority_order = {
            MessagePriority.URGENT: 0,
            MessagePriority.HIGH: 1,
            MessagePriority.MEDIUM: 2,
            MessagePriority.LOW: 3,
        }
        messages.sort(key=lambda m: (priority_order.get(m.priority, 2), m.timestamp))

        return messages

    async def mark_as_processed(self, message_id: str) -> bool:
        """メッセージを処理済みとしてマーク

        Args:
            message_id: メッセージID

        Returns:
            成功したかどうか
        """
        message_file = self.messages_dir / f"{message_id}.yaml"
        if not message_file.exists():
            return False

        # processedディレクトリに移動
        processed_file = self.processed_dir / f"{message_id}.yaml"
        message_file.rename(processed_file)

        self.logger.info(f"Message marked as processed: {message_id}")
        return True

    async def delete_message(self, message_id: str) -> bool:
        """メッセージを削除

        Args:
            message_id: メッセージID

        Returns:
            成功したかどうか
        """
        message_file = self.messages_dir / f"{message_id}.yaml"
        if not message_file.exists():
            # processedディレクトリもチェック
            message_file = self.processed_dir / f"{message_id}.yaml"
            if not message_file.exists():
                return False

        message_file.unlink()
        self.logger.info(f"Message deleted: {message_id}")
        return True

    async def clear_all_messages(self) -> None:
        """全メッセージをクリア"""
        # 未処理メッセージ
        for message_file in self.messages_dir.glob("*.yaml"):
            message_file.unlink()

        # 処理済みメッセージ
        for message_file in self.processed_dir.glob("*.yaml"):
            message_file.unlink()

        self.logger.info("All messages cleared")

    def register_handler(
        self,
        message_type: MessageType,
        handler: Callable[[Message], None],
    ) -> None:
        """メッセージハンドラーを登録

        Args:
            message_type: メッセージタイプ
            handler: ハンドラー関数
        """
        if message_type.value not in self._handlers:
            self._handlers[message_type.value] = []
        self._handlers[message_type.value].append(handler)

    async def process_messages(
        self,
        receiver: str,
        mark_processed: bool = True,
    ) -> int:
        """受信者のメッセージを処理

        Args:
            receiver: 受信者
            mark_processed: 処理済みとしてマークするか

        Returns:
            処理したメッセージ数
        """
        messages = await self.get_messages(receiver=receiver)
        processed_count = 0

        for message in messages:
            # ハンドラーを実行
            handlers = self._handlers.get(message.message_type.value, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                except Exception as e:
                    self.logger.error(f"Handler error for message {message.message_id}: {e}")

            # 処理済みとしてマーク
            if mark_processed:
                await self.mark_as_processed(message.message_id)

            processed_count += 1

        return processed_count

    async def start_polling(
        self,
        receiver: str,
        interval: float = 1.0,
        mark_processed: bool = True,
    ) -> None:
        """メッセージポーリングを開始

        Args:
            receiver: 受信者
            interval: ポーリング間隔（秒）
            mark_processed: 処理済みとしてマークするか
        """
        self.logger.info(f"Starting message polling for {receiver} (interval={interval}s)")

        while True:
            try:
                await self.process_messages(receiver=receiver, mark_processed=mark_processed)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                self.logger.info(f"Polling stopped for {receiver}")
                break
            except Exception as e:
                self.logger.error(f"Polling error for {receiver}: {e}")
                await asyncio.sleep(interval)

    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得

        Returns:
            統計情報
        """
        unprocessed_count = len(list(self.messages_dir.glob("*.yaml")))
        processed_count = len(list(self.processed_dir.glob("*.yaml")))

        return {
            "unprocessed": unprocessed_count,
            "processed": processed_count,
            "total": unprocessed_count + processed_count,
        }
