"""
Task Reporter Mixin - タスク報告・リトライ・再割り当て
"""
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

from mao.orchestrator.message_queue import MessageType, MessagePriority

if TYPE_CHECKING:
    from mao.orchestrator.task_dispatcher import TaskDispatcher, SubTask


class TaskReporterMixin:
    """タスク報告・リトライ・再割り当てを担当するミックスイン"""

    async def report_task_started(
        self: "TaskDispatcher", agent_id: str, subtask_id: str, description: str
    ) -> None:
        """エージェントがタスク開始を報告

        Args:
            agent_id: エージェントID
            subtask_id: サブタスクID
            description: タスク説明
        """
        await self.message_queue.send_message(
            message_type=MessageType.TASK_STARTED,
            sender=agent_id,
            receiver="cto",
            content=f"タスクを開始しました: {description}",
            priority=MessagePriority.MEDIUM,
            metadata={
                "subtask_id": subtask_id,
                "description": description,
            },
        )

        # サブタスクの状態を更新
        for subtask in self.current_subtasks:
            if subtask.subtask_id == subtask_id:
                subtask.status = "in_progress"
                break

    async def report_task_progress(
        self: "TaskDispatcher",
        agent_id: str,
        subtask_id: str,
        progress: str,
        percentage: Optional[int] = None
    ) -> None:
        """エージェントがタスク進捗を報告

        Args:
            agent_id: エージェントID
            subtask_id: サブタスクID
            progress: 進捗内容
            percentage: 進捗率（0-100）
        """
        await self.message_queue.send_message(
            message_type=MessageType.TASK_PROGRESS,
            sender=agent_id,
            receiver="cto",
            content=progress,
            priority=MessagePriority.LOW,
            metadata={
                "subtask_id": subtask_id,
                "percentage": percentage,
            },
        )

    async def report_task_completed(
        self: "TaskDispatcher", agent_id: str, subtask_id: str, result: str
    ) -> None:
        """エージェントがタスク完了を報告

        Args:
            agent_id: エージェントID
            subtask_id: サブタスクID
            result: 実行結果
        """
        await self.message_queue.send_message(
            message_type=MessageType.TASK_COMPLETED,
            sender=agent_id,
            receiver="cto",
            content=f"タスクが完了しました: {result[:100]}",
            priority=MessagePriority.HIGH,
            metadata={
                "subtask_id": subtask_id,
                "result": result,
            },
        )

        # サブタスクの状態を更新
        for subtask in self.current_subtasks:
            if subtask.subtask_id == subtask_id:
                subtask.status = "completed"
                subtask.result = result
                break

    async def report_task_failed(
        self: "TaskDispatcher", agent_id: str, subtask_id: str, error: str
    ) -> None:
        """エージェントがタスク失敗を報告

        Args:
            agent_id: エージェントID
            subtask_id: サブタスクID
            error: エラー内容
        """
        await self.message_queue.send_message(
            message_type=MessageType.TASK_FAILED,
            sender=agent_id,
            receiver="cto",
            content=f"タスクが失敗しました: {error}",
            priority=MessagePriority.URGENT,
            metadata={
                "subtask_id": subtask_id,
                "error": error,
            },
        )

        # サブタスクの状態を更新
        for subtask in self.current_subtasks:
            if subtask.subtask_id == subtask_id:
                subtask.status = "failed"
                break

    async def request_task_reassignment(
        self: "TaskDispatcher",
        subtask_id: str,
        reason: str,
        new_priority: Optional[str] = None
    ) -> bool:
        """タスクの再割り当てをリクエスト

        Args:
            subtask_id: サブタスクID
            reason: 再割り当て理由
            new_priority: 新しい優先度

        Returns:
            成功したかどうか
        """
        # サブタスクを検索
        subtask = None
        for st in self.current_subtasks:
            if st.subtask_id == subtask_id:
                subtask = st
                break

        if not subtask:
            logging.warning(f"Subtask {subtask_id} not found for reassignment")
            return False

        # 優先度を更新
        if new_priority:
            subtask.priority = new_priority

        # ステータスをリセット
        old_worker = subtask.agent_id
        subtask.status = "pending"
        subtask.agent_id = None
        subtask.result = None

        # メッセージを送信
        await self.message_queue.send_message(
            message_type=MessageType.REASSIGN_REQUEST,
            sender="cto",
            receiver="cto",  # 自分自身
            content=f"タスク {subtask_id} を再割り当て: {reason}",
            priority=MessagePriority.HIGH,
            metadata={
                "subtask_id": subtask_id,
                "reason": reason,
                "old_worker": old_worker,
                "new_priority": new_priority,
            },
        )

        logging.info(f"Task {subtask_id} reassignment requested: {reason}")
        return True

    async def retry_failed_task(
        self: "TaskDispatcher", subtask_id: str, max_retries: int = 3
    ) -> bool:
        """失敗したタスクをリトライ

        Args:
            subtask_id: サブタスクID
            max_retries: 最大リトライ回数

        Returns:
            リトライを開始したかどうか
        """
        # サブタスクを検索
        subtask = None
        for st in self.current_subtasks:
            if st.subtask_id == subtask_id:
                subtask = st
                break

        if not subtask or subtask.status != "failed":
            return False

        # メタデータからリトライ回数を取得
        retry_count = getattr(subtask, "retry_count", 0)

        if retry_count >= max_retries:
            logging.warning(f"Task {subtask_id} exceeded max retries ({max_retries})")
            return False

        # リトライ回数を更新
        subtask.retry_count = retry_count + 1  # type: ignore

        # 再割り当てをリクエスト
        await self.request_task_reassignment(
            subtask_id=subtask_id,
            reason=f"リトライ ({retry_count + 1}/{max_retries})",
            new_priority="high",
        )

        return True

    async def get_pending_tasks(self: "TaskDispatcher") -> List["SubTask"]:
        """未割り当てのタスクを取得

        Returns:
            未割り当てタスクのリスト
        """
        return [st for st in self.current_subtasks if st.status == "pending"]

    async def get_task_summary(self: "TaskDispatcher") -> Dict[str, Any]:
        """タスク全体のサマリーを取得

        Returns:
            サマリー情報
        """
        total = len(self.current_subtasks)
        pending = sum(1 for st in self.current_subtasks if st.status == "pending")
        in_progress = sum(1 for st in self.current_subtasks if st.status == "in_progress")
        completed = sum(1 for st in self.current_subtasks if st.status == "completed")
        failed = sum(1 for st in self.current_subtasks if st.status == "failed")

        return {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "failed": failed,
            "progress_percentage": (completed / total * 100) if total > 0 else 0,
        }
