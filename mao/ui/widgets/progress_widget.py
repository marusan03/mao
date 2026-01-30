"""
Progress widgets for dashboard
"""
from textual.widgets import Static, ProgressBar
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn


class TaskProgressWidget(Static):
    """タスク進捗表示ウィジェット（改善版）"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tasks = {}
        self.overall_progress = 0.0

    def update_task(self, task_id: str, name: str, progress: float, status: str = "in_progress"):
        """タスク進捗を更新

        Args:
            task_id: タスクID
            name: タスク名
            progress: 進捗率 (0.0-1.0)
            status: ステータス (pending, in_progress, completed, failed)
        """
        self.tasks[task_id] = {
            "name": name,
            "progress": progress,
            "status": status,
        }
        self._calculate_overall_progress()
        self.refresh_display()

    def remove_task(self, task_id: str):
        """タスクを削除"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._calculate_overall_progress()
            self.refresh_display()

    def _calculate_overall_progress(self):
        """全体進捗を計算"""
        if not self.tasks:
            self.overall_progress = 0.0
            return

        total = sum(task["progress"] for task in self.tasks.values())
        self.overall_progress = total / len(self.tasks)

    def refresh_display(self):
        """表示を更新"""
        lines = ["[bold]タスク進捗[/bold]\n"]

        if not self.tasks:
            lines.append("[dim]実行中のタスクはありません[/dim]")
        else:
            # 全体進捗
            overall_percent = int(self.overall_progress * 100)
            bar_length = 30
            filled = int(bar_length * self.overall_progress)
            bar = "█" * filled + "░" * (bar_length - filled)

            lines.append(f"全体: [{bar}] {overall_percent}%")
            lines.append("")

            # 個別タスク
            for task_id, task in self.tasks.items():
                status_icon = {
                    "pending": "⏳",
                    "in_progress": "⚙️",
                    "completed": "✓",
                    "failed": "✗",
                }.get(task["status"], "•")

                status_color = {
                    "pending": "yellow",
                    "in_progress": "cyan",
                    "completed": "green",
                    "failed": "red",
                }.get(task["status"], "white")

                percent = int(task["progress"] * 100)
                mini_bar_length = 15
                filled = int(mini_bar_length * task["progress"])
                mini_bar = "█" * filled + "░" * (mini_bar_length - filled)

                lines.append(f"[{status_color}]{status_icon}[/{status_color}] {task['name']}")
                lines.append(f"   [{mini_bar}] {percent}%")

        self.update("\n".join(lines))


class AgentActivityWidget(Static):
    """エージェント活動状況ウィジェット"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.activities = []
        self.max_activities = 10

    def add_activity(self, agent_id: str, activity: str, level: str = "info"):
        """活動を追加

        Args:
            agent_id: エージェントID
            activity: 活動内容
            level: レベル (info, success, warning, error)
        """
        import time

        timestamp = time.strftime("%H:%M:%S")

        icon = {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✗",
        }.get(level, "•")

        color = {
            "info": "cyan",
            "success": "green",
            "warning": "yellow",
            "error": "red",
        }.get(level, "white")

        self.activities.append({
            "timestamp": timestamp,
            "agent_id": agent_id,
            "activity": activity,
            "icon": icon,
            "color": color,
        })

        # 最新N件のみ保持
        if len(self.activities) > self.max_activities:
            self.activities = self.activities[-self.max_activities:]

        self.refresh_display()

    def refresh_display(self):
        """表示を更新"""
        lines = ["[bold]最近の活動[/bold]\n"]

        if not self.activities:
            lines.append("[dim]活動履歴がありません[/dim]")
        else:
            for activity in reversed(self.activities):  # 新しい順
                lines.append(
                    f"[{activity['color']}]{activity['icon']}[/{activity['color']}] "
                    f"[{activity['timestamp']}] "
                    f"[dim]{activity['agent_id']}:[/dim] {activity['activity']}"
                )

        self.update("\n".join(lines))


class MetricsWidget(Static):
    """メトリクス表示ウィジェット（Claude使用量含む）"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics = {
            "total_agents": 0,
            "active_agents": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0,
        }
        # Claude API制限（概算）
        self.rate_limit_tokens_per_minute = 400_000  # Tier 2の例
        self.rate_limit_requests_per_minute = 1000

    def update_metrics(self, **kwargs):
        """メトリクスを更新"""
        self.metrics.update(kwargs)
        self.refresh_display()

    def refresh_display(self):
        """表示を更新"""
        lines = ["[bold]統計情報[/bold]\n"]

        # エージェント
        lines.append(f"エージェント: {self.metrics['total_agents']}")
        lines.append(f"稼働中: [green]{self.metrics['active_agents']}[/green]")
        lines.append("")

        # タスク
        total_tasks = self.metrics['completed_tasks'] + self.metrics['failed_tasks']
        if total_tasks > 0:
            success_rate = self.metrics['completed_tasks'] / total_tasks * 100
            lines.append(f"タスク: {total_tasks}件")
            lines.append(f"成功率: [green]{success_rate:.1f}%[/green]")
        else:
            lines.append(f"タスク: 0件")
        lines.append("")

        # Claude使用量
        lines.append("[bold cyan]Claude使用量[/bold cyan]")
        tokens = self.metrics['total_tokens']
        cost = self.metrics['estimated_cost']

        # トークン表示
        if tokens >= 1_000_000:
            lines.append(f"トークン: {tokens / 1_000_000:.2f}M")
        elif tokens >= 1_000:
            lines.append(f"トークン: {tokens / 1_000:.1f}K")
        else:
            lines.append(f"トークン: {tokens}")

        # コスト表示
        if cost >= 1.0:
            lines.append(f"概算コスト: [yellow]${cost:.2f}[/yellow]")
        else:
            lines.append(f"概算コスト: ${cost:.4f}")

        # 参考情報
        lines.append("")
        lines.append("[dim]※ 実際の使用量と制限は[/dim]")
        lines.append("[dim]Anthropic Console で確認[/dim]")

        self.update("\n".join(lines))
