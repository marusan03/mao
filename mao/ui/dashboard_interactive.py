"""
Interactive Dashboard - CTOと対話できるダッシュボード
"""
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio
import uuid
import subprocess
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import Header, Footer
from textual.binding import Binding

from mao.ui.widgets import (
    HeaderWidget,
    AgentListWidget,
    SimpleLogViewer,
    ManagerChatPanel,
    MetricsWidget,
    ApprovalQueueWidget,
    ApprovalRequest,
    RiskLevel,
)
from mao.orchestrator.project_loader import ProjectConfig
from mao.orchestrator.tmux_manager import TmuxManager
from mao.orchestrator.claude_code_executor import ClaudeCodeExecutor
from mao.orchestrator.state_manager import StateManager, AgentStatus
from mao.orchestrator.message_queue import MessageQueue, Message, MessageType
from mao.orchestrator.session_manager import SessionManager
from mao.orchestrator.feedback_manager import FeedbackManager


class InteractiveDashboard(App):
    """CTOと対話できるダッシュボード"""

    CSS = """
    Screen {
        background: $surface;
    }

    #main_container {
        layout: horizontal;
        height: 1fr;
    }

    #manager_chat_panel {
        width: 50%;
        height: 100%;
        border: solid $warning 60%;
        padding: 1;
        layout: vertical;
        overflow-y: auto;
    }

    #manager_chat_panel:focus-within {
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

    #log_viewer_container {
        height: 1fr;
        scrollbar-gutter: stable;
    }

    #log_viewer {
        border: solid blue 60%;
        padding: 1;
        height: auto;
    }

    #log_viewer:focus {
        border: heavy blue;
        background: $surface-darken-1;
    }

    #manager_chat_scroll {
        height: 1fr;
        scrollbar-gutter: stable;
    }

    ManagerChatWidget {
        padding: 1;
    }

    ManagerChatInput {
        height: auto;
        margin-top: 1;
    }

    ManagerChatInput:focus {
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
        Binding("ctrl+1", "focus_manager", "CTO"),
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

        # ウィジェット参照
        self.header_widget: Optional[HeaderWidget] = None
        self.metrics_widget: Optional[MetricsWidget] = None
        self.agent_list_widget: Optional[AgentListWidget] = None
        self.log_viewer_widget: Optional[SimpleLogViewer] = None
        self.manager_chat_panel: Optional[ManagerChatPanel] = None  # CTOチャット
        self.approval_queue_widget: Optional[ApprovalQueueWidget] = None

        # CTOエグゼキュータ（Claude Code使用、スキルベース）
        self.manager_executor = ClaudeCodeExecutor(
            allow_unsafe_operations=config.security.allow_unsafe_operations
        )
        self.manager_active = False

        # エージェント管理
        self.agents: Dict[str, Dict[str, Any]] = {}

        # 状態管理
        self.state_manager = StateManager(project_path=project_path, use_sqlite=True)

        # メッセージキュー
        self.message_queue = MessageQueue(project_path=project_path)

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
            self.session_manager = SessionManager(
                project_path=project_path,
                session_id=new_session_id
            )

        # フィードバック管理
        self.feedback_manager = FeedbackManager(project_path=project_path)

        # 作業ディレクトリの設定
        self.work_dir = self._setup_work_directory()

        # 更新タスク
        self._update_task: Optional[asyncio.Task] = None
        self._message_polling_task: Optional[asyncio.Task] = None

    async def _extract_and_spawn_tasks(self, text: str) -> None:
        """CTOの応答からタスク指示を抽出してワーカーを起動

        Args:
            text: CTOの応答テキスト
        """
        import re

        # タスクパターンを検索 (Task N: で始まる行)
        task_pattern = r'(?:Task|タスク)\s*(\d+)[:：]\s*(.+?)(?=\n(?:Task|タスク)\s*\d+[:：]|\n---|\n\n\n|$)'
        tasks = re.findall(task_pattern, text, re.DOTALL | re.MULTILINE)

        for task_num, task_content in tasks:
            # Role/ロール を抽出
            role_match = re.search(r'(?:Role|ロール)[:：]\s*(\w+)', task_content, re.IGNORECASE)
            role = role_match.group(1) if role_match else "general-purpose"

            # Model/モデル を抽出
            model_match = re.search(r'(?:Model|モデル)[:：]\s*(\w+)', task_content, re.IGNORECASE)
            model = model_match.group(1) if model_match else "sonnet"

            # タスク説明を抽出（最初の行）
            task_lines = task_content.strip().split('\n')
            task_description = task_lines[0].strip()

            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    f"🚀 タスク{task_num}をワーカーに割り当て: {role} ({model})",
                    level="INFO",
                    agent_id="manager",
                )

            # ワーカーを起動
            await self._spawn_task_agent(
                task_description=task_description,
                worker_role=role,
                model=model
            )

    def _extract_feedbacks(self, text: str) -> None:
        """テキストからフィードバックを抽出して保存

        Args:
            text: 検索対象のテキスト
        """
        import re

        # フィードバックのパターンを検索
        pattern = r'\[MAO_FEEDBACK_START\](.*?)\[MAO_FEEDBACK_END\]'
        matches = re.findall(pattern, text, re.DOTALL)

        for match in matches:
            try:
                # フィールドを抽出
                title_match = re.search(r'Title:\s*(.+)', match)
                category_match = re.search(r'Category:\s*(\w+)', match)
                priority_match = re.search(r'Priority:\s*(\w+)', match)
                desc_match = re.search(r'Description:\s*\|?\s*(.+?)(?=\[MAO_FEEDBACK_|$)', match, re.DOTALL)

                if title_match and desc_match:
                    title = title_match.group(1).strip()
                    category = category_match.group(1).strip() if category_match else "improvement"
                    priority = priority_match.group(1).strip() if priority_match else "medium"
                    description = desc_match.group(1).strip()

                    # フィードバックを保存
                    feedback = self.feedback_manager.add_feedback(
                        title=title,
                        description=description,
                        category=category,
                        priority=priority,
                        agent_id="manager",
                        session_id=self.session_manager.session_id,
                    )

                    # ユーザーに通知
                    if self.manager_chat_panel:
                        self.manager_chat_panel.add_system_message(
                            f"📝 フィードバックを記録しました: {title} (ID: {feedback.id[-12:]})"
                        )
            except Exception as e:
                # フィードバック抽出エラーは無視（作業を妨げない）
                pass

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
            self.manager_chat_panel = ManagerChatPanel(id="manager_chat_panel")
            yield self.manager_chat_panel

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

                # ログビューア（個別にスクロール可能）
                with VerticalScroll(id="log_viewer_container"):
                    self.log_viewer_widget = SimpleLogViewer(id="log_viewer")
                    yield self.log_viewer_widget

        yield Footer()

    def on_mount(self) -> None:
        """マウント時の処理"""
        # ウィジェットにボーダータイトルを設定
        if self.header_widget:
            self.header_widget.border_title = "📋 Task Info"
        if self.metrics_widget:
            self.metrics_widget.border_title = "📊 Metrics - 統計・使用量"
        if self.approval_queue_widget:
            self.approval_queue_widget.border_title = "🔔 Approval Queue - 承認待ち"
        if self.agent_list_widget:
            self.agent_list_widget.border_title = "👥 Agents - エージェント一覧"
        if self.log_viewer_widget:
            self.log_viewer_widget.border_title = "📝 Logs - 実行ログ"
        if self.manager_chat_panel:
            self.manager_chat_panel.border_title = "👔 CTO Chat - CTOとの対話"

        # タスク情報を設定
        if self.initial_prompt and self.header_widget:
            self.header_widget.update_task_info(
                task_description=self.initial_prompt,
                active_count=0,
                total_count=0,
            )

        # CTOチャットのコールバック設定
        if self.manager_chat_panel:
            self.manager_chat_panel.set_send_callback(self.on_manager_message_send)

            # セッション履歴を読み込んで表示
            session_messages = self.session_manager.get_messages()
            if session_messages:
                # 既存セッションを継続している場合
                self.manager_chat_panel.add_system_message(
                    f"📚 セッション継続: {self.session_manager.session_id[-12:]} ({len(session_messages)} messages)"
                )

                # 履歴を復元（最新10件のみ表示）
                recent_messages = session_messages[-10:] if len(session_messages) > 10 else session_messages
                for msg in recent_messages:
                    if msg.role == "user":
                        self.manager_chat_panel.chat_widget.add_user_message(msg.content)
                    elif msg.role == "manager":
                        self.manager_chat_panel.chat_widget.add_manager_message(msg.content)
                    # system メッセージはスキップ（ノイズになるため）

                if len(session_messages) > 10:
                    self.manager_chat_panel.add_system_message(
                        f"💡 {len(session_messages) - 10}件の古いメッセージを省略しました"
                    )
            else:
                # 新規セッション
                self.manager_chat_panel.add_system_message(
                    f"🆕 新規セッション: {self.session_manager.session_id[-12:]}"
                )
                self.manager_chat_panel.add_system_message(
                    "CTOに指示を送信できます。タスクの分解と実行を依頼してください。"
                )

        # 初期ログ
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                "インタラクティブダッシュボードを起動しました", level="INFO"
            )
            if self.initial_prompt:
                self.log_viewer_widget.add_log(
                    f"初期タスク: {self.initial_prompt[:50]}...", level="INFO"
                )

        # 初期タスクがあればCTOに送信
        if self.initial_prompt:
            asyncio.create_task(self.send_to_manager(self.initial_prompt))

        # リアルタイム更新タスクを開始
        self._update_task = asyncio.create_task(self._periodic_update())

        # メッセージハンドラーを登録
        self._register_message_handlers()

        # メッセージポーリングを開始
        self._message_polling_task = asyncio.create_task(
            self.message_queue.start_polling(receiver="manager", interval=1.0)
        )

    def on_manager_message_send(self, message: str):
        """ユーザーがCTOにメッセージを送信"""
        # ユーザーメッセージをセッションに保存
        self.session_manager.add_message(role="user", content=message)

        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"CTOに送信: {message[:30]}...", level="INFO"
            )

        # 非同期でCTOに送信
        asyncio.create_task(self.send_to_manager(message))

    async def _periodic_update(self) -> None:
        """定期的に状態を更新（1秒ごと）"""
        while True:
            try:
                await self._update_from_state_manager()
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # エラーが発生してもループは継続
                if self.log_viewer_widget:
                    self.log_viewer_widget.add_log(f"更新エラー: {e}", level="ERROR")
                await asyncio.sleep(1.0)

    async def _update_from_state_manager(self) -> None:
        """StateManagerから状態を読み込んでUIを更新"""
        states = await self.state_manager.get_all_states()

        # エージェント一覧を更新
        if self.agent_list_widget:
            for state in states:
                self.agent_list_widget.update_agent(
                    agent_id=state.agent_id,
                    status=state.status.value,
                    task=state.current_task,
                    tokens=state.tokens_used,
                    role=state.role,
                )

        # ヘッダーを更新
        if self.header_widget:
            stats = self.state_manager.get_stats()
            self.header_widget.update_task_info(
                task_description=self.initial_prompt or "タスク実行中",
                active_count=stats["active_agents"],
                total_count=stats["total_agents"],
            )

        # メトリクスを更新
        if self.metrics_widget:
            stats = self.state_manager.get_stats()
            self.metrics_widget.update_metrics(
                total_agents=stats["total_agents"],
                active_agents=stats["active_agents"],
                total_tokens=stats["total_tokens"],
                estimated_cost=stats["total_cost"],
            )

    def _register_message_handlers(self) -> None:
        """メッセージハンドラーを登録"""
        self.message_queue.register_handler(
            MessageType.TASK_STARTED,
            self._handle_task_started,
        )
        self.message_queue.register_handler(
            MessageType.TASK_PROGRESS,
            self._handle_task_progress,
        )
        self.message_queue.register_handler(
            MessageType.TASK_COMPLETED,
            self._handle_task_completed,
        )
        self.message_queue.register_handler(
            MessageType.TASK_FAILED,
            self._handle_task_failed,
        )

    def _handle_task_started(self, message: Message) -> None:
        """タスク開始メッセージを処理"""
        if self.manager_chat_panel:
            self.manager_chat_panel.add_system_message(
                f"🚀 {message.sender}: {message.content}"
            )

        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"{message.sender}: {message.content}",
                level="INFO",
                agent_id=message.sender,
            )

    def _handle_task_progress(self, message: Message) -> None:
        """タスク進捗メッセージを処理"""
        percentage = message.metadata.get("percentage") if message.metadata else None
        progress_text = message.content

        if percentage is not None:
            progress_text = f"{progress_text} ({percentage}%)"

        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"{message.sender}: {progress_text}",
                level="INFO",
                agent_id=message.sender,
            )

    def _handle_task_completed(self, message: Message) -> None:
        """タスク完了メッセージを処理"""
        if self.manager_chat_panel:
            self.manager_chat_panel.add_system_message(
                f"✅ {message.sender}: {message.content}"
            )

        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"{message.sender}: {message.content}",
                level="INFO",
                agent_id=message.sender,
            )

    def _handle_task_failed(self, message: Message) -> None:
        """タスク失敗メッセージを処理"""
        if self.manager_chat_panel:
            self.manager_chat_panel.add_system_message(
                f"❌ {message.sender}: {message.content}"
            )

        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"{message.sender}: {message.content}",
                level="ERROR",
                agent_id=message.sender,
            )

    async def _spawn_task_agent(
        self,
        task_description: str,
        worker_role: str,
        model: str = "sonnet"
    ) -> None:
        """Taskエージェントを起動する

        Args:
            task_description: タスクの説明
            worker_role: ワーカーのロール
            model: 使用するモデル
        """
        # エージェントIDを生成
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        worker_num = len([a for a in self.agents if a.startswith("worker-")]) + 1
        agent_id = f"worker-{worker_num}"
        pane_role = f"worker-{worker_num}"  # tmux grid paneのロール名

        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"🚀 Starting {agent_id}: {task_description[:50]}...",
                level="INFO",
                agent_id="manager",
            )

        try:
            # エージェントの状態を登録
            await self.state_manager.update_state(
                agent_id=agent_id,
                role=worker_role,
                status=AgentStatus.THINKING,
                current_task=task_description[:50] + "...",
            )

            # エージェント一覧に追加
            if self.agent_list_widget:
                self.agent_list_widget.update_agent(
                    agent_id=agent_id,
                    status="running",
                    task=task_description[:50] + "...",
                    role=worker_role,
                )

            # Feedback モードの場合、ワーカー用 worktree を作成
            worker_worktree = None
            worker_branch = None
            if self.feedback_branch and self.worktree_manager:
                worker_branch = f"{self.feedback_branch}-{agent_id}"
                worker_worktree = self.worktree_manager.create_worker_worktree(
                    parent_branch=self.feedback_branch,
                    worker_id=agent_id
                )

                if worker_worktree:
                    if self.log_viewer_widget:
                        self.log_viewer_widget.add_log(
                            f"📂 Created worktree for {agent_id}: {worker_worktree}",
                            level="INFO",
                            agent_id="manager",
                        )
                else:
                    if self.log_viewer_widget:
                        self.log_viewer_widget.add_log(
                            f"⚠️ Failed to create worktree for {agent_id}, using main worktree",
                            level="WARN",
                            agent_id="manager",
                        )

            # tmuxペインに割り当てて実行
            if self.tmux_manager:
                # ワーカー作業ディレクトリ（worktree がある場合はそちらを使用）
                work_dir = worker_worktree if worker_worktree else self.work_dir

                # ペインに割り当て
                pane_id = self.tmux_manager.assign_agent_to_pane(
                    role=pane_role,
                    agent_id=agent_id,
                    work_dir=work_dir
                )

                if pane_id:
                    # タスク説明に worktree 情報を追加
                    enhanced_prompt = task_description
                    if worker_worktree:
                        enhanced_prompt = f"""⚠️ あなたは独自の git worktree で作業しています。
