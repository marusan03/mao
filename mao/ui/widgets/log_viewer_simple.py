"""Simple Log Viewer Widget - シンプルなログビューア"""
from textual.widgets import Static
from rich.text import Text
from collections import deque
from typing import Deque


class SimpleLogViewer(Static, can_focus=True):
    """シンプルなログビューアウィジェット"""

    # ログレベルカラー
    LOG_COLORS = {
        "INFO": "cyan",
        "DEBUG": "dim",
        "WARN": "yellow",
        "ERROR": "red",
        "TOOL": "magenta",
        "THINKING": "blue",
        "ACTION": "green",
        "RESULT": "bright_green",
    }

    def __init__(self, *args, max_lines: int = 100, **kwargs):
        super().__init__(*args, **kwargs)
        self.logs: Deque[str] = deque(maxlen=max_lines)
        self.current_agent = ""
        self.max_lines = max_lines
        self.auto_scroll = True  # 自動スクロール有効

    def set_current_agent(self, agent_id: str):
        """表示するエージェントを設定"""
        self.current_agent = agent_id
        self.refresh_display()

    def add_log(self, message: str, agent_id: str = "", level: str = "INFO"):
        """ログを追加"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        if agent_id:
            log_entry = f"{timestamp} | {level:<5} | [{agent_id}] {message}"
        else:
            log_entry = f"{timestamp} | {level:<5} | {message}"

        self.logs.append(log_entry)

        # 現在表示中のエージェントのログなら更新
        if not self.current_agent or agent_id == self.current_agent or not agent_id:
            self.refresh_display()

    def clear_logs(self):
        """ログをクリア"""
        self.logs.clear()
        self.refresh_display()

    def refresh_display(self):
        """表示を更新"""
        content = Text()

        # ヘッダー
        if self.current_agent:
            content.append(f"[Log] {self.current_agent}", style="bold")
        else:
            content.append("[Log] All", style="bold")

        content.append("\n\n")

        if not self.logs:
            content.append("ログはまだありません", style="dim")
        else:
            # ログを表示（最新が下）
            for log_entry in self.logs:
                # ログレベルに応じて色付け
                colored_entry = self._colorize_log(log_entry)
                content.append(colored_entry)
                content.append("\n")

        self.update(content)

        # 自動スクロールが有効なら最下部にスクロール
        if self.auto_scroll:
            self.scroll_end(animate=False)

    def _colorize_log(self, log_entry: str) -> Text:
        """ログエントリに色を付ける"""
        text = Text()

        # ログレベルを検出
        for level, color in self.LOG_COLORS.items():
            if f"| {level} |" in log_entry:
                # タイムスタンプ
                parts = log_entry.split("|", 2)
                if len(parts) >= 3:
                    text.append(parts[0] + "|", style="dim")
                    text.append(f" {level} ", style=color)
                    text.append("|" + parts[2], style="white")
                    return text

        # デフォルト
        text.append(log_entry, style="white")
        return text
