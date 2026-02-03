"""
Tests for FeedbackManager
"""
import pytest
from pathlib import Path
from mao.orchestrator.feedback_manager import FeedbackManager, Feedback


class TestFeedback:
    """Feedback のテスト"""

    def test_initialization(self):
        """初期化"""
        feedback = Feedback(
            id="fb_123",
            title="Test feedback",
            description="This is a test",
            category="improvement",
            priority="medium",
            agent_id="manager",
            session_id="session_123",
            created_at="2026-02-01T10:00:00",
            status="open",
        )

        assert feedback.id == "fb_123"
        assert feedback.title == "Test feedback"
        assert feedback.category == "improvement"
        assert feedback.priority == "medium"
        assert feedback.status == "open"

    def test_to_dict(self):
        """to_dict() メソッド"""
        feedback = Feedback(
            id="fb_123",
            title="Test",
            description="Description",
            category="bug",
            priority="high",
            agent_id="manager",
            session_id="session_123",
            created_at="2026-02-01T10:00:00",
        )

        data = feedback.to_dict()

        assert data["id"] == "fb_123"
        assert data["title"] == "Test"
        assert data["category"] == "bug"
        assert data["priority"] == "high"

    def test_from_dict(self):
        """from_dict() メソッド"""
        data = {
            "id": "fb_123",
            "title": "Test",
            "description": "Description",
            "category": "feature",
            "priority": "low",
            "agent_id": "manager",
            "session_id": "session_123",
            "created_at": "2026-02-01T10:00:00",
            "status": "open",
            "metadata": {},
        }

        feedback = Feedback.from_dict(data)

        assert feedback.id == "fb_123"
        assert feedback.category == "feature"
        assert feedback.priority == "low"


