"""
Dashboard State Mixin - 状態管理・定期更新
"""
import asyncio
import subprocess
from typing import TYPE_CHECKING

from mao.orchestrator.message_queue import Message, MessageType
from mao.ui.widgets import ApprovalRequest, RiskLevel

if TYPE_CHECKING:
    from mao.ui.dashboard_interactive import InteractiveDashboard


class DashboardStateMixin:
    """状態管理を担当するミックスイン"""

    async def _periodic_update(self: "InteractiveDashboard") -> None:
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

    async def _update_from_state_manager(self: "InteractiveDashboard") -> None:
        """StateManagerから状態を読み込んでUIを更新"""
        states = await self.state_manager.get_all_states()

        # エージェント一覧を更新
        if self.agent_list_widget:
            for state in states:
                # 新しいエージェントのログタブを追加
                if state.agent_id not in self.log_viewers_by_agent:
                    self.add_agent_log_tab(state.agent_id)

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

        # エージェント完了を監視（シーケンシャルモードのみ）
        if self.sequential_mode and self.tmux_manager:
            await self._check_agent_completion()

    async def _check_agent_completion(self: "InteractiveDashboard") -> None:
        """エージェントの完了をチェックして承認キューに追加（インタラクティブモード対応）

        インタラクティブモードではclaudeが常に動いているため、is_pane_busy()ではなく
        出力パターン（[MAO_TASK_COMPLETE]など）で完了を検知する。
        """
        for agent_id, agent_info in list(self.agents.items()):
            pane_id = agent_info.get("pane_id")
            log_file = agent_info.get("log_file")

            if not pane_id:
                continue

            # 既に承認待ち状態ならスキップ
            if agent_info.get("status") == "awaiting_approval":
                continue

            # 完了パターンを検出（is_pane_busy()ではなく出力パターンで判断）
            completion = None
            if log_file:
                completion = self.tmux_manager.detect_task_completion(pane_id, log_file)

            # 完了が検知された場合
            if completion and completion.get("completed") and agent_info.get("task_number"):
                # pipe-pane を無効化（クリーンアップ）
                self.tmux_manager.disable_pane_logging(pane_id)

                # ログファイルから出力を取得（pipe-paneで記録されている）
                log_file = agent_info.get("log_file")
                output = ""
                if log_file and log_file.exists():
                    try:
                        output = log_file.read_text(encoding="utf-8", errors="ignore")
                    except Exception as e:
                        # フォールバック: ペインから直接取得
                        output = self.tmux_manager.get_pane_content(pane_id, lines=200)
                else:
                    # ログファイルがない場合はペインから直接取得
                    output = self.tmux_manager.get_pane_content(pane_id, lines=200)

                # 変更ファイルを取得（gitで確認）
                changed_files = []
                if agent_info.get("worktree"):
                    try:
                        result = subprocess.run(
                            ["git", "diff", "--name-only", "HEAD"],
                            cwd=agent_info["worktree"],
                            capture_output=True,
                            text=True,
                        )
                        if result.returncode == 0:
                            changed_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
                    except Exception:
                        pass

                # 承認キューに追加
                approval_item = self.approval_queue.add_item(
                    agent_id=agent_id,
                    task_number=agent_info["task_number"],
                    task_description=agent_info["task"],
                    role=agent_info["role"],
                    model=agent_info.get("model", "sonnet"),
                    pane_id=pane_id,
                    worktree=agent_info.get("worktree"),
                    branch=agent_info.get("branch"),
                    changed_files=changed_files,
                    output=output,
                )

                if self.log_viewer_widget:
                    self.log_viewer_widget.add_log(
                        f"✅ {agent_id} 完了 - 承認待ち (ID: {approval_item.id})",
                        level="INFO",
                        agent_id="cto",
                    )

                # 承認キューウィジェットを更新
                if self.approval_queue_widget:
                    # ApprovalRequestオブジェクトを作成
                    approval_request = ApprovalRequest(
                        request_id=approval_item.id,
                        agent_id=agent_id,
                        task_description=agent_info["task"],
                        operation=f"Completed task in {agent_info.get('worktree', 'workspace')}",
                        risk_level=RiskLevel.MEDIUM,  # デフォルトはMEDIUM
                        reason=f"Agent {agent_id} completed task, awaiting approval",
                        recommendation="Review changes before approving",
                        details=f"Changed files: {', '.join(changed_files) if changed_files else 'None'}",
                    )
                    self.approval_queue_widget.add_request(approval_request)

                # エージェントを「承認待ち」状態に変更（削除しない - インタラクティブモードではclaudeが残っている）
                self.agents[agent_id]["status"] = "awaiting_approval"

    def _register_message_handlers(self: "InteractiveDashboard") -> None:
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

    def _handle_task_started(self: "InteractiveDashboard", message: Message) -> None:
        """タスク開始メッセージを処理"""
        if self.cto_chat_panel:
            self.cto_chat_panel.add_system_message(
                f"🚀 {message.sender}: {message.content}"
            )

        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"{message.sender}: {message.content}",
                level="INFO",
                agent_id=message.sender,
            )

    def _handle_task_progress(self: "InteractiveDashboard", message: Message) -> None:
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

    def _handle_task_completed(self: "InteractiveDashboard", message: Message) -> None:
        """タスク完了メッセージを処理"""
        if self.cto_chat_panel:
            self.cto_chat_panel.add_system_message(
                f"✅ {message.sender}: {message.content}"
            )

        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"{message.sender}: {message.content}",
                level="INFO",
                agent_id=message.sender,
            )

    def _handle_task_failed(self: "InteractiveDashboard", message: Message) -> None:
        """タスク失敗メッセージを処理"""
        if self.cto_chat_panel:
            self.cto_chat_panel.add_system_message(
                f"❌ {message.sender}: {message.content}"
            )

        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"{message.sender}: {message.content}",
                level="ERROR",
                agent_id=message.sender,
            )
