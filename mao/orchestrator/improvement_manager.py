"""
Project Improvement Manager - プロジェクト改善タスク管理
"""
import json
import uuid
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
import logging


@dataclass
class Improvement:
    """改善タスク"""

    id: str
    title: str
    description: str
    category: str  # feature, bug, refactor, performance, documentation
    priority: str  # low, medium, high, critical
    status: str  # pending, in_progress, completed, cancelled
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None
    pr_url: Optional[str] = None
    branch_name: Optional[str] = None
    metadata: Optional[dict] = None

    def to_dict(self) -> dict:
        """辞書に変換"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Improvement":
        """辞書から作成"""
        return cls(**data)


class ImprovementManager:
    """プロジェクト改善タスク管理"""

    def __init__(
        self,
        project_path: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Args:
            project_path: プロジェクトパス
            logger: ロガー
        """
        self.project_path = project_path or Path.cwd()
        self.logger = logger or logging.getLogger(__name__)

        # 改善タスクディレクトリ
        self.improvements_dir = self.project_path / ".mao" / "improvements"
        self.improvements_dir.mkdir(parents=True, exist_ok=True)

        # インデックスファイル
        self.index_file = self.improvements_dir / "index.json"

        # メモリ内キャッシュ
        self.improvements: List[Improvement] = []

        # インデックスを読み込み
        self._load_index()

    def _load_index(self) -> None:
        """インデックスを読み込み"""
        if self.index_file.exists():
            try:
                with open(self.index_file) as f:
                    data = json.load(f)
                    self.improvements = [
                        Improvement.from_dict(item) for item in data
                    ]
            except Exception as e:
                self.logger.error(f"Failed to load improvements index: {e}")
                self.improvements = []

    def _save_index(self) -> None:
        """インデックスを保存"""
        try:
            with open(self.index_file, "w") as f:
                data = [imp.to_dict() for imp in self.improvements]
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save improvements index: {e}")

    def create_improvement(
        self,
        title: str,
        description: str,
        category: str = "feature",
        priority: str = "medium",
        metadata: Optional[dict] = None,
    ) -> Improvement:
        """改善タスクを作成

        Args:
            title: タイトル
            description: 説明
            category: カテゴリ
            priority: 優先度
            metadata: メタデータ

        Returns:
            作成された改善タスク
        """
        # IDを生成
        improvement_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        improvement = Improvement(
            id=improvement_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            status="pending",
            created_at=timestamp,
            updated_at=timestamp,
            metadata=metadata or {},
        )

        self.improvements.append(improvement)
        self._save_index()

        self.logger.info(f"Created improvement: {improvement_id}")
        return improvement

    def get_improvement(self, improvement_id: str) -> Optional[Improvement]:
        """改善タスクを取得

        Args:
            improvement_id: 改善タスクID

        Returns:
            改善タスク（存在しない場合はNone）
        """
        for imp in self.improvements:
            if imp.id == improvement_id or imp.id.endswith(improvement_id):
                return imp
        return None

    def list_improvements(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> List[Improvement]:
        """改善タスクを一覧取得

        Args:
            status: ステータスでフィルタ
            category: カテゴリでフィルタ
            priority: 優先度でフィルタ

        Returns:
            改善タスクのリスト
        """
        improvements = self.improvements

        if status:
            improvements = [imp for imp in improvements if imp.status == status]

        if category:
            improvements = [imp for imp in improvements if imp.category == category]

        if priority:
            improvements = [imp for imp in improvements if imp.priority == priority]

        # 優先度順でソート (critical > high > medium > low)
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        improvements.sort(
            key=lambda imp: (
                priority_order.get(imp.priority, 99),
                imp.created_at,
            ),
            reverse=False,
        )

        return improvements

    def update_status(
        self,
        improvement_id: str,
        status: str,
        pr_url: Optional[str] = None,
        branch_name: Optional[str] = None,
    ) -> bool:
        """改善タスクのステータスを更新

        Args:
            improvement_id: 改善タスクID
            status: 新しいステータス
            pr_url: PR URL（completedの場合）
            branch_name: ブランチ名

        Returns:
            成功したかどうか
        """
        improvement = self.get_improvement(improvement_id)
        if not improvement:
            return False

        improvement.status = status
        improvement.updated_at = datetime.utcnow().isoformat()

        if status == "completed":
            improvement.completed_at = datetime.utcnow().isoformat()

        if pr_url:
            improvement.pr_url = pr_url

        if branch_name:
            improvement.branch_name = branch_name

        self._save_index()
        self.logger.info(f"Updated improvement {improvement_id} status to {status}")
        return True

    def delete_improvement(self, improvement_id: str) -> bool:
        """改善タスクを削除

        Args:
            improvement_id: 改善タスクID

        Returns:
            成功したかどうか
        """
        improvement = self.get_improvement(improvement_id)
        if not improvement:
            return False

        self.improvements.remove(improvement)
        self._save_index()

        self.logger.info(f"Deleted improvement: {improvement_id}")
        return True

    def get_stats(self) -> dict:
        """統計情報を取得

        Returns:
            統計情報
        """
        total = len(self.improvements)
        pending = len([imp for imp in self.improvements if imp.status == "pending"])
        in_progress = len(
            [imp for imp in self.improvements if imp.status == "in_progress"]
        )
        completed = len(
            [imp for imp in self.improvements if imp.status == "completed"]
        )
        cancelled = len(
            [imp for imp in self.improvements if imp.status == "cancelled"]
        )

        return {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "cancelled": cancelled,
        }
