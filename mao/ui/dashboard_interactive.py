"""
Interactive Dashboard - CTOと対話できるダッシュボード
"""
from pathlib import Path
from typing import Optional, Dict, Any, List
import asyncio
import uuid
import subprocess
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Header, Footer, TabbedContent, TabPane
from textual.binding import Binding

from mao.ui.widgets import (
    HeaderWidget,
    AgentListWidget,
    SimpleLogViewer,
    CTOChatPanel,
    MetricsWidget,
    ApprovalQueueWidget,
)
from mao.orchestrator.project_loader import ProjectConfig
from mao.orchestrator.tmux_manager import TmuxManager
from mao.orchestrator.claude_code_executor import ClaudeCodeExecutor
from mao.orchestrator.state_manager import StateManager
from mao.orchestrator.message_queue import MessageQueue
from mao.orchestrator.session_manager import SessionManager
from mao.orchestrator.feedback_manager import FeedbackManager
from mao.orchestrator.task_dispatcher import TaskDispatcher

# Mixins
from mao.ui.dashboard_parser import DashboardParserMixin
from mao.ui.dashboard_spawner import DashboardSpawnerMixin
from mao.ui.dashboard_state import DashboardStateMixin
from mao.ui.dashboard_cto import DashboardCTOMixin
from mao.ui.dashboard_handlers import DashboardHandlersMixin