class TestFeedbackManager:
    """FeedbackManager のテスト"""

    def test_initialization(self, tmp_path):
        """初期化"""
        manager = FeedbackManager(project_path=tmp_path)

        assert manager.project_path == tmp_path
        assert manager.feedback_dir.exists()
        assert manager.index_file.exists() or not manager.index_file.exists()

    def test_add_feedback(self, tmp_path):
        """フィードバック追加"""
        manager = FeedbackManager(project_path=tmp_path)

        feedback = manager.add_feedback(
            title="Test feedback",
            description="This is a test feedback",
            category="improvement",
            priority="medium",
            agent_id="manager",
            session_id="session_123",
        )

        assert feedback.title == "Test feedback"
        assert feedback.category == "improvement"
        assert feedback.status == "open"

        # ファイルが作成されていることを確認
        assert manager.feedback_dir.exists()
        feedback_file = manager.feedback_dir / f"{feedback.id}.json"
        assert feedback_file.exists()

    def test_get_feedback(self, tmp_path):
        """フィードバック取得"""
        manager = FeedbackManager(project_path=tmp_path)

        # フィードバックを追加
        feedback1 = manager.add_feedback(
            title="Test 1",
            description="Description 1",
            agent_id="manager",
            session_id="session_123",
        )

        # フィードバックを取得
        feedback2 = manager.get_feedback(feedback1.id)

        assert feedback2 is not None
        assert feedback2.id == feedback1.id
        assert feedback2.title == "Test 1"

    def test_get_nonexistent_feedback(self, tmp_path):
        """存在しないフィードバック取得"""
        manager = FeedbackManager(project_path=tmp_path)

        feedback = manager.get_feedback("nonexistent_id")

        assert feedback is None

    def test_list_feedbacks(self, tmp_path):
        """フィードバック一覧"""
        manager = FeedbackManager(project_path=tmp_path)

        # 複数のフィードバックを追加
        manager.add_feedback("Feedback 1", "Desc 1", "bug", "high", "manager", "session_1")
        manager.add_feedback("Feedback 2", "Desc 2", "feature", "medium", "manager", "session_1")
        manager.add_feedback("Feedback 3", "Desc 3", "improvement", "low", "manager", "session_1")

        # 全フィードバック取得
        feedbacks = manager.list_feedbacks()

        assert len(feedbacks) == 3

    def test_list_feedbacks_with_filter(self, tmp_path):
        """フィルタ付きフィードバック一覧"""
        manager = FeedbackManager(project_path=tmp_path)

        manager.add_feedback("Bug 1", "Desc", "bug", "high", "manager", "session_1")
        manager.add_feedback("Feature 1", "Desc", "feature", "medium", "manager", "session_1")
        manager.add_feedback("Bug 2", "Desc", "bug", "low", "manager", "session_1")

        # カテゴリでフィルタ
        bugs = manager.list_feedbacks(category="bug")
        assert len(bugs) == 2

        # 優先度でフィルタ
        high_priority = manager.list_feedbacks(priority="high")
        assert len(high_priority) == 1

    def test_update_status(self, tmp_path):
        """ステータス更新"""
        manager = FeedbackManager(project_path=tmp_path)

        feedback = manager.add_feedback("Test", "Desc", agent_id="manager", session_id="session_1")

        # ステータスを更新
        success = manager.update_status(feedback.id, "in_progress")

        assert success is True

        # 更新されたフィードバックを取得
        updated = manager.get_feedback(feedback.id)
        assert updated.status == "in_progress"

    def test_delete_feedback(self, tmp_path):
        """フィードバック削除"""
        manager = FeedbackManager(project_path=tmp_path)

        feedback = manager.add_feedback("Test", "Desc", agent_id="manager", session_id="session_1")

        # 削除
        success = manager.delete_feedback(feedback.id)

        assert success is True

        # 削除されたことを確認
        deleted = manager.get_feedback(feedback.id)
        assert deleted is None

    def test_get_stats(self, tmp_path):
        """統計取得"""
        manager = FeedbackManager(project_path=tmp_path)

        # 複数のフィードバックを追加
        fb1 = manager.add_feedback("Test 1", "Desc", "bug", "high", "manager", "session_1")
        manager.add_feedback("Test 2", "Desc", "feature", "medium", "manager", "session_1")
        manager.add_feedback("Test 3", "Desc", "improvement", "low", "manager", "session_1")

        # 1つを完了にする
        manager.update_status(fb1.id, "completed")

        # 統計を取得
        stats = manager.get_stats()

        assert stats["total"] == 3
        assert stats["open"] == 2
        assert stats["completed"] == 1
        assert stats["by_category"]["bug"] == 1
        assert stats["by_category"]["feature"] == 1
        assert stats["by_category"]["improvement"] == 1
        assert stats["by_priority"]["high"] == 1
        assert stats["by_priority"]["medium"] == 1
        assert stats["by_priority"]["low"] == 1

    def test_repair_index_no_issues(self, tmp_path):
        """repair_index: 問題がない場合"""
        manager = FeedbackManager(project_path=tmp_path)

        # フィードバックを追加（正常に追加される）
        manager.add_feedback("Test 1", "Desc", agent_id="manager", session_id="session_1")
        manager.add_feedback("Test 2", "Desc", agent_id="manager", session_id="session_1")

        # 修復実行
        result = manager.repair_index()

        assert result["total_files"] == 2
        assert result["in_index_before"] == 2
        assert result["repaired"] is False
        assert len(result["missing_in_index"]) == 0

    def test_repair_index_with_missing_entries(self, tmp_path):
        """repair_index: index.jsonに欠落がある場合"""
        import json
        manager = FeedbackManager(project_path=tmp_path)

        # フィードバックを正常に追加
        fb1 = manager.add_feedback("Test 1", "Desc", agent_id="manager", session_id="session_1")

        # 2つ目のフィードバックを個別ファイルのみ作成（index.jsonに追加しない）
        fb2_id = "fb_20260201_120000_test1234"
        fb2_data = {
            "id": fb2_id,
            "title": "Orphaned feedback",
            "description": "This is not in index",
            "category": "bug",
            "priority": "high",
            "agent_id": "manager",
            "session_id": "session_1",
            "created_at": "2026-02-01T12:00:00",
            "status": "open",
            "metadata": {}
        }

        # 個別ファイルのみ作成
        orphan_file = manager.feedback_dir / f"{fb2_id}.json"
        with open(orphan_file, "w") as f:
            json.dump(fb2_data, f, indent=2, ensure_ascii=False)

        # 修復前の状態確認
        feedbacks_before = manager.list_feedbacks()
        assert len(feedbacks_before) == 1  # index.jsonには1つだけ

        # 修復実行
        result = manager.repair_index()

        assert result["total_files"] == 2
        assert result["in_index_before"] == 1
        assert result["repaired"] is True
        assert len(result["missing_in_index"]) == 1
        assert fb2_id in result["missing_in_index"]

        # 修復後の確認
        feedbacks_after = manager.list_feedbacks()
        assert len(feedbacks_after) == 2  # 2つになっているはず

        # 孤立していたフィードバックが取得できることを確認
        orphan = manager.get_feedback(fb2_id)
        assert orphan is not None
        assert orphan.title == "Orphaned feedback"

    def test_index_consistency_after_add(self, tmp_path):
        """add_feedback後のindex.jsonと個別ファイルの整合性"""
        import json
        manager = FeedbackManager(project_path=tmp_path)

        # フィードバックを追加
        fb = manager.add_feedback("Test", "Desc", agent_id="manager", session_id="session_1")

        # index.jsonに存在することを確認
        with open(manager.index_file) as f:
            index_data = json.load(f)

        assert len(index_data) == 1
        assert index_data[0]["id"] == fb.id
        assert index_data[0]["title"] == "Test"

        # 個別ファイルに存在することを確認
        feedback_file = manager.feedback_dir / f"{fb.id}.json"
        assert feedback_file.exists()

        with open(feedback_file) as f:
            file_data = json.load(f)

        assert file_data["id"] == fb.id
        assert file_data["title"] == "Test"

    def test_index_consistency_after_update(self, tmp_path):
        """update_status後のindex.jsonと個別ファイルの整合性"""
        import json
        manager = FeedbackManager(project_path=tmp_path)

        # フィードバックを追加
        fb = manager.add_feedback("Test", "Desc", agent_id="manager", session_id="session_1")

        # ステータスを更新
        manager.update_status(fb.id, "completed")

        # index.jsonが更新されていることを確認
        with open(manager.index_file) as f:
            index_data = json.load(f)

        assert index_data[0]["status"] == "completed"

        # 個別ファイルも更新されていることを確認
        feedback_file = manager.feedback_dir / f"{fb.id}.json"
        with open(feedback_file) as f:
            file_data = json.load(f)

        assert file_data["status"] == "completed"