Worktree: {worker_worktree}
Branch: {worker_branch}

完了したら変更を commit してください。
マージは CTO が確認後に行います。

{task_description}"""

                    # tmuxペイン内でclaude-codeを実行
                    self.tmux_manager.execute_claude_code_in_pane(
                        pane_id=pane_id,
                        prompt=enhanced_prompt,
                        model=model,
                        work_dir=work_dir,
                        allow_unsafe=self.config.security.allow_unsafe_operations
                    )

                    self.agents[agent_id] = {
                        "role": worker_role,
                        "pane_id": pane_id,
                        "task": task_description,
                        "worktree": worker_worktree,
                        "branch": worker_branch,
                    }

                    if self.log_viewer_widget:
                        self.log_viewer_widget.add_log(
                            f"✅ {agent_id} started in tmux pane {pane_id}",
                            level="INFO",
                            agent_id="manager",
                        )
                else:
                    if self.log_viewer_widget:
                        self.log_viewer_widget.add_log(
                            f"⚠️ Could not assign {agent_id} to tmux pane",
                            level="WARN",
                            agent_id="manager",
                        )
            else:
                # tmuxなしの場合は直接実行
                executor = ClaudeCodeExecutor(
                    allow_unsafe_operations=self.config.security.allow_unsafe_operations
                )
                asyncio.create_task(
                    self._execute_worker_agent(
                        executor, agent_id, task_description, worker_role, model
                    )
                )

        except Exception as e:
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    f"❌ Failed to spawn worker {agent_id}: {str(e)}",
                    level="ERROR",
                    agent_id="manager",
                )

    async def _execute_worker_agent(
        self,
        executor: ClaudeCodeExecutor,
        agent_id: str,
        task_description: str,
        worker_role: str,
        model: str
    ) -> None:
        """ワーカーエージェントを実行（バックグラウンド）

        Args:
            executor: ClaudeCodeExecutor
            agent_id: エージェントID
            task_description: タスクの説明
            worker_role: ワーカーのロール
            model: 使用するモデル
        """
        try:
            # エージェントを実行
            result = await executor.execute_agent(
                prompt=task_description,
                model=model,
                work_dir=self.work_dir,
            )

            if result.get("success"):
                # 成功
                if self.log_viewer_widget:
                    self.log_viewer_widget.add_log(
                        f"✅ Worker {agent_id} completed successfully",
                        level="INFO",
                        agent_id=agent_id,
                    )

                # エージェントの状態を更新
                await self.state_manager.update_state(
                    agent_id=agent_id,
                    role=worker_role,
                    status=AgentStatus.IDLE,
                    current_task="完了",
                )

                # エージェント一覧を更新
                if self.agent_list_widget:
                    self.agent_list_widget.update_agent(
                        agent_id=agent_id,
                        status="completed",
                        task="完了",
                        role=worker_role,
                    )

                # CTOに結果を報告
                if self.manager_chat_panel:
                    response = result.get("response", "")[:200]
                    self.manager_chat_panel.add_system_message(
                        f"✅ {agent_id} 完了\n"
                        f"   結果: {response}..."
                    )

            else:
                # エラー
                error = result.get("error", "Unknown error")
                if self.log_viewer_widget:
                    self.log_viewer_widget.add_log(
                        f"❌ Worker {agent_id} failed: {error}",
                        level="ERROR",
                        agent_id=agent_id,
                    )

                # エージェントの状態を更新
                await self.state_manager.update_state(
                    agent_id=agent_id,
                    role=worker_role,
                    status=AgentStatus.ERROR,
                    current_task="エラー",
                    error_message=error,
                )

                # エージェント一覧を更新
                if self.agent_list_widget:
                    self.agent_list_widget.update_agent(
                        agent_id=agent_id,
                        status="error",
                        task=f"エラー: {error[:30]}",
                        role=worker_role,
                    )

        except Exception as e:
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    f"❌ Worker {agent_id} crashed: {str(e)}",
                    level="ERROR",
                    agent_id=agent_id,
                )

    async def send_to_manager(self, message: str):
        """CTOにメッセージを送信して応答を取得"""
        if not self.manager_chat_panel:
            return

        self.manager_active = True

        # ストリーミングメッセージを開始
        self.manager_chat_panel.chat_widget.start_streaming_message()

        # CTOの状態を更新（実行中）
        await self.state_manager.update_state(
            agent_id="manager",
            role="manager",
            status=AgentStatus.THINKING,
            current_task=f"処理中: {message[:30]}...",
        )

        try:
            # 会話履歴を取得
            conversation_history = []
            if self.manager_chat_panel and self.manager_chat_panel.chat_widget:
                conversation_history = self.manager_chat_panel.chat_widget.get_conversation_history()

            # 会話履歴をフォーマット
            history_text = ""
            if conversation_history:
                history_text = "\n以下は今までの会話履歴です:\n\n"
                for msg in conversation_history:
                    role_name = "User" if msg["role"] == "user" else "Assistant"
                    history_text += f"{role_name}: {msg['content']}\n\n"
                history_text += "---\n\n"

            # Worktree ワークフローの説明を追加（Feedbackモードの場合）
            worktree_instructions = ""
            if self.feedback_branch and self.worktree_manager:
                worktree_instructions = f"""
