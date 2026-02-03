"""
Legacy Dashboard Widgets - 旧式のシンプルなウィジェット
"""
import time
from typing import List

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label, Input, Select


class AgentStatusWidget(Static, can_focus=True):
    """エージェント状態表示ウィジェット"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agents = {}

    def update_status(self, agent_id: str, status: str, task: str = ""):
        """エージェント状態を更新"""
        self.agents[agent_id] = {"status": status, "task": task}
        self.refresh_display()

    def refresh_display(self):
        """表示を更新"""
        lines = ["[bold]エージェント状態[/bold]\n"]

        if not self.agents:
            lines.append("[dim]稼働中のエージェントはありません[/dim]")
        else:
            for agent_id, info in self.agents.items():
                status_color = {
                    "ACTIVE": "green",
                    "THINKING": "yellow",
                    "IDLE": "dim",
                    "ERROR": "red",
                }.get(info["status"], "white")

                status_text = {
                    "ACTIVE": "実行中",
                    "THINKING": "思考中",
                    "IDLE": "待機中",
                    "ERROR": "エラー",
                }.get(info["status"], info["status"])

                lines.append(f"[{status_color}]●[/{status_color}] {agent_id}")
                lines.append(f"  状態: {status_text}")
                if info["task"]:
                    lines.append(f"  タスク: {info['task']}")
                lines.append("")

        self.update("\n".join(lines))


class TaskProgressWidget(Static):
    """タスク進捗表示ウィジェット"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield Label("[bold]タスク進捗[/bold]")
        yield Label("\n全体: [dim]実行中のタスクはありません[/dim]")


class LogViewerWidget(Static):
    """ログビューアーウィジェット"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logs: List[str] = []

    def add_log(self, message: str):
        """ログを追加"""
        timestamp = time.strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")

        # 最新100件のみ保持
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]

        self.refresh_display()

    def refresh_display(self):
        """表示を更新"""
        lines = ["[bold]アクティビティログ[/bold]\n"]
        if not self.logs:
            lines.append("[dim]まだアクティビティがありません[/dim]")
        else:
            lines.extend(self.logs[-20:])  # 最新20件を表示

        self.update("\n".join(lines))


class TaskControlPanel(Container):
    """タスク入力とエージェント起動のコントロールパネル"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        """UIコンポーネントを構築"""
        with Vertical():
            yield Label("[bold]タスクコントロール[/bold]")
            yield Input(placeholder="タスクを入力...", id="task_input")
            with Horizontal():
                yield Label("エージェント数:", classes="label")
                yield Select(
                    [(f"{i} Agents", i) for i in range(1, 9)],
                    value=3,
                    id="num_agents",
                )
                yield Button("起動", id="launch_task", variant="primary")
