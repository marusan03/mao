"""
Tests for TaskDispatcher worker communication features
"""
import pytest
from pathlib import Path
from mao.orchestrator.task_dispatcher import TaskDispatcher, SubTask


class TestWorkerCommunication:
    """ワーカー通信機能のテスト"""

    @pytest.mark.asyncio
    async def test_report_task_started(self, tmp_path):
        """タスク開始報告"""
        dispatcher = TaskDispatcher(project_path=tmp_path)

        # サブタスクを作成
        subtask = SubTask(
            subtask_id="task-1",
            parent_task_id="parent-1",
            description="Test task",
            worker_id="worker-1",
        )
        dispatcher.current_subtasks = [subtask]

        # タスク開始を報告
        await dispatcher.report_task_started(
            worker_id="worker-1",
            subtask_id="task-1",
            description="Test task",
        )

        # サブタスクの状態が更新されたことを確認
        assert subtask.status == "in_progress"

        # メッセージが送信されたことを確認
        messages = await dispatcher.message_queue.get_messages(receiver="manager")
        assert len(messages) == 1
        assert messages[0].sender == "worker-1"
        assert "開始" in messages[0].content

    @pytest.mark.asyncio
    async def test_report_task_progress(self, tmp_path):
        """タスク進捗報告"""
        dispatcher = TaskDispatcher(project_path=tmp_path)

        await dispatcher.report_task_progress(
            worker_id="worker-1",
            subtask_id="task-1",
            progress="50% completed",
            percentage=50,
        )

        messages = await dispatcher.message_queue.get_messages(receiver="manager")
        assert len(messages) == 1
        assert messages[0].content == "50% completed"
        assert messages[0].metadata["percentage"] == 50

    @pytest.mark.asyncio
    async def test_report_task_completed(self, tmp_path):
        """タスク完了報告"""
        dispatcher = TaskDispatcher(project_path=tmp_path)

        # サブタスクを作成
        subtask = SubTask(
            subtask_id="task-1",
            parent_task_id="parent-1",
            description="Test task",
            worker_id="worker-1",
        )
        subtask.status = "in_progress"
        dispatcher.current_subtasks = [subtask]

        # タスク完了を報告
        await dispatcher.report_task_completed(
            worker_id="worker-1",
            subtask_id="task-1",
            result="Task completed successfully",
        )

        # サブタスクの状態が更新されたことを確認
        assert subtask.status == "completed"
        assert subtask.result == "Task completed successfully"

        # メッセージが送信されたことを確認
        messages = await dispatcher.message_queue.get_messages(receiver="manager")
        assert len(messages) == 1
        assert "完了" in messages[0].content

    @pytest.mark.asyncio
    async def test_report_task_failed(self, tmp_path):
        """タスク失敗報告"""
        dispatcher = TaskDispatcher(project_path=tmp_path)

        # サブタスクを作成
        subtask = SubTask(
            subtask_id="task-1",
            parent_task_id="parent-1",
            description="Test task",
            worker_id="worker-1",
        )
        subtask.status = "in_progress"
        dispatcher.current_subtasks = [subtask]

        # タスク失敗を報告
        await dispatcher.report_task_failed(
            worker_id="worker-1",
            subtask_id="task-1",
            error="Connection timeout",
        )

        # サブタスクの状態が更新されたことを確認
        assert subtask.status == "failed"

        # メッセージが送信されたことを確認
        messages = await dispatcher.message_queue.get_messages(receiver="manager")
        assert len(messages) == 1
        assert "失敗" in messages[0].content


