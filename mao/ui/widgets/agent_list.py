"""Agent List Widget - エージェント一覧表示"""
from textual.widgets import Static
from rich.text import Text
from typing import Dict, Any


class AgentListWidget(Static, can_focus=True):
    """エージェント一覧を表示するウィジェット"""

    # ステータスカラー
    STATUS_COLORS = {
        "completed": "green",
        "running": "yellow",
        "waiting": "dim",
        "error": "red",
    }

    # ステータスアイコン
    STATUS_ICONS = {
        "completed": "✓",
        "running": "⚙",
        "waiting": "⏸",
        "error": "✗",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.selected_index = 0

    def update_agent(
        self,
        agent_id: str,
        status: str,
        task: str = "",
        tokens: int = 0,
        role: str = "",
    ):
        """エージェント情報を更新"""
        self.agents[agent_id] = {
            "status": status,
            "task": task,
            "tokens": tokens,
            "role": role or agent_id,
        }
        self.refresh_display()

    def remove_agent(self, agent_id: str):
        """エージェントを削除"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            self.refresh_display()

    def get_selected_agent(self) -> str:
        """選択中のエージェントIDを取得"""
        agent_ids = list(self.agents.keys())
        if agent_ids and 0 <= self.selected_index < len(agent_ids):
            return agent_ids[self.selected_index]
        return ""

    def select_next(self):
        """次のエージェントを選択"""
        if self.agents:
            self.selected_index = (self.selected_index + 1) % len(self.agents)
            self.refresh_display()

    def select_prev(self):
        """前のエージェントを選択"""
        if self.agents:
            self.selected_index = (self.selected_index - 1) % len(self.agents)
            self.refresh_display()

    def refresh_display(self):
        """表示を更新"""
        content = Text()
        content.append("[Agents]", style="bold")

        if self.agents:
            content.append(f" {len(self.agents)} active\n\n", style="dim")
        else:
            content.append("\n\n")

        if not self.agents:
            content.append("稼働中のエージェントはありません", style="dim")
        else:
            agent_ids = list(self.agents.keys())
            for idx, agent_id in enumerate(agent_ids):
                info = self.agents[agent_id]

                # ステータスに応じた色とアイコン
                status_key = self._normalize_status(info["status"])
                color = self.STATUS_COLORS.get(status_key, "white")
                icon = self.STATUS_ICONS.get(status_key, "●")

                # 選択中の表示
                prefix = "❯ " if idx == self.selected_index else "  "

                # エージェント名
                role_name = info.get("role", agent_id)
                content.append(f"{prefix}", style="cyan" if idx == self.selected_index else "dim")
                content.append(f"{icon} ", style=color)
                content.append(f"{role_name:<12}", style="bold" if idx == self.selected_index else "white")

                # ステータステキスト
                status_text = self._get_status_text(info["status"])
                content.append(f" {status_text:<12}", style=color)

                # トークン数
                if info.get("tokens", 0) > 0:
                    tokens_text = f"{info['tokens']:,}"
                    content.append(f" Tokens: {tokens_text}", style="dim")

                content.append("\n")

        self.update(content)

    def _normalize_status(self, status: str) -> str:
        """ステータスを正規化"""
        status_lower = status.lower()
        if "complete" in status_lower or status_lower == "active":
            return "completed"
        elif "running" in status_lower or "thinking" in status_lower:
            return "running"
        elif "error" in status_lower or "fail" in status_lower:
            return "error"
        else:
            return "waiting"

    def _get_status_text(self, status: str) -> str:
        """ステータステキストを取得"""
        status_map = {
            "completed": "Completed",
            "running": "Running...",
            "waiting": "Waiting",
            "error": "Error",
            "ACTIVE": "Completed",
            "THINKING": "Running...",
            "IDLE": "Waiting",
            "ERROR": "Error",
        }
        return status_map.get(status, status)
