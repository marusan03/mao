"""
Interactive Dashboard - マネージャーと対話できるダッシュボード
"""
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio
import uuid
import subprocess
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer
from textual.binding import Binding

from mao.ui.widgets import (
    HeaderWidget,
    AgentListWidget,
    SimpleLogViewer,
    ManagerChatPanel,
    MetricsWidget,
)
from mao.orchestrator.project_loader import ProjectConfig
from mao.orchestrator.tmux_manager import TmuxManager
from mao.orchestrator.claude_code_executor import ClaudeCodeExecutor
from mao.orchestrator.state_manager import StateManager, AgentStatus
from mao.orchestrator.message_queue import MessageQueue, Message, MessageType
from mao.orchestrator.session_manager import SessionManager
from mao.orchestrator.feedback_manager import FeedbackManager


class InteractiveDashboard(App):
    """マネージャーと対話できるダッシュボード"""

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
        border: solid yellow;
        padding: 1;
        layout: vertical;
    }

    #right_panel {
        width: 50%;
        layout: vertical;
    }

    #header_widget {
        height: auto;
        border: solid cyan;
        padding: 1;
        margin-bottom: 1;
    }

    #metrics_widget {
        height: auto;
        border: solid magenta;
        padding: 1;
        margin-bottom: 1;
    }

    #agent_list {
        height: 30%;
        border: solid green;
        padding: 1;
        margin-bottom: 1;
        overflow-y: auto;
    }

    #log_viewer {
        height: 1fr;
        border: solid blue;
        padding: 1;
        overflow-y: auto;
    }

    ManagerChatWidget {
        height: 1fr;
        overflow-y: scroll;
        scrollbar-gutter: stable;
    }

    ManagerChatInput {
        height: auto;
        margin-top: 1;
    }

    Footer {
        background: $accent;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+r", "refresh", "Refresh"),
        Binding("ctrl+up", "select_prev", "↑ Agent"),
        Binding("ctrl+down", "select_next", "↓ Agent"),
        Binding("ctrl+m", "focus_manager", "Manager Chat"),
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

        # ウィジェット参照
        self.header_widget: Optional[HeaderWidget] = None
        self.metrics_widget: Optional[MetricsWidget] = None
        self.agent_list_widget: Optional[AgentListWidget] = None
        self.log_viewer_widget: Optional[SimpleLogViewer] = None
        self.manager_chat_panel: Optional[ManagerChatPanel] = None

        # マネージャーエグゼキュータ（セキュリティ設定を適用）
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

        # セッション管理（常に新しいセッションを作成）
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
            # 左パネル: マネージャーチャット（全体）
            self.manager_chat_panel = ManagerChatPanel(id="manager_chat_panel")
            yield self.manager_chat_panel

            # 右パネル: タスク情報 + メトリクス + エージェント一覧 + ログ
            with Vertical(id="right_panel"):
                # ヘッダー（タスク情報）
                self.header_widget = HeaderWidget(id="header_widget")
                yield self.header_widget

                # メトリクス（進捗、トークン、コスト）
                self.metrics_widget = MetricsWidget(id="metrics_widget")
                yield self.metrics_widget

                # エージェント一覧
                self.agent_list_widget = AgentListWidget(id="agent_list")
                yield self.agent_list_widget

                # ログビューア
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
        if self.agent_list_widget:
            self.agent_list_widget.border_title = "👥 Agents - エージェント一覧"
        if self.log_viewer_widget:
            self.log_viewer_widget.border_title = "📝 Logs - 実行ログ"
        if self.manager_chat_panel:
            self.manager_chat_panel.border_title = "💬 Manager Chat - マネージャーとの対話"

        # タスク情報を設定
        if self.initial_prompt and self.header_widget:
            self.header_widget.update_task_info(
                task_description=self.initial_prompt,
                active_count=0,
                total_count=0,
            )

        # マネージャーチャットのコールバック設定
        if self.manager_chat_panel:
            self.manager_chat_panel.set_send_callback(self.on_manager_message_send)

            # 初期メッセージを表示
            self.manager_chat_panel.add_system_message(
                "マネージャーに指示を送信できます。タスクの計画や質問をしてください。"
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

        # 初期タスクがあればマネージャーに送信
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
        """ユーザーがマネージャーにメッセージを送信"""
        # ユーザーメッセージをセッションに保存
        self.session_manager.add_message(role="user", content=message)

        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"マネージャーに送信: {message[:30]}...", level="INFO"
            )

        # 非同期でマネージャーに送信
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

    async def send_to_manager(self, message: str):
        """マネージャーにメッセージを送信して応答を取得"""
        if not self.manager_chat_panel:
            return

        self.manager_active = True

        # ストリーミングメッセージを開始
        self.manager_chat_panel.chat_widget.start_streaming_message()

        # マネージャーの状態を更新（実行中）
        await self.state_manager.update_state(
            agent_id="manager",
            role="manager",
            status=AgentStatus.THINKING,
            current_task=f"処理中: {message[:30]}...",
        )

        # リアルタイムログコールバック
        def on_log(log_line: str):
            """マネージャーの実行ログを受け取る"""
            if log_line.strip():
                # [stderr] プレフィックスがある場合はログビューアにERRORレベルで表示
                if log_line.startswith("[stderr]"):
                    if self.log_viewer_widget:
                        self.log_viewer_widget.add_log(
                            log_line.replace("[stderr] ", ""),
                            level="ERROR",
                            agent_id="manager",
                        )
                else:
                    # 通常のログはストリーミング表示とログビューアの両方に追加
                    if self.manager_chat_panel:
                        self.manager_chat_panel.chat_widget.append_streaming_chunk(log_line + "\n")

                    if self.log_viewer_widget:
                        self.log_viewer_widget.add_log(
                            log_line,
                            level="INFO",
                            agent_id="manager",
                        )

        try:
            # Claude Code経由でマネージャーに送信
            result = await self.manager_executor.execute_agent(
                prompt=f"""あなたはマネージャーエージェントです。
以下のタスクまたは質問について、計画を立てるか回答してください。

タスク/質問: {message}

回答は簡潔に、具体的に行ってください。
必要なワーカーエージェントやサブタスクがあれば提案してください。

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

例：エージェント間の通信が遅い場合
[MAO_FEEDBACK_START]
Title: エージェント間通信の高速化
Category: improvement
Priority: high
Description: |
  現在の YAML ベースの通信は遅延が大きい。
  Redis や SQLite を使った高速化を検討すべき。
[MAO_FEEDBACK_END]
""",
                model=self.initial_model,
                work_dir=self.work_dir,
                log_callback=on_log,
            )

            if result.get("success"):
                # ストリーミングメッセージを完了
                if self.manager_chat_panel:
                    self.manager_chat_panel.chat_widget.complete_streaming_message()

                response = result.get("response", "").strip()

                # マネージャーの応答をセッションに保存
                self.session_manager.add_message(role="manager", content=response)

                # フィードバックを抽出
                self._extract_feedbacks(response)

                if self.log_viewer_widget:
                    self.log_viewer_widget.add_log(
                        f"マネージャー応答完了",
                        level="INFO",
                        agent_id="manager",
                    )

                # マネージャーの状態を更新（完了）
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

                # マネージャーの状態を更新（エラー）
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

            # マネージャーの状態を更新（エラー）
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

    def action_select_prev(self) -> None:
        """前のエージェントを選択"""
        if self.agent_list_widget:
            self.agent_list_widget.select_prev()
            selected = self.agent_list_widget.get_selected_agent()
            if selected and self.log_viewer_widget:
                self.log_viewer_widget.set_current_agent(selected)

    def action_select_next(self) -> None:
        """次のエージェントを選択"""
        if self.agent_list_widget:
            self.agent_list_widget.select_next()
            selected = self.agent_list_widget.get_selected_agent()
            if selected and self.log_viewer_widget:
                self.log_viewer_widget.set_current_agent(selected)

    def action_focus_manager(self) -> None:
        """マネージャーチャット入力にフォーカス"""
        if self.manager_chat_panel and self.manager_chat_panel.input_widget:
            self.manager_chat_panel.input_widget.focus()


# エイリアス
Dashboard = InteractiveDashboard
