"""
Main Textual dashboard
"""
from pathlib import Path
from typing import Optional
import time
import asyncio

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Button, Label
from textual.binding import Binding

from mao.orchestrator.project_loader import ProjectConfig
from mao.orchestrator.tmux_manager import TmuxManager
from mao.orchestrator.agent_logger import AgentLogger
from mao.orchestrator.agent_executor import AgentExecutor, AgentProcess


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
        lines = ["[bold]アクティビティログ[/bold]\n"]
        if not self.logs:
            lines.append("[dim]まだアクティビティがありません[/dim]")
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

        # エージェント実行エンジン
        try:
            self.executor = AgentExecutor()
        except ValueError:
            self.executor = None
            # API key がない場合はログに記録（起動後）

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
            yield Label("[bold]承認パネル[/bold]")
            yield Label("\n[dim]承認待ちの項目はありません[/dim]")

        yield approval_panel

        # ログビューアー
        self.log_viewer_widget = LogViewerWidget(id="log_viewer")
        yield self.log_viewer_widget

        yield Footer()

    def on_mount(self) -> None:
        """アプリケーション起動時の処理"""
        self.title = f"MAO ダッシュボード - {self.config.project_name}"

        # 起動ログ
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log("ダッシュボードを起動しました")
            self.log_viewer_widget.add_log(f"プロジェクト: {self.config.project_name}")
            self.log_viewer_widget.add_log(f"言語: {self.config.default_language}")

            if self.tmux_manager:
                self.log_viewer_widget.add_log("tmux監視が有効です")

            if not self.executor:
                self.log_viewer_widget.add_log(
                    "⚠ ANTHROPIC_API_KEY が設定されていません。エージェント実行は無効です"
                )

    def action_refresh(self) -> None:
        """画面をリフレッシュ"""
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log("ダッシュボードを更新しました")

        if self.agent_status_widget:
            self.agent_status_widget.refresh_display()

    def spawn_agent(self, role_name: str, task: dict, prompt: str, model: str = "claude-sonnet-4-20250514") -> Optional[str]:
        """エージェントを起動（ヘッドレス）

        Args:
            role_name: ロール名
            task: タスク情報
            prompt: エージェントプロンプト
            model: 使用するモデル

        Returns:
            エージェントID（失敗時はNone）
        """
        if not self.executor:
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    "⚠ エージェント実行エンジンが利用できません（API key未設定）"
                )
            return None

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
            self.log_viewer_widget.add_log(f"エージェントを起動しました: {agent_id}")

        # ステータス更新
        if self.agent_status_widget:
            self.agent_status_widget.update_status(
                agent_id, "THINKING", task.get("description", "")
            )

        # エージェントプロセス作成
        agent_process = AgentProcess(
            agent_id=agent_id,
            role_name=role_name,
            prompt=prompt,
            model=model,
            logger=agent_logger,
            executor=self.executor,
        )

        # エージェント情報を保存
        self.agents[agent_id] = {
            "role": role_name,
            "logger": agent_logger,
            "task": task,
            "process": agent_process,
        }

        # バックグラウンドで起動
        asyncio.create_task(self._run_agent(agent_id, agent_process))

        return agent_id

    async def _run_agent(self, agent_id: str, process: AgentProcess):
        """エージェントをバックグラウンドで実行"""
        try:
            result = await process.start()

            # ステータス更新
            if self.agent_status_widget:
                if result.get("success"):
                    self.agent_status_widget.update_status(agent_id, "IDLE", "完了")
                else:
                    self.agent_status_widget.update_status(agent_id, "ERROR", "エラー")

            # ログ更新
            if self.log_viewer_widget:
                if result.get("success"):
                    self.log_viewer_widget.add_log(f"✓ {agent_id} が完了しました")
                else:
                    self.log_viewer_widget.add_log(f"✗ {agent_id} がエラーで終了しました")

        except Exception as e:
            if self.agent_status_widget:
                self.agent_status_widget.update_status(agent_id, "ERROR", str(e))

            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(f"✗ {agent_id} で例外発生: {str(e)}")
