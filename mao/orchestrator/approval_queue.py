"""
Approval Queue - CTOによるエージェント作業承認管理
"""
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import logging


class ApprovalStatus(Enum):
    """承認ステータス"""
    PENDING = "pending"  # 承認待ち
    APPROVED = "approved"  # 承認済み
    REJECTED = "rejected"  # 却下
    IN_REVIEW = "in_review"  # レビュー中


@dataclass
class ApprovalItem:
    """承認待ちアイテム"""
    id: str
    agent_id: str
    task_number: int
    task_description: str
    role: str
    model: str
    status: str
    created_at: str
    reviewed_at: Optional[str] = None
    reviewer_feedback: Optional[str] = None
    pane_id: Optional[str] = None
    worktree: Optional[Path] = None
    branch: Optional[str] = None
    changed_files: Optional[List[str]] = None
    output: Optional[str] = None

    def to_dict(self) -> dict:
        """辞書に変換"""
        data = asdict(self)
        if self.worktree:
            data['worktree'] = str(self.worktree)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ApprovalItem":
        """辞書から作成"""
        # 後方互換性: worker_id が存在する場合は agent_id に変換
        if 'worker_id' in data and 'agent_id' not in data:
            data['agent_id'] = data.pop('worker_id')

        if 'worktree' in data and data['worktree']:
            data['worktree'] = Path(data['worktree'])
        return cls(**data)


class ApprovalQueue:
    """承認キュー管理"""

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

        # 承認キューディレクトリ
        self.queue_dir = self.project_path / ".mao" / "approval_queue"
        self.queue_dir.mkdir(parents=True, exist_ok=True)

        # インデックスファイル
        self.index_file = self.queue_dir / "index.json"

        # メモリ内キャッシュ
        self.items: List[ApprovalItem] = []

        # インデックスを読み込み
        self._load_index()

    def _load_index(self) -> None:
        """インデックスを読み込み"""
        if self.index_file.exists():
            try:
                with open(self.index_file) as f:
                    data = json.load(f)
                    self.items = [ApprovalItem.from_dict(item) for item in data]
            except Exception as e:
                self.logger.error(f"Failed to load approval queue index: {e}")
                self.items = []

    def _save_index(self) -> None:
        """インデックスを保存"""
        try:
            with open(self.index_file, "w") as f:
                data = [item.to_dict() for item in self.items]
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save approval queue index: {e}")

    def add_item(
        self,
        agent_id: str,
        task_number: int,
        task_description: str,
        role: str,
        model: str,
        pane_id: Optional[str] = None,
        worktree: Optional[Path] = None,
        branch: Optional[str] = None,
        changed_files: Optional[List[str]] = None,
        output: Optional[str] = None,
    ) -> ApprovalItem:
        """承認アイテムを追加

        Args:
            agent_id: エージェントID
            task_number: タスク番号
            task_description: タスク説明
            role: MAOロール名
            model: モデル
            pane_id: tmuxペインID
            worktree: worktreeパス
            branch: ブランチ名
            changed_files: 変更ファイルリスト
            output: エージェントの出力

        Returns:
            作成された承認アイテム
        """
        item_id = str(uuid.uuid4())[:8]
        timestamp = datetime.utcnow().isoformat()

        item = ApprovalItem(
            id=item_id,
            agent_id=agent_id,
            task_number=task_number,
            task_description=task_description,
            role=role,
            model=model,
            status=ApprovalStatus.PENDING.value,
            created_at=timestamp,
            pane_id=pane_id,
            worktree=worktree,
            branch=branch,
            changed_files=changed_files or [],
            output=output,
        )

        self.items.append(item)
        self._save_index()

        self.logger.info(f"Added approval item: {item_id} for {agent_id}")
        return item

    def get_item(self, item_id: str) -> Optional[ApprovalItem]:
        """承認アイテムを取得

        Args:
            item_id: アイテムID

        Returns:
            承認アイテム（存在しない場合はNone）
        """
        for item in self.items:
            if item.id == item_id or item.id.startswith(item_id):
                return item
        return None

    def get_pending_items(self) -> List[ApprovalItem]:
        """承認待ちアイテムを取得

        Returns:
            承認待ちアイテムのリスト
        """
        return [
            item for item in self.items
            if item.status == ApprovalStatus.PENDING.value
        ]

    def approve(
        self,
        item_id: str,
        feedback: Optional[str] = None
    ) -> bool:
        """アイテムを承認

        Args:
            item_id: アイテムID
            feedback: フィードバック

        Returns:
            成功したかどうか
        """
        item = self.get_item(item_id)
        if not item:
            return False

        item.status = ApprovalStatus.APPROVED.value
        item.reviewed_at = datetime.utcnow().isoformat()
        item.reviewer_feedback = feedback

        self._save_index()
        self.logger.info(f"Approved item: {item_id}")
        return True

    def reject(
        self,
        item_id: str,
        feedback: str
    ) -> bool:
        """アイテムを却下

        Args:
            item_id: アイテムID
            feedback: フィードバック（必須）

        Returns:
            成功したかどうか
        """
        item = self.get_item(item_id)
        if not item:
            return False

        item.status = ApprovalStatus.REJECTED.value
        item.reviewed_at = datetime.utcnow().isoformat()
        item.reviewer_feedback = feedback

        self._save_index()
        self.logger.info(f"Rejected item: {item_id} with feedback: {feedback}")
        return True

    def delete_item(self, item_id: str) -> bool:
        """アイテムを削除

        Args:
            item_id: アイテムID

        Returns:
            成功したかどうか
        """
        item = self.get_item(item_id)
        if not item:
            return False

        self.items.remove(item)
        self._save_index()

        self.logger.info(f"Deleted approval item: {item_id}")
        return True

    def clear_approved(self) -> int:
        """承認済みアイテムをクリア

        Returns:
            削除された件数
        """
        before_count = len(self.items)
        self.items = [
            item for item in self.items
            if item.status != ApprovalStatus.APPROVED.value
        ]
        deleted_count = before_count - len(self.items)

        if deleted_count > 0:
            self._save_index()
            self.logger.info(f"Cleared {deleted_count} approved items")

        return deleted_count

    def get_stats(self) -> Dict[str, int]:
        """統計情報を取得

        Returns:
            統計情報
        """
        total = len(self.items)
        pending = len([i for i in self.items if i.status == ApprovalStatus.PENDING.value])
        approved = len([i for i in self.items if i.status == ApprovalStatus.APPROVED.value])
        rejected = len([i for i in self.items if i.status == ApprovalStatus.REJECTED.value])

        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
        }
