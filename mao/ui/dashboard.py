"""
Main Textual dashboard
"""
from pathlib import Path
from typing import Optional
import time

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Button, Label
from textual.binding import Binding

from mao.orchestrator.project_loader import ProjectConfig
from mao.orchestrator.tmux_manager import TmuxManager
from mao.orchestrator.agent_logger import AgentLogger


class AgentStatusWidget(Static):
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
        lines = ["[bold]Agent Status[/bold]\n"]

        if not self.agents:
            lines.append("[dim]No active agents[/dim]")
        else:
            for agent_id, info in self.agents.items():
                status_color = {
                    "ACTIVE": "green",
                    "THINKING": "yellow",
                    "IDLE": "dim",
                    "ERROR": "red",
                }.get(info["status"], "white")

                lines.append(f"[{status_color}]●[/{status_color}] {agent_id}")
                lines.append(f"  Status: {info['status']}")
                if info["task"]:
                    lines.append(f"  Task: {info['task']}")
                lines.append("")

        self.update("\n".join(lines))


class TaskProgressWidget(Static):
    """タスク進捗表示ウィジェット"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield Label("[bold]Task Progress[/bold]")
        yield Label("\nOverall: [dim]No active tasks[/dim]")


class LogViewerWidget(Static):
    """ログビューアーウィジェット"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logs = []

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
        lines = ["[bold]Activity Log[/bold]\n"]
        if not self.logs:
            lines.append("[dim]No activity yet[/dim]")
        else:
            lines.extend(self.logs[-20:])  # 最新20件を表示

        self.update("\n".join(lines))


class Dashboard(App):
    """Main Textual dashboard"""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 3;
        grid-gutter: 1;
        padding: 1;
    }

    #agent_status {
        row-span: 2;
        border: solid green;
        padding: 1;
    }

    #task_progress {
        border: solid blue;
        padding: 1;
    }

    #approval_panel {
        border: solid yellow;
        padding: 1;
    }

    #log_viewer {
        column-span: 2;
        border: solid cyan;
        padding: 1;
        height: 100%;
    }

    Button {
        margin: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(
        self,
        project_path: Path,
        config: ProjectConfig,
        use_redis: bool = True,
        redis_url: Optional[str] = None,
        tmux_manager: Optional[TmuxManager] = None,
    ):
        super().__init__()
        self.project_path = project_path
        self.config = config
        self.use_redis = use_redis
        self.redis_url = redis_url
        self.tmux_manager = tmux_manager
        self.agents = {}

        # ログディレクトリ
        self.log_dir = project_path / ".mao" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # ウィジェット参照
        self.agent_status_widget = None
        self.log_viewer_widget = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        # エージェント状態
        self.agent_status_widget = AgentStatusWidget(id="agent_status")
        yield self.agent_status_widget

        # タスク進捗
        yield TaskProgressWidget(id="task_progress")

        # 承認パネル
        approval_panel = Container(id="approval_panel")
        with approval_panel:
            yield Label("[bold]Approval Panel[/bold]")
            yield Label("\n[dim]No pending approvals[/dim]")

        yield approval_panel

        # ログビューアー
        self.log_viewer_widget = LogViewerWidget(id="log_viewer")
        yield self.log_viewer_widget

        yield Footer()

    def on_mount(self) -> None:
        """アプリケーション起動時の処理"""
        self.title = f"MAO Dashboard - {self.config.project_name}"

        # 起動ログ
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log("Dashboard started")
            self.log_viewer_widget.add_log(f"Project: {self.config.project_name}")
            self.log_viewer_widget.add_log(f"Language: {self.config.default_language}")

            if self.tmux_manager:
                self.log_viewer_widget.add_log("tmux monitoring enabled")

    def action_refresh(self) -> None:
        """画面をリフレッシュ"""
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log("Dashboard refreshed")

        if self.agent_status_widget:
            self.agent_status_widget.refresh_display()

    def spawn_agent(self, role_name: str, task: dict) -> str:
        """エージェントを起動（ヘッドレス）"""
        agent_id = f"{role_name}-{int(time.time())}"

        # エージェント専用ロガー作成
        agent_logger = AgentLogger(
            agent_id=agent_id, agent_name=role_name, log_dir=self.log_dir
        )

        # tmuxペイン作成（ログファイルをtail）
        if self.tmux_manager:
            self.tmux_manager.create_pane_for_agent(
                agent_id=agent_id, agent_name=role_name, log_file=agent_logger.log_file
            )

        # ログに記録
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(f"Spawned agent: {agent_id}")

        # ステータス更新
        if self.agent_status_widget:
            self.agent_status_widget.update_status(
                agent_id, "ACTIVE", task.get("description", "")
            )

        # エージェント情報を保存
        self.agents[agent_id] = {
            "role": role_name,
            "logger": agent_logger,
            "task": task,
        }

        # TODO: 実際のエージェント起動処理
        # agent_logger.info(f"Starting {role_name} agent")
        # agent_logger.thinking("Analyzing task...")

        return agent_id
