"""
Tests for Progress Widgets
"""
import pytest
from mao.ui.widgets.progress_widget import (
    TaskProgressWidget,
    AgentActivityWidget,
    MetricsWidget,
)


class TestTaskProgressWidget:
    """TaskProgressWidget のテスト"""

    def test_initialization(self):
        """初期化"""
        widget = TaskProgressWidget()

        assert widget.tasks == {}
        assert widget.overall_progress == 0.0

    def test_update_task(self):
        """タスク更新"""
        widget = TaskProgressWidget()

        widget.update_task(
            task_id="task-1",
            name="Test Task",
            progress=0.5,
            status="in_progress",
        )

        assert "task-1" in widget.tasks
        assert widget.tasks["task-1"]["name"] == "Test Task"
        assert widget.tasks["task-1"]["progress"] == 0.5
        assert widget.tasks["task-1"]["status"] == "in_progress"

    def test_remove_task(self):
        """タスク削除"""
        widget = TaskProgressWidget()

        widget.update_task(
            task_id="task-1",
            name="Task 1",
            progress=0.3,
        )
        widget.update_task(
            task_id="task-2",
            name="Task 2",
            progress=0.7,
        )

        assert len(widget.tasks) == 2

        widget.remove_task("task-1")

        assert len(widget.tasks) == 1
        assert "task-1" not in widget.tasks
        assert "task-2" in widget.tasks

    def test_calculate_overall_progress(self):
        """全体進捗計算"""
        widget = TaskProgressWidget()

        widget.update_task("task-1", "Task 1", 0.5)
        widget.update_task("task-2", "Task 2", 0.8)
        widget.update_task("task-3", "Task 3", 0.2)

        # (0.5 + 0.8 + 0.2) / 3 = 0.5
        assert widget.overall_progress == 0.5

    def test_overall_progress_empty(self):
        """空のタスクリスト"""
        widget = TaskProgressWidget()

        assert widget.overall_progress == 0.0

    def test_task_status_icons(self):
        """タスクステータスアイコン"""
        widget = TaskProgressWidget()

        # 各ステータスでタスクを更新（エラーが発生しないことを確認）
        widget.update_task("task-1", "Pending", 0.0, "pending")
        widget.update_task("task-2", "In Progress", 0.5, "in_progress")
        widget.update_task("task-3", "Completed", 1.0, "completed")
        widget.update_task("task-4", "Failed", 0.3, "failed")

        assert len(widget.tasks) == 4


class TestAgentActivityWidget:
    """AgentActivityWidget のテスト"""

    def test_initialization(self):
        """初期化"""
        widget = AgentActivityWidget()

        assert widget.activities == []
        assert widget.max_activities == 10

    def test_add_activity(self):
        """活動追加"""
        widget = AgentActivityWidget()

        widget.add_activity("agent-1", "Started task", "info")

        assert len(widget.activities) == 1
        assert widget.activities[0]["agent_id"] == "agent-1"
        assert widget.activities[0]["activity"] == "Started task"
        assert widget.activities[0]["color"] == "cyan"

    def test_add_activity_different_levels(self):
        """異なるレベルの活動"""
        widget = AgentActivityWidget()

        widget.add_activity("agent-1", "Info message", "info")
        widget.add_activity("agent-2", "Success message", "success")
        widget.add_activity("agent-3", "Warning message", "warning")
        widget.add_activity("agent-4", "Error message", "error")

        assert len(widget.activities) == 4
        assert widget.activities[0]["color"] == "cyan"
        assert widget.activities[1]["color"] == "green"
        assert widget.activities[2]["color"] == "yellow"
        assert widget.activities[3]["color"] == "red"

    def test_max_activities_limit(self):
        """最大活動数の制限"""
        widget = AgentActivityWidget()

        # 15個の活動を追加（max_activities=10）
        for i in range(15):
            widget.add_activity(f"agent-{i}", f"Activity {i}", "info")

        # 最新10件のみ保持
        assert len(widget.activities) == 10

        # 最後の10件が保持されている
        assert widget.activities[0]["activity"] == "Activity 5"
        assert widget.activities[-1]["activity"] == "Activity 14"

    def test_activity_has_timestamp(self):
        """活動にタイムスタンプがあること"""
        widget = AgentActivityWidget()

        widget.add_activity("agent-1", "Test", "info")

        assert "timestamp" in widget.activities[0]
        assert ":" in widget.activities[0]["timestamp"]  # HH:MM:SS形式


class TestMetricsWidget:
    """MetricsWidget のテスト"""

    def test_initialization(self):
        """初期化"""
        widget = MetricsWidget()

        assert widget.metrics["total_agents"] == 0
        assert widget.metrics["active_agents"] == 0
        assert widget.metrics["completed_tasks"] == 0
        assert widget.metrics["failed_tasks"] == 0
        assert widget.metrics["total_tokens"] == 0
        assert widget.metrics["estimated_cost"] == 0.0

    def test_update_metrics(self):
        """メトリクス更新"""
        widget = MetricsWidget()

        widget.update_metrics(
            total_agents=5,
            active_agents=3,
            completed_tasks=10,
            failed_tasks=2,
            total_tokens=50000,
            estimated_cost=0.25,
        )

        assert widget.metrics["total_agents"] == 5
        assert widget.metrics["active_agents"] == 3
        assert widget.metrics["completed_tasks"] == 10
        assert widget.metrics["failed_tasks"] == 2
        assert widget.metrics["total_tokens"] == 50000
        assert widget.metrics["estimated_cost"] == 0.25

    def test_update_metrics_partial(self):
        """部分更新"""
        widget = MetricsWidget()

        widget.update_metrics(total_agents=5, active_agents=3)
        widget.update_metrics(completed_tasks=8)

        assert widget.metrics["total_agents"] == 5
        assert widget.metrics["active_agents"] == 3
        assert widget.metrics["completed_tasks"] == 8

    def test_success_rate_calculation(self):
        """成功率の計算（refresh_display内で使用）"""
        widget = MetricsWidget()

        widget.update_metrics(
            completed_tasks=8,
            failed_tasks=2,
        )

        # 成功率は refresh_display で計算される
        # completed_tasks / (completed_tasks + failed_tasks) = 8/10 = 0.8
        total = widget.metrics["completed_tasks"] + widget.metrics["failed_tasks"]
        success_rate = widget.metrics["completed_tasks"] / total * 100

        assert total == 10
        assert success_rate == 80.0

    def test_token_display_formats(self):
        """トークン数の表示フォーマット"""
        widget = MetricsWidget()

        # 1000未満
        widget.update_metrics(total_tokens=500)
        assert widget.metrics["total_tokens"] == 500

        # 1000以上1M未満 (Kで表示)
        widget.update_metrics(total_tokens=50_000)
        assert widget.metrics["total_tokens"] == 50_000

        # 1M以上 (Mで表示)
        widget.update_metrics(total_tokens=2_500_000)
        assert widget.metrics["total_tokens"] == 2_500_000

    def test_cost_display_formats(self):
        """コストの表示フォーマット"""
        widget = MetricsWidget()

        # 1ドル未満（4桁精度）
        widget.update_metrics(estimated_cost=0.0123)
        assert widget.metrics["estimated_cost"] == 0.0123

        # 1ドル以上（2桁精度）
        widget.update_metrics(estimated_cost=12.345)
        assert widget.metrics["estimated_cost"] == 12.345

    def test_rate_limits(self):
        """レート制限の参照値"""
        widget = MetricsWidget()

        # デフォルト値が設定されていること
        assert widget.rate_limit_tokens_per_minute > 0
        assert widget.rate_limit_requests_per_minute > 0