---
⚠️ **Git Worktree ワークフロー有効**

現在、Feedbackブランチ `{self.feedback_branch}` で作業しています。

**ワーカーの作業フロー:**
1. 各ワーカーは独自の git worktree と branch で作業します
2. Worktree は自動的に作成されます（例: `{self.feedback_branch}-worker-1`）
3. ワーカーは自分のブランチで変更を commit します
4. **マージプロセス:**
   - ワーカーが作業を完了したら、CTOに報告してください
   - CTO はワーカーのブランチを確認し、問題なければ merge を承認します
   - ワーカーのブランチは `{self.feedback_branch}` にマージされます

**CTOの責任:**
- ワーカーの作業進捗を監視
- 完了したワーカーのコードをレビュー
- マージの承認/却下を判断
- すべてのワーカーが完了したら、全体の統合を確認
---
"""

            # Claude Code経由でCTOに送信（スキルベース）
            result = await self.manager_executor.execute_agent(
                prompt=f"""あなたはCTO（Chief Technology Officer）です。
システム全体の技術責任を持ち、ワーカーの作業を監視・管理します。
{history_text}
現在のユーザーからの依頼: {message}
{worktree_instructions}

上記の会話履歴を踏まえて、以下の手順で作業してください：

1. **タスク分解**
   依頼を実行可能なサブタスクに分解します。
   各サブタスクは明確で、ワーカーが理解できる粒度にしてください。

