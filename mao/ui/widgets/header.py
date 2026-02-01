"""Header Widget - タスク情報表示"""
from textual.widgets import Static
from rich.text import Text
from typing import Optional, Dict, Any


class HeaderWidget(Static):
    """タスク情報を表示するヘッダーウィジェット"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_description = ""
        self.active_count = 0
        self.total_count = 0
        self.selected_agent_id: Optional[str] = None
        self.selected_agent_info: Optional[Dict[str, Any]] = None

    def update_task_info(
        self, task_description: str, active_count: int = 0, total_count: int = 0
    ):
        """タスク情報を更新"""
        self.task_description = task_description
        self.active_count = active_count
        self.total_count = total_count
        self.refresh_display()

    def update_selected_agent(self, agent_id: str, agent_info: Dict[str, Any]):
        """選択されたエージェントの情報を更新"""
        self.selected_agent_id = agent_id
        self.selected_agent_info = agent_info
        self.refresh_display()

    def clear_selected_agent(self):
        """選択されたエージェントの情報をクリア"""
        self.selected_agent_id = None
        self.selected_agent_info = None
        self.refresh_display()

    def refresh_display(self):
        """表示を更新"""
        content = Text()

        # ヘッダー
        content.append("MAO - Multi-Agent Orchestrator\n", style="bold cyan")

        # タスク情報
        if self.task_description:
            content.append(f"Task: {self.task_description}\n", style="white")
            if self.total_count > 0:
                content.append(
                    f"Agents: {self.active_count}/{self.total_count} active\n",
                    style="dim"
                )
        else:
            content.append("待機中...\n", style="dim")

        # 選択されたエージェントの情報
        if self.selected_agent_id and self.selected_agent_info:
            content.append("\n", style="dim")
            content.append("─" * 50 + "\n", style="dim")
            content.append(f"Selected Agent: ", style="bold yellow")
            content.append(f"{self.selected_agent_id}\n", style="yellow")

            # ロール
            role = self.selected_agent_info.get("role", self.selected_agent_id)
            content.append(f"  Role: ", style="dim")
            content.append(f"{role}\n", style="white")

            # ステータス
            status = self.selected_agent_info.get("status", "unknown")
            status_color = self._get_status_color(status)
            content.append(f"  Status: ", style="dim")
            content.append(f"{status}\n", style=status_color)

            # 現在のタスク
            task = self.selected_agent_info.get("task", "")
            if task:
                content.append(f"  Task: ", style="dim")
                # 長いタスクは折り返す
                if len(task) > 45:
                    content.append(f"{task[:45]}...\n", style="white")
                else:
                    content.append(f"{task}\n", style="white")

            # トークン数
            tokens = self.selected_agent_info.get("tokens", 0)
            if tokens > 0:
                content.append(f"  Tokens: ", style="dim")
                content.append(f"{tokens:,}\n", style="cyan")

            # Worktree パス
            worktree_path = self.selected_agent_info.get("worktree_path", "")
            if worktree_path:
                content.append(f"  Worktree: ", style="dim")
                # パスの最後の部分のみ表示
                worktree_name = worktree_path.split("/")[-1] if "/" in worktree_path else worktree_path
                content.append(f"🌳 {worktree_name}", style="green")

        self.update(content)

    def _get_status_color(self, status: str) -> str:
        """ステータスに応じた色を返す"""
        status_lower = status.lower()
        if "complete" in status_lower or status_lower == "active":
            return "green"
        elif "running" in status_lower or "thinking" in status_lower:
            return "yellow"
        elif "error" in status_lower or "fail" in status_lower:
            return "red"
        else:
            return "dim"
