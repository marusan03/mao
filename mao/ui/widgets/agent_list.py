"""Agent List Widget - エージェント一覧表示"""
from textual.widgets import Static
from rich.text import Text
from typing import Dict, Any, Optional, Callable


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

    BINDINGS = [
        ("up", "select_previous_agent", "Select Previous"),
        ("down", "select_next_agent", "Select Next"),
        ("pageup", "page_up", "Page Up"),
        ("pagedown", "page_down", "Page Down"),
    ]

    def __init__(self, *args, on_selection_changed: Optional[Callable[[str, Dict[str, Any]], None]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.selected_index = 0
        self.on_selection_changed = on_selection_changed

    def update_agent(
        self,
        agent_id: str,
        status: str,
        task: str = "",
        tokens: int = 0,
        role: str = "",
        worktree_path: str = "",
    ):
        """エージェント情報を更新"""
        self.agents[agent_id] = {
            "status": status,
            "task": task,
            "tokens": tokens,
            "role": role or agent_id,
            "worktree_path": worktree_path,
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
            self._notify_selection_changed()

    def select_prev(self):
        """前のエージェントを選択"""
        if self.agents:
            self.selected_index = (self.selected_index - 1) % len(self.agents)
            self.refresh_display()
            self._notify_selection_changed()

    def _notify_selection_changed(self):
        """選択変更を通知"""
        if self.on_selection_changed:
            agent_id = self.get_selected_agent()
            if agent_id and agent_id in self.agents:
                self.on_selection_changed(agent_id, self.agents[agent_id])

    def action_select_next_agent(self):
        """次のエージェントを選択（キーボードアクション）"""
        self.select_next()

    def action_select_previous_agent(self):
        """前のエージェントを選択（キーボードアクション）"""
        self.select_prev()

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

                # エージェント名とロール
                role_name = info.get("role", agent_id)
                content.append(f"{prefix}", style="cyan" if idx == self.selected_index else "dim")
                content.append(f"{icon} ", style=color)
                content.append(f"{role_name:<12}", style="bold" if idx == self.selected_index else "white")

                # ステータステキスト
                status_text = self._get_status_text(info["status"])
                content.append(f" {status_text:<12}", style=color)

                # Worktree 情報
                worktree_path = info.get("worktree_path", "")
                if worktree_path:
                    content.append(" 🌳", style="green")
                    # パスの最後の部分のみ表示
                    worktree_name = worktree_path.split("/")[-1] if "/" in worktree_path else worktree_path
                    content.append(f" {worktree_name[:20]}", style="dim")

                content.append("\n")

                # トークン数（2行目）
                if info.get("tokens", 0) > 0:
                    tokens_text = f"{info['tokens']:,}"
                    content.append(f"  │ Tokens: {tokens_text}", style="dim")
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