class InteractiveDashboard(
    DashboardParserMixin,
    DashboardSpawnerMixin,
    DashboardStateMixin,
    DashboardCTOMixin,
    DashboardHandlersMixin,
    App,
):
    """CTOと対話できるダッシュボード"""

    CSS = """
    Screen {
        background: $surface;
    }

    #main_container {
        layout: horizontal;
        height: 1fr;
    }

    #cto_chat_panel {
        width: 50%;
        height: 100%;
        border: solid $warning 60%;
        padding: 1;
        layout: vertical;
        overflow-y: auto;
    }

    #cto_chat_panel:focus-within {
        border: heavy yellow;
        background: $surface-darken-1;
    }

    #right_panel {
        width: 50%;
    }

    #right_panel:focus-within {
        border: heavy cyan;
    }

    #header_container {
        height: 1fr;
        margin-bottom: 1;
        scrollbar-gutter: stable;
    }

    #header_widget {
        height: auto;
        border: solid cyan 60%;
        padding: 1;
    }

    #header_widget:focus-within {
        border: heavy cyan;
        background: $surface-darken-1;
    }

    #metrics_container {
        height: 1fr;
        margin-bottom: 1;
        scrollbar-gutter: stable;
    }

    #metrics_widget {
        height: auto;
        border: solid magenta 60%;
        padding: 1;
    }

    #metrics_widget:focus-within {
        border: heavy magenta;
        background: $surface-darken-1;
    }

    #approval_queue_container {
        height: 1fr;
        margin-bottom: 1;
        scrollbar-gutter: stable;
    }

    #approval_queue {
        border: solid red 60%;
        padding: 1;
        height: auto;
    }

    #approval_queue:focus {
        border: heavy red;
        background: $surface-darken-1;
    }

    .approval-request-container {
        border: solid yellow;
        padding: 1;
        margin-bottom: 1;
    }

    .approval-request-container:focus-within {
        border: heavy yellow;
        background: $surface-darken-1;
    }

    .approval-header {
        layout: horizontal;
        height: auto;
    }

    .approval-title {
        width: 1fr;
    }

    .risk-badge {
        width: auto;
        padding: 0 1;
    }

    .approval-buttons {
        layout: horizontal;
        height: auto;
        margin-top: 1;
    }

    .approve-button, .reject-button, .details-button {
        margin-right: 1;
    }

    #agent_list_container {
        height: 1fr;
        margin-bottom: 1;
        scrollbar-gutter: stable;
    }

    #agent_list {
        border: solid green 60%;
        padding: 1;
        height: auto;
    }

    #agent_list:focus {
        border: heavy green;
        background: $surface-darken-1;
    }

    #log_tabs {
        height: 1fr;
        border: solid blue 60%;
    }

    #log_viewer {
        padding: 1;
        height: auto;
    }

    #log_viewer:focus {
        border: heavy blue;
        background: $surface-darken-1;
    }

    #cto_chat_scroll {
        height: 1fr;
        scrollbar-gutter: stable;
    }

    CTOChatWidget {
        padding: 1;
    }

    CTOChatInput {
        height: auto;
        margin-top: 1;
    }

    CTOChatInput:focus {
        border: heavy yellow;
    }

    Footer {
        background: $accent;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+r", "refresh", "Refresh"),
        Binding("tab", "focus_next", "Next Panel"),
        Binding("shift+tab", "focus_previous", "Prev Panel"),
        Binding("ctrl+1", "focus_cto", "CTO"),
        Binding("ctrl+0", "focus_approvals", "Approvals"),
        Binding("ctrl+2", "focus_agents", "Agents"),
        Binding("ctrl+3", "focus_logs", "Logs"),
    ]

    def __init__(
        self,
        project_path: Path,
        config: ProjectConfig,
        use_redis: bool = False,
        redis_url: Optional[str] = None,
        tmux_manager: Optional[TmuxManager] = None,
        initial_prompt: Optional[str] = None,
        initial_role: str = "general",
        initial_model: str = "claude-sonnet-4-20250514",
        feedback_branch: Optional[str] = None,
        worktree_manager: Optional[Any] = None,
        session_id: Optional[str] = None,
        session_title: Optional[str] = None,
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
        self.feedback_branch = feedback_branch
        self.worktree_manager = worktree_manager
        self._provided_session_id = session_id
        self._provided_session_title = session_title

        # ウィジェット参照
        self.header_widget: Optional[HeaderWidget] = None
        self.metrics_widget: Optional[MetricsWidget] = None
        self.agent_list_widget: Optional[AgentListWidget] = None
        self.log_viewer_widget: Optional[SimpleLogViewer] = None  # Allタブのログビューア
        self.log_viewers_by_agent: Dict[str, SimpleLogViewer] = {}  # エージェント別ログビューア
        self.cto_chat_panel: Optional[CTOChatPanel] = None  # CTOチャット
        self.approval_queue_widget: Optional[ApprovalQueueWidget] = None

        # CTOエグゼキュータ（Claude Code使用、スキルベース）
        self.cto_executor = ClaudeCodeExecutor(
            allow_unsafe_operations=config.security.allow_unsafe_operations
        )
        self.cto_active = False

        # TaskDispatcher（MAOロール読み込み）
        self.task_dispatcher = TaskDispatcher(
            project_path=project_path,
        )

        # MAOロール定義をロード
        self.available_roles = self.task_dispatcher.roles
        self.role_names = list(self.available_roles.keys())

        # エージェント管理
        self.agents: Dict[str, Dict[str, Any]] = {}

        # メッセージキュー
        self.message_queue = MessageQueue(project_path=project_path)

        # 承認キュー（エージェント完了タスクの承認管理）
        from mao.orchestrator.approval_queue import ApprovalQueue
        self.approval_queue = ApprovalQueue(project_path=project_path)

        # タスクキュー（順次実行用）
        self.task_queue: List[Dict[str, Any]] = []
        self.current_task_index = 0
        self.sequential_mode = True  # シーケンシャル実行モード

        # セッション管理（session_id が指定されている場合はそれを使用、なければ新規作成）
        if self._provided_session_id:
            # 既存セッションを継続
            self.session_manager = SessionManager(
                project_path=project_path,
                session_id=self._provided_session_id
            )
        else:
            # 新規セッションを作成
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            short_uuid = str(uuid.uuid4())[:8]
            new_session_id = f"{timestamp}_{short_uuid}"

            # タイトルを決定（ユーザー指定 or initial_promptから生成）
            session_title = self._provided_session_title
            if not session_title and self.initial_prompt:
                # initial_promptから簡潔なタイトルを生成（最初の50文字）
                session_title = self.initial_prompt[:50]
                if len(self.initial_prompt) > 50:
                    session_title += "..."

            self.session_manager = SessionManager(
                project_path=project_path,
                session_id=new_session_id,
                title=session_title
            )

        # 状態管理（セッションIDで分離）
        self.state_manager = StateManager(
            project_path=project_path,
            use_sqlite=True,
            session_id=self.session_manager.session_id
        )

        # フィードバック管理
        self.feedback_manager = FeedbackManager(project_path=project_path)

        # 作業ディレクトリの設定
        self.work_dir = self._setup_work_directory()

        # 更新タスク
        self._update_task: Optional[asyncio.Task] = None
        self._message_polling_task: Optional[asyncio.Task] = None

    def _setup_work_directory(self) -> Path:
        """作業ディレクトリを設定

        git リポジトリの場合は worktree を作成、そうでない場合は project_path を使用
        """
        # git リポジトリかチェック
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            is_git_repo = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            is_git_repo = False

        if is_git_repo:
            # git worktree を作成
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            worktree_name = f"mao-work-{timestamp}"
            worktree_path = self.project_path / ".mao" / "worktrees" / worktree_name

            try:
                # worktrees ディレクトリを作成
                worktree_path.parent.mkdir(parents=True, exist_ok=True)

                # worktree を作成
                subprocess.run(
                    ["git", "worktree", "add", str(worktree_path)],
                    cwd=self.project_path,
                    capture_output=True,
                    check=True,
                    timeout=30,
                )
                return worktree_path
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                # worktree 作成に失敗した場合はプロジェクトディレクトリを使用
                return self.project_path
        else:
            # git リポジトリでない場合はプロジェクトディレクトリをそのまま使用
            return self.project_path

    def compose(self) -> ComposeResult:
        """ウィジェットを作成"""
        yield Header()

        # メインコンテナ（左右分割）
        with Container(id="main_container"):
            # 左パネル: CTOチャット（全体）
            self.cto_chat_panel = CTOChatPanel(id="cto_chat_panel")
            yield self.cto_chat_panel

            # 右パネル: タスク情報 + メトリクス + 承認キュー + エージェント一覧 + ログ
            with Vertical(id="right_panel"):
                # ヘッダー（タスク情報）（個別にスクロール可能）
                with VerticalScroll(id="header_container"):
                    self.header_widget = HeaderWidget(id="header_widget")
                    yield self.header_widget

                # メトリクス（進捗、トークン、コスト）（個別にスクロール可能）
                with VerticalScroll(id="metrics_container"):
                    self.metrics_widget = MetricsWidget(id="metrics_widget")
                    yield self.metrics_widget

                # 承認キュー（個別にスクロール可能）
                with VerticalScroll(id="approval_queue_container"):
                    self.approval_queue_widget = ApprovalQueueWidget(
                        id="approval_queue",
                        on_approve=self.on_approve_request,
                        on_reject=self.on_reject_request,
                    )
                    yield self.approval_queue_widget

                # エージェント一覧（個別にスクロール可能）
                with VerticalScroll(id="agent_list_container"):
                    self.agent_list_widget = AgentListWidget(
                        on_selection_changed=self.on_agent_selection_changed,
                        id="agent_list"
                    )
                    yield self.agent_list_widget

                # ログビューア（タブ形式でエージェント別に表示）
                with TabbedContent(id="log_tabs"):
                    with TabPane("All", id="tab-all"):
                        self.log_viewer_widget = SimpleLogViewer(id="log_viewer")
                        yield self.log_viewer_widget
                    # エージェント別のタブは動的に追加される

        yield Footer()


# エイリアス
Dashboard = InteractiveDashboard
