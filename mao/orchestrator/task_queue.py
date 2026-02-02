"""
YAML-based task queue for inter-agent communication

Based on the pattern from multi-agent-shogun:
- Manager writes tasks to queue/tasks/<agent-id>.yaml
- Agents poll for their task file
- Agents write results to queue/results/<agent-id>.yaml
"""
import yaml
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
import logging


class TaskStatus(str, Enum):
    """タスクステータス"""
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class Task:
    """タスク定義"""
    task_id: str
    role: str  # 担当するロール（agent-1, agent-2, etc.）
    prompt: str  # claude-codeに渡すプロンプト
    model: str = "sonnet"
    status: TaskStatus = TaskStatus.PENDING
    assigned_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    result: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """辞書に変換"""
        data = asdict(self)
        # Enumを文字列に変換
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """辞書から作成"""
        # statusを文字列からEnumに変換
        if isinstance(data.get("status"), str):
            data["status"] = TaskStatus(data["status"])
        return cls(**data)


class TaskQueue:
    """YAMLベースのタスクキュー"""

    def __init__(
        self,
        project_path: Path,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Args:
            project_path: プロジェクトルートパス
            logger: ロガー
        """
        self.project_path = project_path
        self.logger = logger or logging.getLogger(__name__)

        # キューディレクトリ
        self.queue_dir = project_path / ".mao" / "queue"
        self.tasks_dir = self.queue_dir / "tasks"
        self.results_dir = self.queue_dir / "results"

        # ディレクトリ作成
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def assign_task(self, task: Task) -> bool:
        """タスクをエージェントに割り当て

        Args:
            task: 割り当てるタスク

        Returns:
            成功したかどうか
        """
        try:
            # タスクファイルのパス
            task_file = self.tasks_dir / f"{task.role}.yaml"

            # 既にタスクがある場合は警告
            if task_file.exists():
                self.logger.warning(
                    f"Task file already exists for {task.role}, overwriting"
                )

            # タスクをYAMLとして書き込み
            task.status = TaskStatus.ASSIGNED
            task.assigned_at = time.time()

            with task_file.open("w", encoding="utf-8") as f:
                yaml.dump(task.to_dict(), f, allow_unicode=True)

            self.logger.info(f"Task assigned to {task.role}: {task.task_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to assign task: {e}")
            return False

    def get_task(self, role: str) -> Optional[Task]:
        """エージェント用：自分のタスクを取得

        Args:
            role: ロール名（agent-1, agent-2, etc.）

        Returns:
            タスク、なければNone
        """
        try:
            task_file = self.tasks_dir / f"{role}.yaml"

            if not task_file.exists():
                return None

            # YAMLを読み込み
            with task_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            task = Task.from_dict(data)

            # タスクファイルを削除（取得済み）
            task_file.unlink()

            self.logger.info(f"Task retrieved by {role}: {task.task_id}")
            return task

        except Exception as e:
            self.logger.error(f"Failed to get task for {role}: {e}")
            return None

    def submit_result(self, task: Task) -> bool:
        """ワーカー用：タスク結果を提出

        Args:
            task: 完了したタスク

        Returns:
            成功したかどうか
        """
        try:
            result_file = self.results_dir / f"{task.role}.yaml"

            # 結果をYAMLとして書き込み
            with result_file.open("w", encoding="utf-8") as f:
                yaml.dump(task.to_dict(), f, allow_unicode=True)

            self.logger.info(f"Result submitted by {task.role}: {task.task_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to submit result: {e}")
            return False

    def get_result(self, role: str) -> Optional[Task]:
        """マネージャー用：ワーカーの結果を取得

        Args:
            role: ロール名

        Returns:
            結果タスク、なければNone
        """
        try:
            result_file = self.results_dir / f"{role}.yaml"

            if not result_file.exists():
                return None

            # YAMLを読み込み
            with result_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            task = Task.from_dict(data)

            # 結果ファイルを削除（取得済み）
            result_file.unlink()

            self.logger.info(f"Result retrieved for {role}: {task.task_id}")
            return task

        except Exception as e:
            self.logger.error(f"Failed to get result for {role}: {e}")
            return None

    def has_task(self, role: str) -> bool:
        """タスクが存在するかチェック

        Args:
            role: ロール名

        Returns:
            タスクが存在するか
        """
        task_file = self.tasks_dir / f"{role}.yaml"
        return task_file.exists()

    def has_result(self, role: str) -> bool:
        """結果が存在するかチェック

        Args:
            role: ロール名

        Returns:
            結果が存在するか
        """
        result_file = self.results_dir / f"{role}.yaml"
        return result_file.exists()

    def list_pending_tasks(self) -> List[str]:
        """未処理タスクのリストを取得

        Returns:
            ロール名のリスト
        """
        return [f.stem for f in self.tasks_dir.glob("*.yaml")]

    def list_completed_results(self) -> List[str]:
        """完了済み結果のリストを取得

        Returns:
            ロール名のリスト
        """
        return [f.stem for f in self.results_dir.glob("*.yaml")]

    def cleanup(self) -> None:
        """キューをクリーンアップ（全タスク・結果を削除）"""
        for task_file in self.tasks_dir.glob("*.yaml"):
            task_file.unlink()

        for result_file in self.results_dir.glob("*.yaml"):
            result_file.unlink()

        self.logger.info("Task queue cleaned up")
