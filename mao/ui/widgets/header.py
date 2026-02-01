"""Header Widget - タスク情報表示"""
from textual.widgets import Static
from rich.text import Text


class HeaderWidget(Static):
    """タスク情報を表示するヘッダーウィジェット"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_description = ""
        self.active_count = 0
        self.total_count = 0

    def update_task_info(
        self, task_description: str, active_count: int = 0, total_count: int = 0
    ):
        """タスク情報を更新"""
        self.task_description = task_description
        self.active_count = active_count
        self.total_count = total_count
        self.refresh_display()

    def refresh_display(self):
        """表示を更新"""
        if self.task_description:
            # タスク情報を表示
            content = Text()
            content.append("MAO - Multi-Agent Orchestrator\n", style="bold cyan")
            content.append(f"Task: {self.task_description}\n", style="white")

            if self.total_count > 0:
                content.append(
                    f"Agents: {self.active_count}/{self.total_count} active",
                    style="dim"
                )
        else:
            # タスクなし
            content = Text()
            content.append("MAO - Multi-Agent Orchestrator\n", style="bold cyan")
            content.append("待機中...", style="dim")

        self.update(content)
