"""
Tests for SessionManager
"""
import pytest
import json
from pathlib import Path
from mao.orchestrator.session_manager import SessionManager, ChatMessage


class TestChatMessage:
    """ChatMessage のテスト"""

    def test_initialization(self):
        """初期化"""
        message = ChatMessage(
            role="user",
            content="Hello",
            timestamp="2026-02-01T10:00:00",
        )

        assert message.role == "user"
        assert message.content == "Hello"
        assert message.timestamp == "2026-02-01T10:00:00"
        assert message.metadata is None

    def test_to_dict(self):
        """to_dict() メソッドのテスト"""
        message = ChatMessage(
            role="manager",
            content="Response",
            timestamp="2026-02-01T10:00:00",
            metadata={"tokens": 100},
        )

        data = message.to_dict()

        assert data["role"] == "manager"
        assert data["content"] == "Response"
        assert data["timestamp"] == "2026-02-01T10:00:00"
        assert data["metadata"] == {"tokens": 100}

    def test_from_dict(self):
        """from_dict() メソッドのテスト"""
        data = {
            "role": "system",
            "content": "System message",
            "timestamp": "2026-02-01T10:00:00",
            "metadata": {},
        }

        message = ChatMessage.from_dict(data)

        assert message.role == "system"
        assert message.content == "System message"
        assert message.timestamp == "2026-02-01T10:00:00"


