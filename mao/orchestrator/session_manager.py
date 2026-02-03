"""
Session management for chat history persistence
"""
import json
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, asdict
import logging


@dataclass
class ChatMessage:
    """チャットメッセージ"""

    role: str  # "user", "cto", "system"
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """辞書に変換"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        """辞書から作成"""
        return cls(**data)


class SessionManager:
    """チャットセッション管理"""

    def __init__(
        self,
        project_path: Optional[Path] = None,
        session_id: Optional[str] = None,
        title: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Args:
            project_path: プロジェクトパス（.maoディレクトリの親）
            session_id: セッションID（Noneの場合は新規作成または最新セッションを使用）
            title: セッションタイトル（新規作成時のみ有効）
            logger: ロガー
        """
        self.project_path = project_path or Path.cwd()
        self.logger = logger or logging.getLogger(__name__)
        self._initial_title = title

        # セッションディレクトリ
        self.sessions_dir = self.project_path / ".mao" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # セッションID
        if session_id:
            self.session_id = session_id
        else:
            # 最新のセッションを取得、なければ新規作成
            latest = self.get_latest_session_id()
            self.session_id = latest if latest else self._generate_session_id()

        # セッションディレクトリ
        self.session_dir = self.sessions_dir / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # チャット履歴ファイル
        self.chat_file = self.session_dir / "chat.json"

        # メタデータファイル
        self.metadata_file = self.session_dir / "metadata.json"

        # メモリ内履歴
        self.messages: List[ChatMessage] = []

        # セッションメタデータ
        self.metadata: Dict[str, Any] = {
            "session_id": self.session_id,
            "title": self._initial_title or "",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "message_count": 0,
        }

        # 既存セッションを読み込み
        self._load_session()

        # 新規セッションの場合、タイトルが指定されていれば保存
        if self._initial_title and not self.metadata.get("title"):
            self.metadata["title"] = self._initial_title
            self._save_session()

    def _generate_session_id(self) -> str:
        """セッションIDを生成

        Returns:
            セッションID（タイムスタンプ + UUID）
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"{timestamp}_{short_uuid}"

    def _load_session(self) -> None:
        """セッションを読み込み"""
        # チャット履歴を読み込み
        if self.chat_file.exists():
            try:
                with open(self.chat_file) as f:
                    data = json.load(f)
                    self.messages = [ChatMessage.from_dict(msg) for msg in data]
                    self.logger.info(f"Loaded {len(self.messages)} messages from session {self.session_id}")
            except Exception as e:
                self.logger.error(f"Failed to load chat history: {e}")

        # メタデータを読み込み
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file) as f:
                    self.metadata = json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load metadata: {e}")

    def _save_session(self) -> None:
        """セッションを保存"""
        # チャット履歴を保存
        try:
            with open(self.chat_file, "w") as f:
                data = [msg.to_dict() for msg in self.messages]
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save chat history: {e}")

        # メタデータを保存
        try:
            self.metadata["updated_at"] = datetime.utcnow().isoformat()
            self.metadata["message_count"] = len(self.messages)

            with open(self.metadata_file, "w") as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """メッセージを追加

        Args:
            role: ロール（user, manager, system）
            content: メッセージ内容
            metadata: メタデータ

        Returns:
            追加されたメッセージ
        """
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.utcnow().isoformat(),
            metadata=metadata,
        )

        self.messages.append(message)
        self._save_session()

        return message

    def get_messages(
        self,
        role: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[ChatMessage]:
        """メッセージを取得

        Args:
            role: ロールでフィルタ（Noneの場合は全て）
            limit: 取得する最大件数（最新からN件）

        Returns:
            メッセージのリスト
        """
        messages = self.messages

        # ロールでフィルタ
        if role:
            messages = [msg for msg in messages if msg.role == role]

        # 最新N件を取得
        if limit:
            messages = messages[-limit:]

        return messages

    def clear_messages(self) -> None:
        """メッセージをクリア"""
        self.messages.clear()
        self._save_session()
        self.logger.info(f"Cleared all messages in session {self.session_id}")

    def delete_session(self) -> bool:
        """セッションを削除

        Returns:
            成功したかどうか
        """
        try:
            if self.session_dir.exists():
                # チャットファイルを削除
                if self.chat_file.exists():
                    self.chat_file.unlink()

                # メタデータファイルを削除
                if self.metadata_file.exists():
                    self.metadata_file.unlink()

                # セッションディレクトリを削除
                self.session_dir.rmdir()

                self.logger.info(f"Deleted session {self.session_id}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to delete session: {e}")

        return False

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """全セッションのメタデータを取得

        Returns:
            セッションメタデータのリスト
        """
        sessions = []

        for session_dir in sorted(self.sessions_dir.iterdir()):
            if not session_dir.is_dir():
                continue

            metadata_file = session_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                        sessions.append(metadata)
                except Exception as e:
                    self.logger.error(f"Failed to load metadata from {session_dir}: {e}")

        # 更新日時の降順でソート
        sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)

        return sessions

    def get_latest_session_id(self) -> Optional[str]:
        """最新のセッションIDを取得

        Returns:
            最新のセッションID（存在しない場合はNone）
        """
        sessions = self.get_all_sessions()
        if sessions:
            return sessions[0]["session_id"]
        return None

    def search_messages(self, query: str) -> List[ChatMessage]:
        """メッセージを検索

        Args:
            query: 検索クエリ

        Returns:
            マッチしたメッセージのリスト
        """
        query_lower = query.lower()
        results = []

        for message in self.messages:
            if query_lower in message.content.lower():
                results.append(message)

        return results

    def get_session_stats(self) -> Dict[str, Any]:
        """セッション統計を取得

        Returns:
            統計情報
        """
        user_messages = sum(1 for msg in self.messages if msg.role == "user")
        cto_messages = sum(1 for msg in self.messages if msg.role == "cto")
        system_messages = sum(1 for msg in self.messages if msg.role == "system")

        return {
            "session_id": self.session_id,
            "title": self.metadata.get("title", ""),
            "total_messages": len(self.messages),
            "user_messages": user_messages,
            "cto_messages": cto_messages,
            "system_messages": system_messages,
            "created_at": self.metadata.get("created_at"),
            "updated_at": self.metadata.get("updated_at"),
        }

    def set_title(self, title: str) -> None:
        """セッションタイトルを設定

        Args:
            title: セッションタイトル
        """
        self.metadata["title"] = title
        self._save_session()
        self.logger.info(f"Updated session title: {title}")

    def get_title(self) -> str:
        """セッションタイトルを取得

        Returns:
            セッションタイトル
        """
        return self.metadata.get("title", "")

    def export_session(self, output_file: Path) -> bool:
        """セッションをエクスポート

        Args:
            output_file: 出力ファイルパス

        Returns:
            成功したかどうか
        """
        try:
            export_data = {
                "metadata": self.metadata,
                "messages": [msg.to_dict() for msg in self.messages],
            }

            with open(output_file, "w") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Exported session to {output_file}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to export session: {e}")
            return False

    def import_session(self, import_file: Path) -> bool:
        """セッションをインポート

        Args:
            import_file: インポートファイルパス

        Returns:
            成功したかどうか
        """
        try:
            with open(import_file) as f:
                import_data = json.load(f)

            # メタデータを復元
            if "metadata" in import_data:
                self.metadata = import_data["metadata"]

            # メッセージを復元
            if "messages" in import_data:
                self.messages = [ChatMessage.from_dict(msg) for msg in import_data["messages"]]

            # セッションを保存
            self._save_session()

            self.logger.info(f"Imported session from {import_file}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to import session: {e}")
            return False