2. **リスク評価**
   各サブタスクのリスクレベル（低/中/高）を評価します。

3. **ロール選択とワーカーへの割り当て**
   各タスクの性質に応じて、最適なワーカーロールを選択してください：

   **ロール選択ガイド:**
   - **general-purpose**: コード実装、ファイル編集、複雑なロジック実装
     例: 認証機能の実装、APIエンドポイント作成、バグ修正

   - **Bash**: コマンド実行、スクリプト実行、システム操作
     例: git操作、ファイルのコピー/移動、パッケージインストール

   - **Explore**: コードベース探索、ファイル検索、構造分析
     例: 既存の実装を調査、依存関係の把握、アーキテクチャ理解

   - **Plan**: 計画立案、アーキテクチャ設計、詳細なタスク分解
     例: 実装方針の策定、技術選定、設計ドキュメント作成

   **モデル選択ガイド:**
   - **opus**: 複雑な実装、重要な判断、アーキテクチャ設計
   - **sonnet**: 通常の実装タスク（推奨、バランス型）
   - **haiku**: シンプルなタスク、軽微な修正、調査タスク

4. **Taskツールを使ってワーカーを起動**
   各タスクに対して、**必ずTaskツールを使ってワーカーを起動してください。**

   例:
   ```
   Task 1: 既存コードの調査
   - Role: Explore
   - Model: haiku
   → Taskツールでワーカーを起動
   ```

