"""Simple Log Viewer Widget - シンプルなログビューア"""
from textual.widgets import Static
from rich.text import Text
from collections import deque
from typing import Deque, Dict


class SimpleLogViewer(Static, can_focus=True):
    """シンプルなログビューアウィジェット（エージェント別フィルタリング対応）"""

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

    BINDINGS = [
        ("up", "scroll_up", "Scroll Up"),
        ("down", "scroll_down", "Scroll Down"),
        ("pageup", "page_up", "Page Up"),
        ("pagedown", "page_down", "Page Down"),
    ]

    def __init__(self, *args, max_lines: int = 100, **kwargs):
        super().__init__(*args, **kwargs)
        # エージェント別にログを管理
        self.logs_by_agent: Dict[str, Deque[str]] = {}
        self.current_agent = ""  # 空文字列 = "All"
        self.max_lines = max_lines
        self.auto_scroll = True  # 自動スクロール有効

    def set_current_agent(self, agent_id: str):
        """表示するエージェントを設定

        Args:
            agent_id: エージェントID（空文字列で全ログ表示）
        """
        self.current_agent = agent_id
        self.refresh_display()

    def add_log(self, message: str, agent_id: str = "", level: str = "INFO"):
        """ログを追加

        Args:
            message: ログメッセージ
            agent_id: エージェントID（空文字列はシステムログ）
            level: ログレベル
        """
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        if agent_id:
            log_entry = f"{timestamp} | {level:<5} | [{agent_id}] {message}"
        else:
            log_entry = f"{timestamp} | {level:<5} | {message}"
            agent_id = "_system"  # システムログ用

        # エージェント別にログを保存
        if agent_id not in self.logs_by_agent:
            self.logs_by_agent[agent_id] = deque(maxlen=self.max_lines)

        self.logs_by_agent[agent_id].append(log_entry)

        # 現在表示中のエージェントのログなら更新
        if not self.current_agent or agent_id == self.current_agent:
            self.refresh_display()

    def clear_logs(self):
        """ログをクリア"""
        self.logs_by_agent.clear()
        self.refresh_display()

    def get_agent_ids(self) -> list[str]:
        """登録されているエージェントIDのリストを取得

        Returns:
            エージェントIDのリスト（_systemを除く）
        """
        return [aid for aid in self.logs_by_agent.keys() if aid != "_system"]

    def refresh_display(self):
        """表示を更新（current_agentに基づいてフィルタリング）"""
        content = Text()

        # ヘッダー
        if self.current_agent:
            content.append(f"[Log] {self.current_agent}", style="bold")
        else:
            content.append("[Log] All", style="bold")

        content.append("\n\n")

        # 表示するログを収集
        logs_to_display = []

        if not self.current_agent:
            # 全ログ表示（全エージェントのログを時系列順にマージ）
            for agent_id, logs in self.logs_by_agent.items():
                logs_to_display.extend(logs)
            # タイムスタンプでソート
            logs_to_display.sort()
        elif self.current_agent in self.logs_by_agent:
            # 特定エージェントのログのみ
            logs_to_display = list(self.logs_by_agent[self.current_agent])

        if not logs_to_display:
            content.append("ログはまだありません", style="dim")
        else:
            # ログを表示（最新が下）
            for log_entry in logs_to_display:
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