class TestTaskReassignment:
    """タスク再割り当て機能のテスト"""

    @pytest.mark.asyncio
    async def test_request_task_reassignment(self, tmp_path):
        """タスク再割り当てリクエスト"""
        dispatcher = TaskDispatcher(project_path=tmp_path)

        # サブタスクを作成
        subtask = SubTask(
            subtask_id="task-1",
            parent_task_id="parent-1",
            description="Test task",
            worker_id="worker-1",
            priority="medium",
        )
        subtask.status = "failed"
        dispatcher.current_subtasks = [subtask]

        # 再割り当てをリクエスト
        success = await dispatcher.request_task_reassignment(
            subtask_id="task-1",
            reason="Worker failed",
            new_priority="high",
        )

        assert success is True

        # サブタスクが更新されたことを確認
        assert subtask.status == "pending"
        assert subtask.worker_id is None
        assert subtask.priority == "high"

        # メッセージが送信されたことを確認
        messages = await dispatcher.message_queue.get_messages(receiver="manager")
        assert len(messages) == 1
        assert "再割り当て" in messages[0].content

    @pytest.mark.asyncio
    async def test_request_reassignment_nonexistent_task(self, tmp_path):
        """存在しないタスクの再割り当てリクエスト"""
        dispatcher = TaskDispatcher(project_path=tmp_path)

        success = await dispatcher.request_task_reassignment(
            subtask_id="nonexistent",
            reason="Test",
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_retry_failed_task(self, tmp_path):
        """失敗したタスクのリトライ"""
        dispatcher = TaskDispatcher(project_path=tmp_path)

        # 失敗したサブタスクを作成
        subtask = SubTask(
            subtask_id="task-1",
            parent_task_id="parent-1",
            description="Test task",
            worker_id="worker-1",
        )
        subtask.status = "failed"
        dispatcher.current_subtasks = [subtask]

        # リトライ
        success = await dispatcher.retry_failed_task("task-1", max_retries=3)

        assert success is True
        assert subtask.retry_count == 1
        assert subtask.status == "pending"

    @pytest.mark.asyncio
    async def test_retry_exceeds_max_retries(self, tmp_path):
        """最大リトライ回数を超える"""
        dispatcher = TaskDispatcher(project_path=tmp_path)

        # 失敗したサブタスクを作成
        subtask = SubTask(
            subtask_id="task-1",
            parent_task_id="parent-1",
            description="Test task",
            worker_id="worker-1",
        )
        subtask.status = "failed"
        subtask.retry_count = 3  # type: ignore
        dispatcher.current_subtasks = [subtask]

        # リトライ（最大回数を超えている）
        success = await dispatcher.retry_failed_task("task-1", max_retries=3)

        assert success is False

    @pytest.mark.asyncio
    async def test_retry_non_failed_task(self, tmp_path):
        """失敗していないタスクのリトライ"""
        dispatcher = TaskDispatcher(project_path=tmp_path)

        # 完了したサブタスクを作成
        subtask = SubTask(
            subtask_id="task-1",
            parent_task_id="parent-1",
            description="Test task",
            worker_id="worker-1",
        )
        subtask.status = "completed"
        dispatcher.current_subtasks = [subtask]

        # リトライ（失敗していないのでFalse）
        success = await dispatcher.retry_failed_task("task-1")

        assert success is False


class TestTaskManagement:
    """タスク管理機能のテスト"""

    @pytest.mark.asyncio
    async def test_get_pending_tasks(self, tmp_path):
        """未割り当てタスクの取得"""
        dispatcher = TaskDispatcher(project_path=tmp_path)

        # 複数のサブタスクを作成
        subtask1 = SubTask(
            subtask_id="task-1",
            parent_task_id="parent-1",
            description="Task 1",
        )
        subtask1.status = "pending"

        subtask2 = SubTask(
            subtask_id="task-2",
            parent_task_id="parent-1",
            description="Task 2",
        )
        subtask2.status = "in_progress"

        subtask3 = SubTask(
            subtask_id="task-3",
            parent_task_id="parent-1",
            description="Task 3",
        )
        subtask3.status = "pending"

        dispatcher.current_subtasks = [subtask1, subtask2, subtask3]

        # 未割り当てタスクを取得
        pending = await dispatcher.get_pending_tasks()

        assert len(pending) == 2
        assert pending[0].subtask_id == "task-1"
        assert pending[1].subtask_id == "task-3"

    @pytest.mark.asyncio
    async def test_get_task_summary(self, tmp_path):
        """タスクサマリーの取得"""
        dispatcher = TaskDispatcher(project_path=tmp_path)

        # 様々な状態のサブタスクを作成
        for i in range(10):
            subtask = SubTask(
                subtask_id=f"task-{i}",
                parent_task_id="parent-1",
                description=f"Task {i}",
            )

            if i < 2:
                subtask.status = "pending"
            elif i < 5:
                subtask.status = "in_progress"
            elif i < 8:
                subtask.status = "completed"
            else:
                subtask.status = "failed"

            dispatcher.current_subtasks.append(subtask)

        # サマリーを取得
        summary = await dispatcher.get_task_summary()

        assert summary["total"] == 10
        assert summary["pending"] == 2
        assert summary["in_progress"] == 3
        assert summary["completed"] == 3
        assert summary["failed"] == 2
        assert summary["progress_percentage"] == 30.0  # 3/10 * 100

    @pytest.mark.asyncio
    async def test_get_task_summary_empty(self, tmp_path):
        """空のタスクサマリー"""
        dispatcher = TaskDispatcher(project_path=tmp_path)

        summary = await dispatcher.get_task_summary()

        assert summary["total"] == 0
        assert summary["progress_percentage"] == 0