class TestSessionManager:
    """SessionManager のテスト"""

    def test_initialization_new_session(self, tmp_path):
        """新規セッションの初期化"""
        manager = SessionManager(project_path=tmp_path)

        assert manager.project_path == tmp_path
        assert manager.session_id is not None
        assert manager.session_dir.exists()
        assert len(manager.messages) == 0

    def test_initialization_with_session_id(self, tmp_path):
        """セッションID指定での初期化"""
        session_id = "test_session_123"
        manager = SessionManager(project_path=tmp_path, session_id=session_id)

        assert manager.session_id == session_id
        assert manager.session_dir.name == session_id

    def test_add_message(self, tmp_path):
        """メッセージ追加"""
        manager = SessionManager(project_path=tmp_path)

        message = manager.add_message(
            role="user",
            content="Test message",
        )

        assert message.role == "user"
        assert message.content == "Test message"
        assert len(manager.messages) == 1

        # ファイルに保存されていることを確認
        assert manager.chat_file.exists()

    def test_get_messages(self, tmp_path):
        """メッセージ取得"""
        manager = SessionManager(project_path=tmp_path)

        manager.add_message("user", "Message 1")
        manager.add_message("manager", "Response 1")
        manager.add_message("user", "Message 2")
        manager.add_message("system", "System info")

        # 全メッセージ取得
        all_messages = manager.get_messages()
        assert len(all_messages) == 4

        # ロールでフィルタ
        user_messages = manager.get_messages(role="user")
        assert len(user_messages) == 2
        assert all(msg.role == "user" for msg in user_messages)

        # 最新N件取得
        latest = manager.get_messages(limit=2)
        assert len(latest) == 2
        assert latest[0].content == "Message 2"
        assert latest[1].content == "System info"

    def test_clear_messages(self, tmp_path):
        """メッセージクリア"""
        manager = SessionManager(project_path=tmp_path)

        manager.add_message("user", "Message 1")
        manager.add_message("user", "Message 2")

        assert len(manager.messages) == 2

        manager.clear_messages()

        assert len(manager.messages) == 0

    def test_session_persistence(self, tmp_path):
        """セッション永続化"""
        session_id = "persistent_session"

        # 最初のマネージャーでメッセージを追加
        manager1 = SessionManager(project_path=tmp_path, session_id=session_id)
        manager1.add_message("user", "Message 1")
        manager1.add_message("manager", "Response 1")

        # 2番目のマネージャーで同じセッションを読み込み
        manager2 = SessionManager(project_path=tmp_path, session_id=session_id)

        assert len(manager2.messages) == 2
        assert manager2.messages[0].content == "Message 1"
        assert manager2.messages[1].content == "Response 1"

    def test_delete_session(self, tmp_path):
        """セッション削除"""
        manager = SessionManager(project_path=tmp_path)

        manager.add_message("user", "Test")

        session_dir = manager.session_dir
        assert session_dir.exists()

        success = manager.delete_session()

        assert success is True
        assert not session_dir.exists()

    def test_get_all_sessions(self, tmp_path):
        """全セッション取得"""
        # 複数のセッションを作成
        manager1 = SessionManager(project_path=tmp_path, session_id="session1")
        manager1.add_message("user", "Message 1")

        manager2 = SessionManager(project_path=tmp_path, session_id="session2")
        manager2.add_message("user", "Message 2")

        manager3 = SessionManager(project_path=tmp_path, session_id="session3")
        manager3.add_message("user", "Message 3")

        # 全セッション取得
        sessions = manager3.get_all_sessions()

        assert len(sessions) == 3
        session_ids = {s["session_id"] for s in sessions}
        assert session_ids == {"session1", "session2", "session3"}

    def test_get_latest_session_id(self, tmp_path):
        """最新セッションID取得"""
        # 最初のセッションを作成（メッセージを追加してメタデータを保存）
        manager = SessionManager(project_path=tmp_path, session_id="first_session")
        manager.add_message("user", "First message")

        latest = manager.get_latest_session_id()
        assert latest == "first_session"

        # 別のセッションを作成
        import time
        time.sleep(0.1)  # 時間差を作る

        manager2 = SessionManager(project_path=tmp_path, session_id="newer_session")
        manager2.add_message("user", "Test")

        # 最新セッションIDを取得
        latest = manager2.get_latest_session_id()
        assert latest == "newer_session"

    def test_search_messages(self, tmp_path):
        """メッセージ検索"""
        manager = SessionManager(project_path=tmp_path)

        manager.add_message("user", "Implement authentication system")
        manager.add_message("manager", "I will create auth module")
        manager.add_message("user", "Add tests")
        manager.add_message("manager", "Tests added for authentication")

        # 検索
        results = manager.search_messages("auth")

        assert len(results) == 3
        assert "authentication" in results[0].content.lower()
        assert "auth" in results[1].content.lower()

    def test_get_session_stats(self, tmp_path):
        """セッション統計"""
        manager = SessionManager(project_path=tmp_path)

        manager.add_message("user", "Message 1")
        manager.add_message("manager", "Response 1")
        manager.add_message("user", "Message 2")
        manager.add_message("system", "System info")
        manager.add_message("manager", "Response 2")

        stats = manager.get_session_stats()

        assert stats["total_messages"] == 5
        assert stats["user_messages"] == 2
        assert stats["manager_messages"] == 2
        assert stats["system_messages"] == 1

    def test_export_session(self, tmp_path):
        """セッションエクスポート"""
        manager = SessionManager(project_path=tmp_path)

        manager.add_message("user", "Message 1")
        manager.add_message("manager", "Response 1")

        export_file = tmp_path / "export.json"
        success = manager.export_session(export_file)

        assert success is True
        assert export_file.exists()

        # エクスポートされた内容を確認
        with open(export_file) as f:
            data = json.load(f)

        assert "metadata" in data
        assert "messages" in data
        assert len(data["messages"]) == 2

    def test_import_session(self, tmp_path):
        """セッションインポート"""
        # エクスポートデータを作成
        export_file = tmp_path / "import.json"
        export_data = {
            "metadata": {
                "session_id": "imported_session",
                "created_at": "2026-02-01T10:00:00",
            },
            "messages": [
                {
                    "role": "user",
                    "content": "Imported message",
                    "timestamp": "2026-02-01T10:00:00",
                    "metadata": {},
                }
            ],
        }

        with open(export_file, "w") as f:
            json.dump(export_data, f)

        # インポート
        manager = SessionManager(project_path=tmp_path)
        success = manager.import_session(export_file)

        assert success is True
        assert len(manager.messages) == 1
        assert manager.messages[0].content == "Imported message"

    def test_metadata_persistence(self, tmp_path):
        """メタデータの永続化"""
        session_id = "metadata_test"

        manager1 = SessionManager(project_path=tmp_path, session_id=session_id)
        manager1.add_message("user", "Test")

        # メタデータファイルが作成されていることを確認
        assert manager1.metadata_file.exists()

        # メタデータを読み込み
        manager2 = SessionManager(project_path=tmp_path, session_id=session_id)

        assert manager2.metadata["session_id"] == session_id
        assert manager2.metadata["message_count"] == 1
