"""
Main Textual dashboard
"""
from pathlib import Path
from typing import Optional, List, Dict, Any
import time
import asyncio

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Button, Label, Input, Select
from textual.binding import Binding

from mao.orchestrator.project_loader import ProjectConfig
from mao.orchestrator.tmux_manager import TmuxManager
from mao.orchestrator.agent_logger import AgentLogger
from mao.orchestrator.agent_executor import AgentExecutor
from mao.orchestrator.agent_executor import AgentProcess as APIAgentProcess
from mao.orchestrator.claude_code_executor import ClaudeCodeExecutor
from mao.orchestrator.claude_code_executor import AgentProcess as ClaudeAgentProcess
from typing import Union
from mao.ui.widgets.progress_widget import (
    TaskProgressWidget as EnhancedTaskProgressWidget,
    AgentActivityWidget,
    MetricsWidget,
)
from mao.ui.widgets.approval_widget import UnifiedApprovalPanel


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


class TaskControlPanel(Container):
    """タスク入力とワーカー起動のコントロールパネル"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        """UIコンポーネントを構築"""
        with Vertical():
            yield Label("[bold]タスクコントロール[/bold]")
            yield Input(placeholder="タスクを入力...", id="task_input")
            with Horizontal():
                yield Label("ワーカー数:", classes="label")
                yield Select(
                    [(f"{i} Workers", i) for i in range(1, 9)],
                    value=3,
                    id="num_workers",
                )
                yield Button("起動", id="launch_task", variant="primary")


class Dashboard(App):
    """Main Textual dashboard"""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 5;
        grid-gutter: 1;
        padding: 1;
    }

    #agent_status {
        row-span: 2;
        border: solid green;
        padding: 1;
        overflow-y: auto;  /* スクロール可能にする */
    }

    #task_progress {
        border: solid blue;
        padding: 1;
        overflow-y: auto;
    }

    #metrics {
        border: solid magenta;
        padding: 1;
    }

    #approval_panel {
        border: solid yellow;
        padding: 1;
        row-span: 2;
    }

    #activity {
        border: solid cyan;
        padding: 1;
        overflow-y: auto;
    }

    #task_control {
        column-span: 3;
        border: solid white;
        padding: 1;
        height: auto;
    }

    #log_viewer {
        column-span: 3;
        border: solid cyan;
        padding: 1;
        height: 100%;
        overflow-y: auto;
    }

    Button {
        margin: 1;
    }

    #task_input {
        width: 100%;
        margin-bottom: 1;
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
        initial_prompt: Optional[str] = None,
        initial_role: str = "general",
        initial_model: str = "claude-sonnet-4-20250514",
    ):
        super().__init__()
        self.project_path = project_path
        self.config = config
        self.use_redis = use_redis
        self.redis_url = redis_url
        self.tmux_manager = tmux_manager
        self.initial_prompt = initial_prompt
        self.initial_role = initial_role
        self.initial_model = initial_model
        self.agents = {}

        # ログディレクトリ
        self.log_dir = project_path / ".mao" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # エージェント作業ディレクトリ
        self.agents_work_dir = project_path / ".mao" / "agents"
        self.agents_work_dir.mkdir(parents=True, exist_ok=True)

        # エージェント実行エンジン
        # 1. Claude Code CLIを優先的に使用
        # 2. なければAPI key経由
        self.executor = None
        self.executor_type = None

        try:
            claude_executor = ClaudeCodeExecutor(
                allow_unsafe_operations=config.security.allow_unsafe_operations
            )
            if claude_executor.is_available():
                self.executor = claude_executor
                self.executor_type = "claude_code"
        except Exception:
            pass

        # Claude Codeが使えない場合はAPI経由
        if self.executor is None:
            api_executor = AgentExecutor()
            self.executor = api_executor
            self.executor_type = "api"

        # タスクディスパッチャー（マルチワーカー対応）
        from mao.orchestrator.task_dispatcher import TaskDispatcher
        self.task_dispatcher = TaskDispatcher(project_path=project_path)

        # メトリクス追跡
        self.total_tokens_used = 0
        self.total_cost = 0.0
        self.completed_tasks = 0
        self.failed_tasks = 0

        # ウィジェット参照
        self.agent_status_widget = None
        self.log_viewer_widget = None
        self.task_progress_widget = None
        self.metrics_widget = None
        self.activity_widget = None
        self.approval_widget = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        # エージェント状態
        self.agent_status_widget = AgentStatusWidget(id="agent_status")
        yield self.agent_status_widget

        # タスク進捗（改善版）
        self.task_progress_widget = EnhancedTaskProgressWidget(id="task_progress")
        yield self.task_progress_widget

        # メトリクス（Claude使用量含む）
        self.metrics_widget = MetricsWidget(id="metrics")
        yield self.metrics_widget

        # 承認パネル（統合版）
        self.approval_widget = UnifiedApprovalPanel(id="approval_panel")
        yield self.approval_widget

        # 最近の活動
        self.activity_widget = AgentActivityWidget(id="activity")
        yield self.activity_widget

        # タスクコントロールパネル（グリッドモードの場合のみ表示）
        if self.tmux_manager and self.tmux_manager.use_grid_layout:
            self.task_control_panel = TaskControlPanel(id="task_control")
            yield self.task_control_panel

        # ログビューアー
        self.log_viewer_widget = LogViewerWidget(id="log_viewer")
        yield self.log_viewer_widget

        yield Footer()

    def on_mount(self) -> None:
        """アプリケーション起動時の処理"""
        self.title = f"MAO ダッシュボード - {self.config.project_name}"

        # メトリクス初期化
        if self.metrics_widget:
            self.metrics_widget.update_metrics(
                total_agents=0,
                active_agents=0,
                completed_tasks=0,
                failed_tasks=0,
                total_tokens=0,
                estimated_cost=0.0,
            )

        # 起動ログ
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log("ダッシュボードを起動しました")
            self.log_viewer_widget.add_log(f"プロジェクト: {self.config.project_name}")
            self.log_viewer_widget.add_log(f"言語: {self.config.default_language}")

            if self.tmux_manager:
                self.log_viewer_widget.add_log("tmux監視が有効です")

            # エージェント実行方式を表示
            if self.executor_type == "claude_code":
                self.log_viewer_widget.add_log("✓ エージェント実行: Claude Code CLI")
                self.log_viewer_widget.add_log(f"  作業ディレクトリ: {self.agents_work_dir}")
            elif self.executor_type == "api" and self.executor.is_available():
                self.log_viewer_widget.add_log("✓ エージェント実行: Anthropic API")
            else:
                self.log_viewer_widget.add_log(
                    "⚠ エージェント実行機能が利用できません"
                )
                self.log_viewer_widget.add_log(
                    "  以下のいずれかを設定してください："
                )
                self.log_viewer_widget.add_log(
                    "  1. Claude Code CLIをインストール"
                )
                self.log_viewer_widget.add_log(
                    "  2. export ANTHROPIC_API_KEY=your-api-key"
                )

        # 活動ログ
        if self.activity_widget:
            if self.executor_type == "claude_code":
                self.activity_widget.add_activity(
                    "system", "ダッシュボード起動（Claude Code CLI）", "success"
                )
            elif self.executor_type == "api" and self.executor.is_available():
                self.activity_widget.add_activity(
                    "system", "ダッシュボード起動（Anthropic API）", "success"
                )
            else:
                self.activity_widget.add_activity(
                    "system", "ダッシュボード起動（エージェント実行無効）", "warning"
                )

        # 初期プロンプトがあればエージェントを起動
        if self.initial_prompt:
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(f"初期タスクを開始: {self.initial_prompt[:50]}...")

            # グリッドレイアウトの場合は複数ワーカーに分配
            if self.tmux_manager and self.tmux_manager.use_grid_layout:
                self.spawn_multi_agents(
                    task_description=self.initial_prompt,
                    num_workers=3,  # デフォルト3ワーカー
                    model=self.initial_model,
                )
            else:
                # 通常モード：単一エージェント
                task_info = {
                    "description": self.initial_prompt,
                    "role": self.initial_role,
                }

                self.spawn_agent(
                    role_name=self.initial_role,
                    task=task_info,
                    prompt=self.initial_prompt,
                    model=self.initial_model,
                )

    def action_quit(self) -> None:
        """アプリケーションを終了"""
        self.exit()

    def action_refresh(self) -> None:
        """画面をリフレッシュ"""
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log("ダッシュボードを更新しました")

        if self.agent_status_widget:
            self.agent_status_widget.refresh_display()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """ボタンクリックイベントハンドラー"""
        button_id = event.button.id

        if button_id != "launch_task":
            return

        # タスク入力フィールドから値を取得
        task_input = self.query_one("#task_input", Input)
        task_description = task_input.value.strip()

        if not task_description:
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log("⚠ タスクを入力してください")
            return

        # ワーカー数をSelectから取得
        num_workers_select = self.query_one("#num_workers", Select)
        num_workers = num_workers_select.value

        # タスクをログに記録
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(f"🚀 タスク起動: {num_workers}ワーカー")

        # マルチワーカーでタスク実行
        self.spawn_multi_agents(
            task_description=task_description,
            num_workers=num_workers,
            model=self.initial_model,
        )

        # 入力フィールドをクリア
        task_input.value = ""

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
        if not self.executor.is_available():
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    "⚠ エージェント実行エンジンが利用できません"
                )
                self.log_viewer_widget.add_log(
                    "  ANTHROPIC_API_KEY を設定してください"
                )
            if self.activity_widget:
                self.activity_widget.add_activity(
                    "system", "API key未設定のためエージェント起動失敗", "error"
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
        if self.executor_type == "claude_code":
            # Claude Code executorの場合は専用の作業ディレクトリを作成
            agent_work_dir = self.agents_work_dir / agent_id
            agent_process = ClaudeAgentProcess(
                agent_id=agent_id,
                role_name=role_name,
                prompt=prompt,
                model=model,
                logger=agent_logger,
                executor=self.executor,
                work_dir=agent_work_dir,
            )
        else:
            # API経由の場合
            agent_process = APIAgentProcess(
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

    def spawn_multi_agents(
        self, task_description: str, num_workers: int = 3, model: str = "claude-sonnet-4-20250514"
    ) -> List[str]:
        """複数のワーカーエージェントを起動（グリッドレイアウト用）

        Args:
            task_description: タスクの説明
            num_workers: 起動するワーカー数
            model: 使用するモデル

        Returns:
            起動したエージェントIDのリスト
        """
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(f"マルチエージェントモード: {num_workers}ワーカーを起動")

        # タスクIDを生成
        task_id = f"task-{int(time.time())}"

        # タスクを分解
        subtasks = self.task_dispatcher.decompose_task_to_workers(
            task_id=task_id,
            task_description=task_description,
            num_workers=num_workers
        )

        # ダッシュボード更新
        self.task_dispatcher.update_dashboard(task_id, task_description, "Running")

        # 各サブタスクに対してワーカーを起動
        agent_ids = []
        for subtask in subtasks:
            if not subtask.worker_id:
                continue

            agent_id = f"{subtask.worker_id}-{int(time.time())}"

            # エージェント専用ロガー作成
            agent_logger = AgentLogger(
                agent_id=agent_id,
                agent_name=subtask.worker_id,
                log_dir=self.log_dir
            )

            # グリッドレイアウトのペインに割り当て
            if self.tmux_manager:
                self.tmux_manager.assign_agent_to_pane(
                    role=subtask.worker_id,
                    agent_id=agent_id,
                    log_file=agent_logger.log_file
                )

            # ログ
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(f"{subtask.worker_id} を起動: {subtask.description[:30]}...")

            # ステータス更新
            if self.agent_status_widget:
                self.agent_status_widget.update_status(
                    agent_id, "THINKING", subtask.description
                )

            # エージェントプロセス作成
            if self.executor_type == "claude_code":
                agent_work_dir = self.agents_work_dir / agent_id
                agent_process = ClaudeAgentProcess(
                    agent_id=agent_id,
                    role_name=subtask.worker_id,
                    prompt=subtask.description,
                    model=model,
                    logger=agent_logger,
                    executor=self.executor,
                    work_dir=agent_work_dir,
                )
            else:
                agent_process = APIAgentProcess(
                    agent_id=agent_id,
                    role_name=subtask.worker_id,
                    prompt=subtask.description,
                    model=model,
                    logger=agent_logger,
                    executor=self.executor,
                )

            # エージェント情報を保存
            self.agents[agent_id] = {
                "role": subtask.worker_id,
                "logger": agent_logger,
                "task": {"id": subtask.subtask_id, "description": subtask.description},
                "process": agent_process,
            }

            # バックグラウンドで起動
            asyncio.create_task(self._run_agent(agent_id, agent_process))

            agent_ids.append(agent_id)

        if self.activity_widget:
            self.activity_widget.add_activity(
                "system", f"{len(agent_ids)}ワーカーを起動", "success"
            )

        return agent_ids

    async def _run_agent(self, agent_id: str, process: Union[APIAgentProcess, ClaudeAgentProcess]):
        """エージェントをバックグラウンドで実行"""
        try:
            # 活動ログ：開始
            if self.activity_widget:
                self.activity_widget.add_activity(agent_id, "実行開始", "info")

            result = await process.start()

            # メトリクス更新
            if result.get("success"):
                usage = result.get("usage", {})
                tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                self.total_tokens_used += tokens

                # コスト計算（AgentExecutorと同じロジック）
                model = result.get("model", "")
                pricing = {
                    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
                    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
                    "claude-haiku-4-20250514": {"input": 0.25, "output": 1.25},
                }
                price = pricing.get(model, {"input": 3.0, "output": 15.0})
                cost = (
                    usage.get("input_tokens", 0) / 1_000_000 * price["input"]
                    + usage.get("output_tokens", 0) / 1_000_000 * price["output"]
                )
                self.total_cost += cost

                self.completed_tasks += 1

                # メトリクスウィジェット更新
                if self.metrics_widget:
                    self.metrics_widget.update_metrics(
                        total_agents=len(self.agents),
                        active_agents=sum(
                            1 for a in self.agents.values() if a["process"].is_running()
                        ),
                        completed_tasks=self.completed_tasks,
                        failed_tasks=self.failed_tasks,
                        total_tokens=self.total_tokens_used,
                        estimated_cost=self.total_cost,
                    )
            else:
                self.failed_tasks += 1

                if self.metrics_widget:
                    self.metrics_widget.update_metrics(
                        total_agents=len(self.agents),
                        active_agents=sum(
                            1 for a in self.agents.values() if a["process"].is_running()
                        ),
                        completed_tasks=self.completed_tasks,
                        failed_tasks=self.failed_tasks,
                    )

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

            # 活動ログ：完了
            if self.activity_widget:
                if result.get("success"):
                    usage = result.get("usage", {})
                    tokens = usage.get("output_tokens", 0)
                    self.activity_widget.add_activity(
                        agent_id, f"完了 ({tokens} tokens)", "success"
                    )
                else:
                    self.activity_widget.add_activity(agent_id, "エラー", "error")

        except Exception as e:
            self.failed_tasks += 1

            if self.agent_status_widget:
                self.agent_status_widget.update_status(agent_id, "ERROR", str(e))

            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(f"✗ {agent_id} で例外発生: {str(e)}")

            if self.activity_widget:
                self.activity_widget.add_activity(agent_id, f"例外: {str(e)}", "error")