回答は簡潔に、具体的に行ってください。

---
MAO へのフィードバック:
作業中に MAO 自体の改善案を発見した場合、以下のフォーマットで記録してください：

[MAO_FEEDBACK_START]
Title: 改善案のタイトル
Category: bug | feature | improvement | documentation
Priority: low | medium | high | critical
Description: |
  詳細な説明
[MAO_FEEDBACK_END]
""",
                model=self.initial_model,
                work_dir=self.work_dir,
            )

            if result.get("success"):
                response = result.get("response", "").strip()

                # レスポンスをストリーミングバッファに追加
                if self.manager_chat_panel and response:
                    self.manager_chat_panel.chat_widget.append_streaming_chunk(response)
                    self.manager_chat_panel.chat_widget.complete_streaming_message()

                # CTOの応答をセッションに保存
                self.session_manager.add_message(role="manager", content=response)

                # フィードバックを抽出
                self._extract_feedbacks(response)

                # タスク指示を抽出してワーカーを起動
                await self._extract_and_spawn_tasks(response)

                if self.log_viewer_widget:
                    self.log_viewer_widget.add_log(
                        f"CTO応答完了",
                        level="INFO",
                        agent_id="manager",
                    )

                # CTOの状態を更新（完了）
                await self.state_manager.update_state(
                    agent_id="manager",
                    role="manager",
                    status=AgentStatus.IDLE,
                    current_task="待機中",
                    tokens_used=result.get("tokens_used", 0),
                    cost=result.get("cost", 0.0),
                )
            else:
                error = result.get("error", "不明なエラー")
                if self.manager_chat_panel:
                    # ストリーミングメッセージをキャンセル（完了させない）
                    self.manager_chat_panel.chat_widget._streaming_message = None
                    self.manager_chat_panel.chat_widget._streaming_buffer = ""
                    self.manager_chat_panel.add_system_message(f"エラー: {error}")

                # CTOの状態を更新（エラー）
                await self.state_manager.update_state(
                    agent_id="manager",
                    role="manager",
                    status=AgentStatus.ERROR,
                    current_task="エラー発生",
                    error_message=error,
                )

        except Exception as e:
            if self.manager_chat_panel:
                # ストリーミングメッセージをキャンセル
                self.manager_chat_panel.chat_widget._streaming_message = None
                self.manager_chat_panel.chat_widget._streaming_buffer = ""
                self.manager_chat_panel.add_system_message(f"エラー: {str(e)}")

            # CTOの状態を更新（エラー）
            await self.state_manager.update_state(
                agent_id="manager",
                role="manager",
                status=AgentStatus.ERROR,
                current_task="例外発生",
                error_message=str(e),
            )

        finally:
            self.manager_active = False

    def action_quit(self) -> None:
        """アプリケーションを終了"""
        # 更新タスクをキャンセル
        if self._update_task:
            self._update_task.cancel()

        # メッセージポーリングタスクをキャンセル
        if self._message_polling_task:
            self._message_polling_task.cancel()

        # StateManagerをクローズ
        if self.state_manager:
            self.state_manager.close()

        # git worktree をクリーンアップ
        if self.work_dir != self.project_path and ".mao/worktrees/" in str(self.work_dir):
            try:
                subprocess.run(
                    ["git", "worktree", "remove", str(self.work_dir), "--force"],
                    cwd=self.project_path,
                    capture_output=True,
                    timeout=10,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                pass  # クリーンアップ失敗は無視

        self.exit()

    def action_refresh(self) -> None:
        """画面を更新"""
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log("画面を更新しました", level="INFO")

        # 状態を手動で更新
        asyncio.create_task(self._update_from_state_manager())

        if self.header_widget:
            self.header_widget.refresh_display()
        if self.agent_list_widget:
            self.agent_list_widget.refresh_display()

    def action_focus_manager(self) -> None:
        """CTOチャットにフォーカス"""
        if self.manager_chat_panel:
            # スクロールコンテナを探してフォーカス
            scroll = self.query_one("#manager_chat_scroll", VerticalScroll)
            if scroll:
                scroll.focus()

    def action_focus_approvals(self) -> None:
        """承認キューにフォーカス"""
        if self.approval_queue_widget:
            self.approval_queue_widget.focus()

    def action_focus_agents(self) -> None:
        """エージェント一覧にフォーカス"""
        if self.agent_list_widget:
            self.agent_list_widget.focus()

    def action_focus_logs(self) -> None:
        """ログビューアにフォーカス"""
        if self.log_viewer_widget:
            self.log_viewer_widget.focus()

    def on_approve_request(self, request_id: str) -> None:
        """承認リクエストを承認

        Args:
            request_id: リクエストID
        """
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"リクエスト {request_id} を承認しました",
                level="INFO",
            )

        if self.manager_chat_panel:
            self.manager_chat_panel.add_system_message(
                f"✅ リクエスト {request_id} を承認しました"
            )

        # TODO: CTOに承認を通知
        # approval_queue から削除
        if self.approval_queue_widget:
            self.approval_queue_widget.remove_request(request_id)

    def on_reject_request(self, request_id: str) -> None:
        """承認リクエストを却下

        Args:
            request_id: リクエストID
        """
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"リクエスト {request_id} を却下しました",
                level="WARN",
            )

        if self.manager_chat_panel:
            self.manager_chat_panel.add_system_message(
                f"❌ リクエスト {request_id} を却下しました"
            )

        # TODO: CTOに却下を通知
        # approval_queue から削除
        if self.approval_queue_widget:
            self.approval_queue_widget.remove_request(request_id)

    def on_agent_selection_changed(self, agent_id: str, agent_info: Dict[str, Any]) -> None:
        """エージェント選択が変更された時の処理

        Args:
            agent_id: エージェントID
            agent_info: エージェント情報
        """
        # ヘッダーウィジェットに選択されたエージェントの情報を表示
        if self.header_widget:
            self.header_widget.update_selected_agent(agent_id, agent_info)


# エイリアス
Dashboard = InteractiveDashboard
