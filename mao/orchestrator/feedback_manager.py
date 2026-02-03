"""
Feedback Manager - MAO への改善提案を管理
"""
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import logging


@dataclass
class Feedback:
    """フィードバック"""

    id: str
    title: str
    description: str
    category: str  # "bug", "feature", "improvement", "documentation"
    priority: str  # "low", "medium", "high", "critical"
    agent_id: str
    session_id: str
    created_at: str
    status: str = "open"  # "open", "in_progress", "completed", "rejected"
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """辞書に変換"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "priority": self.priority,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "status": self.status,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Feedback":
        """辞書から作成"""
        return cls(**data)


class FeedbackManager:
    """フィードバック管理"""

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

        # フィードバックディレクトリ
        self.feedback_dir = self.project_path / ".mao" / "feedback"
        self.feedback_dir.mkdir(parents=True, exist_ok=True)

        # フィードバック一覧ファイル
        self.index_file = self.feedback_dir / "index.json"

    def _load_index(self) -> List[Dict[str, Any]]:
        """インデックスを読み込み"""
        if self.index_file.exists():
            try:
                with open(self.index_file) as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load feedback index: {e}")
                return []
        return []

    def _save_index(self, feedbacks: List[Dict[str, Any]]) -> None:
        """インデックスを保存（アトミック書き込み）"""
        import tempfile
        import os

        try:
            # 一時ファイルに書き込み
            fd, temp_path = tempfile.mkstemp(
                dir=self.feedback_dir,
                prefix=".index_",
                suffix=".json.tmp"
            )

            with os.fdopen(fd, "w") as f:
                json.dump(feedbacks, f, indent=2, ensure_ascii=False)

            # アトミックにリネーム（既存ファイルを上書き）
            os.replace(temp_path, self.index_file)

        except Exception as e:
            self.logger.error(f"Failed to save feedback index: {e}")
            # 一時ファイルが残っている場合は削除
            if 'temp_path' in locals() and Path(temp_path).exists():
                try:
                    os.unlink(temp_path)
                except:
                    pass
            raise  # エラーを上位に伝播

    def add_feedback(
        self,
        title: str,
        description: str,
        category: str = "improvement",
        priority: str = "medium",
        agent_id: str = "unknown",
        session_id: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Feedback:
        """フィードバックを追加

        Args:
            title: タイトル
            description: 詳細説明
            category: カテゴリ（bug, feature, improvement, documentation）
            priority: 優先度（low, medium, high, critical）
            agent_id: エージェントID
            session_id: セッションID
            metadata: メタデータ

        Returns:
            追加されたフィードバック
        """
        # フィードバックID生成
        feedback_id = f"fb_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

        feedback = Feedback(
            id=feedback_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            agent_id=agent_id,
            session_id=session_id,
            created_at=datetime.utcnow().isoformat(),
            status="open",
            metadata=metadata,
        )

        # 個別ファイルに保存（先に実行してエラーチェック）
        feedback_file = self.feedback_dir / f"{feedback_id}.json"
        try:
            with open(feedback_file, "w") as f:
                json.dump(feedback.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save feedback file: {e}")
            raise  # ファイル書き込み失敗時は処理を中断

        # インデックスに追加（個別ファイル保存成功後のみ）
        try:
            feedbacks = self._load_index()
            feedbacks.append(feedback.to_dict())
            self._save_index(feedbacks)
        except Exception as e:
            # index.json更新失敗時は個別ファイルを削除してロールバック
            self.logger.error(f"Failed to update index, rolling back: {e}")
            try:
                feedback_file.unlink()
            except:
                pass
            raise

        self.logger.info(f"Added feedback: {feedback_id} - {title}")
        return feedback

    def get_feedback(self, feedback_id: str) -> Optional[Feedback]:
        """フィードバックを取得

        Args:
            feedback_id: フィードバックID

        Returns:
            フィードバック（存在しない場合はNone）
        """
        feedback_file = self.feedback_dir / f"{feedback_id}.json"
        if feedback_file.exists():
            try:
                with open(feedback_file) as f:
                    data = json.load(f)
                    return Feedback.from_dict(data)
            except Exception as e:
                self.logger.error(f"Failed to load feedback: {e}")

        return None

    def list_feedbacks(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> List[Feedback]:
        """フィードバック一覧を取得

        Args:
            status: ステータスでフィルタ（open, in_progress, completed, rejected）
            category: カテゴリでフィルタ
            priority: 優先度でフィルタ

        Returns:
            フィードバックのリスト
        """
        feedbacks = self._load_index()
        results = []

        for fb_data in feedbacks:
            # フィルタ適用
            if status and fb_data.get("status") != status:
                continue
            if category and fb_data.get("category") != category:
                continue
            if priority and fb_data.get("priority") != priority:
                continue

            results.append(Feedback.from_dict(fb_data))

        # 作成日時の降順でソート
        results.sort(key=lambda fb: fb.created_at, reverse=True)

        return results

    def update_status(self, feedback_id: str, status: str) -> bool:
        """フィードバックのステータスを更新

        Args:
            feedback_id: フィードバックID
            status: 新しいステータス

        Returns:
            成功したかどうか
        """
        feedback = self.get_feedback(feedback_id)
        if not feedback:
            return False

        # 古いステータスを保存（ロールバック用）
        old_status = feedback.status
        feedback.status = status

        # 個別ファイルを更新（先に実行）
        feedback_file = self.feedback_dir / f"{feedback_id}.json"
        try:
            with open(feedback_file, "w") as f:
                json.dump(feedback.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to update feedback file: {e}")
            return False

        # インデックスを更新（個別ファイル更新成功後のみ）
        try:
            feedbacks = self._load_index()
            for i, fb in enumerate(feedbacks):
                if fb["id"] == feedback_id:
                    feedbacks[i]["status"] = status
                    break

            self._save_index(feedbacks)
            return True

        except Exception as e:
            # index.json更新失敗時は個別ファイルをロールバック
            self.logger.error(f"Failed to update index, rolling back: {e}")
            feedback.status = old_status
            try:
                with open(feedback_file, "w") as f:
                    json.dump(feedback.to_dict(), f, indent=2, ensure_ascii=False)
            except:
                pass
            return False

    def delete_feedback(self, feedback_id: str) -> bool:
        """フィードバックを削除

        Args:
            feedback_id: フィードバックID

        Returns:
            成功したかどうか
        """
        # インデックスから削除
        feedbacks = self._load_index()
        feedbacks = [fb for fb in feedbacks if fb["id"] != feedback_id]
        self._save_index(feedbacks)

        # 個別ファイルを削除
        feedback_file = self.feedback_dir / f"{feedback_id}.json"
        if feedback_file.exists():
            try:
                feedback_file.unlink()
                self.logger.info(f"Deleted feedback: {feedback_id}")
                return True
            except Exception as e:
                self.logger.error(f"Failed to delete feedback: {e}")

        return False

    def get_stats(self) -> Dict[str, Any]:
        """フィードバック統計を取得

        Returns:
            統計情報
        """
        feedbacks = self._load_index()

        stats = {
            "total": len(feedbacks),
            "open": sum(1 for fb in feedbacks if fb.get("status") == "open"),
            "in_progress": sum(1 for fb in feedbacks if fb.get("status") == "in_progress"),
            "completed": sum(1 for fb in feedbacks if fb.get("status") == "completed"),
            "rejected": sum(1 for fb in feedbacks if fb.get("status") == "rejected"),
            "by_category": {},
            "by_priority": {},
        }

        # カテゴリ別集計
        for fb in feedbacks:
            category = fb.get("category", "unknown")
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

        # 優先度別集計
        for fb in feedbacks:
            priority = fb.get("priority", "unknown")
            stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1

        return stats

    def repair_index(self) -> Dict[str, Any]:
        """index.jsonを修復（個別ファイルから再構築）

        Returns:
            修復結果の統計情報
        """
        # 既存のindex.jsonを読み込み
        existing_feedbacks = self._load_index()
        existing_ids = {fb["id"] for fb in existing_feedbacks}

        # 個別ファイルから全feedbackを読み込み
        all_feedbacks = []
        missing_in_index = []

        for feedback_file in sorted(self.feedback_dir.glob("fb_*.json")):
            try:
                with open(feedback_file) as f:
                    fb_data = json.load(f)
                    all_feedbacks.append(fb_data)

                    # index.jsonに存在しないfeedbackを記録
                    if fb_data["id"] not in existing_ids:
                        missing_in_index.append(fb_data["id"])

            except Exception as e:
                self.logger.error(f"Failed to load {feedback_file}: {e}")

        # 作成日時でソート
        all_feedbacks.sort(key=lambda x: x.get("created_at", ""))

        # index.jsonを更新
        if missing_in_index:
            self._save_index(all_feedbacks)
            self.logger.info(f"Repaired index.json: added {len(missing_in_index)} missing feedbacks")

        return {
            "total_files": len(all_feedbacks),
            "in_index_before": len(existing_ids),
            "missing_in_index": missing_in_index,
            "repaired": len(missing_in_index) > 0,
        }
