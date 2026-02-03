"""
Dashboard Handlers Mixin - イベントハンドラ・アクション
"""
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, TYPE_CHECKING

from textual.containers import VerticalScroll
from textual.widgets import TabbedContent, TabPane

from mao.ui.widgets import SimpleLogViewer

if TYPE_CHECKING:
    from mao.ui.dashboard_interactive import InteractiveDashboard


class DashboardHandlersMixin:
    """イベントハンドラとアクションを担当するミックスイン"""

    def on_mount(self: "InteractiveDashboard") -> None:
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
        if self.cto_chat_panel:
            self.cto_chat_panel.border_title = "👔 CTO Chat - CTOとの対話"

        # タスク情報を設定
        if self.initial_prompt and self.header_widget:
            self.header_widget.update_task_info(
                task_description=self.initial_prompt,
                active_count=0,
                total_count=0,
            )

        # CTOチャットのコールバック設定
        if self.cto_chat_panel:
            self.cto_chat_panel.set_send_callback(self.on_cto_message_send)

            # セッション履歴を読み込んで表示
            session_messages = self.session_manager.get_messages()
            if session_messages:
                # 既存セッションを継続している場合
                self.cto_chat_panel.add_system_message(
                    f"📚 セッション継続: {self.session_manager.session_id[-12:]} ({len(session_messages)} messages)"
                )

                # 履歴を復元（最新10件のみ表示）
                recent_messages = session_messages[-10:] if len(session_messages) > 10 else session_messages
                for msg in recent_messages:
                    if msg.role == "user":
                        self.cto_chat_panel.chat_widget.add_user_message(msg.content)
                    elif msg.role == "cto":
                        self.cto_chat_panel.chat_widget.add_cto_message(msg.content)
                    # system メッセージはスキップ（ノイズになるため）

                if len(session_messages) > 10:
                    self.cto_chat_panel.add_system_message(
                        f"💡 {len(session_messages) - 10}件の古いメッセージを省略しました"
                    )
            else:
                # 新規セッション
                self.cto_chat_panel.add_system_message(
                    f"🆕 新規セッション: {self.session_manager.session_id[-12:]}"
                )
                self.cto_chat_panel.add_system_message(
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
            asyncio.create_task(self.send_to_cto(self.initial_prompt))

        # リアルタイム更新タスクを開始
        self._update_task = asyncio.create_task(self._periodic_update())

        # メッセージハンドラーを登録
        self._register_message_handlers()

        # メッセージポーリングを開始
        self._message_polling_task = asyncio.create_task(
            self.message_queue.start_polling(receiver="cto", interval=1.0)
        )

    def on_cto_message_send(self: "InteractiveDashboard", message: str):
        """ユーザーがCTOにメッセージを送信"""
        # コマンドをチェック
        if message.startswith('/'):
            asyncio.create_task(self._handle_command(message))
            return

        # ユーザーメッセージをセッションに保存
        self.session_manager.add_message(role="user", content=message)

        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"CTOに送信: {message[:30]}...", level="INFO"
            )

        # 非同期でCTOに送信
        asyncio.create_task(self.send_to_cto(message))

    async def _handle_command(self: "InteractiveDashboard", command: str) -> None:
        """コマンドを処理

        Args:
            command: コマンド文字列（/で始まる）
        """
        parts = command.split(maxsplit=2)
        cmd = parts[0].lower()

        if cmd == "/approve":
            if len(parts) < 2:
                if self.cto_chat_panel:
                    self.cto_chat_panel.add_system_message(
                        "❌ 使用法: /approve <approval_id> [feedback]"
                    )
                return

            approval_id = parts[1]
            feedback = parts[2] if len(parts) > 2 else None

            # 承認処理
            success = self.approval_queue.approve(approval_id, feedback)

            if success:
                if self.cto_chat_panel:
                    self.cto_chat_panel.add_system_message(
                        f"✅ タスク {approval_id} を承認しました"
                    )

                # 承認キューウィジェットから削除
                if self.approval_queue_widget:
                    self.approval_queue_widget.remove_agent_approval(approval_id)

                # 次のタスクを開始
                self.current_task_index += 1
                await self._start_next_task()
            else:
                if self.cto_chat_panel:
                    self.cto_chat_panel.add_system_message(
                        f"❌ タスク {approval_id} が見つかりません"
                    )

        elif cmd == "/reject":
            if len(parts) < 3:
                if self.cto_chat_panel:
                    self.cto_chat_panel.add_system_message(
                        "❌ 使用法: /reject <approval_id> <feedback>"
                    )
                return

            approval_id = parts[1]
            feedback = parts[2]

            # 却下処理
            success = self.approval_queue.reject(approval_id, feedback)

            if success:
                if self.cto_chat_panel:
                    self.cto_chat_panel.add_system_message(
                        f"❌ タスク {approval_id} を却下しました。フィードバック: {feedback}"
                    )

                # 承認キューウィジェットから削除
                if self.approval_queue_widget:
                    self.approval_queue_widget.remove_agent_approval(approval_id)

                # 同じタスクを再実行（フィードバック付き）
                await self._retry_task_with_feedback(approval_id, feedback)
            else:
                if self.cto_chat_panel:
                    self.cto_chat_panel.add_system_message(
                        f"❌ タスク {approval_id} が見つかりません"
                    )

        elif cmd == "/diff":
            if len(parts) < 2:
                if self.cto_chat_panel:
                    self.cto_chat_panel.add_system_message(
                        "❌ 使用法: /diff <approval_id>"
                    )
                return

            approval_id = parts[1]

            # 承認アイテムを取得
            item = self.approval_queue.get_item(approval_id)

            if item:
                # git diff を表示
                if item.worktree:
                    try:
                        result = subprocess.run(
                            ["git", "diff", "HEAD"],
                            cwd=item.worktree,
                            capture_output=True,
                            text=True,
                        )
                        if result.returncode == 0:
                            diff_output = result.stdout[:2000]  # 最初の2000文字
                            if self.cto_chat_panel:
                                self.cto_chat_panel.add_system_message(
                                    f"📝 差分 ({approval_id}):\n```\n{diff_output}\n```"
                                )
                        else:
                            if self.cto_chat_panel:
                                self.cto_chat_panel.add_system_message(
                                    f"❌ 差分の取得に失敗しました"
                                )
                    except Exception as e:
                        if self.cto_chat_panel:
                            self.cto_chat_panel.add_system_message(
                                f"❌ エラー: {str(e)}"
                            )
                else:
                    if self.cto_chat_panel:
                        self.cto_chat_panel.add_system_message(
                            "❌ このタスクにはworktreeが関連付けられていません"
                        )
            else:
                if self.cto_chat_panel:
                    self.cto_chat_panel.add_system_message(
                        f"❌ タスク {approval_id} が見つかりません"
                    )

        else:
            if self.cto_chat_panel:
                self.cto_chat_panel.add_system_message(
                    f"❌ 未知のコマンド: {cmd}\n利用可能: /approve, /reject, /diff"
                )

    async def _retry_task_with_feedback(
        self: "InteractiveDashboard", approval_id: str, feedback: str
    ) -> None:
        """タスクをフィードバック付きで再実行（前回のエージェントをクリーンアップ）

        Args:
            approval_id: 承認アイテムID
            feedback: フィードバック
        """
        # 1. 承認アイテムを取得
        item = self.approval_queue.get_item(approval_id)
        if not item:
            return

        # 2. 前回のエージェント状態をクリア
        await self.state_manager.clear_state(item.agent_id)

        # 3. 前回のworktreeを削除
        if item.worktree and self.worktree_manager:
            worktree_path = Path(item.worktree)
            if worktree_path.exists():
                self.worktree_manager.remove_worktree(worktree_path)

        # 4. ApprovalQueueから削除
        self.approval_queue.delete_item(approval_id)

        # 5. ログ記録
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"🔄 {item.agent_id} を却下してクリーンアップしました",
                agent_id=item.agent_id,
                level="INFO"
            )

        # 6. フィードバック付きでタスクを再実行
        enhanced_description = f"""{item.task_description}

【前回の指摘事項】
{feedback}

上記のフィードバックを反映して修正してください。
"""

        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"🔄 タスク{item.task_number}を再実行: {feedback[:50]}...",
                level="INFO",
                agent_id="cto",
            )

        # エージェントを再起動
        await self._spawn_task_agent(
            task_description=enhanced_description,
            role=item.role,
            model=item.model,
            task_number=item.task_number,
        )

    def action_quit(self: "InteractiveDashboard") -> None:
        """アプリケーションを終了（全リソースをクリーンアップ）"""
        # 既存: タスクキャンセル
        if self._update_task:
            self._update_task.cancel()
        if self._message_polling_task:
            self._message_polling_task.cancel()

        # Phase 3 追加: 未承認アイテムを警告
        pending_items = self.approval_queue.get_pending_items()
        if pending_items:
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    f"⚠️  {len(pending_items)}件の未承認タスクがあります。終了します。",
                    level="WARN"
                )

        # Phase 3 追加: 全エージェント状態をクリア
        if self.state_manager:
            try:
                # 非同期メソッドを同期的に実行
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.state_manager.clear_all_states())
                else:
                    loop.run_until_complete(self.state_manager.clear_all_states())
            except Exception as e:
                if self.log_viewer_widget:
                    self.log_viewer_widget.add_log(
                        f"⚠️  エージェント状態のクリアに失敗: {e}",
                        level="WARN"
                    )

            self.state_manager.close()

        # Phase 3 追加: タスクキューをクリア
        if self.task_dispatcher:
            self.task_dispatcher.clear_queue()

        # Phase 3 追加: 承認キューをクリア
        if self.approval_queue:
            self.approval_queue.clear_approved()

        # Phase 3 追加: すべてのworktreeをクリーンアップ
        if self.worktree_manager:
            cleaned = self.worktree_manager.cleanup_worktrees()
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    f"🧹 {cleaned}個のworktreeをクリーンアップしました",
                    level="INFO"
                )

        # 既存: ダッシュボード用worktreeのクリーンアップ
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

    def action_refresh(self: "InteractiveDashboard") -> None:
        """画面を更新"""
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log("画面を更新しました", level="INFO")

        # 状態を手動で更新
        asyncio.create_task(self._update_from_state_manager())

        if self.header_widget:
            self.header_widget.refresh_display()
        if self.agent_list_widget:
            self.agent_list_widget.refresh_display()

    def action_focus_cto(self: "InteractiveDashboard") -> None:
        """CTOチャットにフォーカス"""
        if self.cto_chat_panel:
            # スクロールコンテナを探してフォーカス
            scroll = self.query_one("#cto_chat_scroll", VerticalScroll)
            if scroll:
                scroll.focus()

    def action_focus_approvals(self: "InteractiveDashboard") -> None:
        """承認キューにフォーカス"""
        if self.approval_queue_widget:
            self.approval_queue_widget.focus()

    def action_focus_agents(self: "InteractiveDashboard") -> None:
        """エージェント一覧にフォーカス"""
        if self.agent_list_widget:
            self.agent_list_widget.focus()

    def add_agent_log_tab(self: "InteractiveDashboard", agent_id: str) -> None:
        """エージェント専用のログタブを追加

        Args:
            agent_id: エージェントID
        """
        # 既にタブが存在する場合はスキップ
        if agent_id in self.log_viewers_by_agent:
            return

        # エージェント専用のログビューアを作成
        agent_log_viewer = SimpleLogViewer(id=f"log-{agent_id}")
        agent_log_viewer.set_current_agent(agent_id)

        # エージェント別ログビューア辞書に登録
        self.log_viewers_by_agent[agent_id] = agent_log_viewer

        # TabbedContentを取得してタブを追加
        try:
            log_tabs = self.query_one("#log_tabs", TabbedContent)
            log_tabs.add_pane(TabPane(agent_id, agent_log_viewer, id=f"tab-{agent_id}"))

            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    f"エージェント {agent_id} のログタブを追加しました",
                    level="INFO",
                )
        except Exception as e:
            # タブ追加に失敗してもエラーは記録するだけ
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    f"ログタブ追加エラー: {e}",
                    level="ERROR",
                )

    def add_log(
        self: "InteractiveDashboard",
        message: str,
        agent_id: str = "",
        level: str = "INFO"
    ) -> None:
        """ログを追加（Allタブとエージェント別タブの両方に）

        Args:
            message: ログメッセージ
            agent_id: エージェントID（空文字列はシステムログ）
            level: ログレベル
        """
        # Allタブのログビューアに追加
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(message, agent_id=agent_id, level=level)

        # エージェント専用タブがあれば、そちらにも追加
        if agent_id and agent_id in self.log_viewers_by_agent:
            self.log_viewers_by_agent[agent_id].add_log(
                message, agent_id=agent_id, level=level
            )

    def action_focus_logs(self: "InteractiveDashboard") -> None:
        """ログビューアにフォーカス"""
        if self.log_viewer_widget:
            self.log_viewer_widget.focus()

    async def on_approve_request(self: "InteractiveDashboard", request_id: str) -> None:
        """承認リクエストを承認し、エージェントをクリーンアップ

        Args:
            request_id: リクエストID
        """
        # 1. 承認アイテムを取得
        approval_item = self.approval_queue.get_item(request_id)
        if not approval_item:
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    f"❌ 承認アイテム {request_id} が見つかりません",
                    level="ERROR"
                )
            return

        # 2. ApprovalQueueで承認ステータスを設定
        self.approval_queue.approve(request_id, feedback=None)

        # 3. StateManagerから状態削除
        await self.state_manager.clear_state(approval_item.agent_id)

        # 4. Worktree削除（存在する場合）
        if approval_item.worktree and self.worktree_manager:
            worktree_path = Path(approval_item.worktree)
            if worktree_path.exists():
                self.worktree_manager.remove_worktree(worktree_path)

        # 5. ApprovalQueueからアイテム削除
        self.approval_queue.delete_item(request_id)

        # 6. UIから削除
        if self.approval_queue_widget:
            self.approval_queue_widget.remove_request(request_id)

        # 7. ログ記録
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"✅ {approval_item.agent_id} を承認してクリーンアップしました",
                agent_id=approval_item.agent_id,
                level="INFO"
            )

        if self.cto_chat_panel:
            self.cto_chat_panel.add_system_message(
                f"✅ リクエスト {request_id} を承認しました"
            )

        # 8. 次のタスクを開始（シーケンシャルモード）
        if self.sequential_mode:
            self.current_task_index += 1
            await self._start_next_task()

    def on_reject_request(self: "InteractiveDashboard", request_id: str) -> None:
        """承認リクエストを却下

        Args:
            request_id: リクエストID
        """
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"リクエスト {request_id} を却下しました",
                level="WARN",
            )

        if self.cto_chat_panel:
            self.cto_chat_panel.add_system_message(
                f"❌ リクエスト {request_id} を却下しました"
            )

        # TODO: CTOに却下を通知
        # approval_queue から削除
        if self.approval_queue_widget:
            self.approval_queue_widget.remove_request(request_id)

    def on_agent_selection_changed(
        self: "InteractiveDashboard",
        agent_id: str,
        agent_info: Dict[str, Any]
    ) -> None:
        """エージェント選択が変更された時の処理

        Args:
            agent_id: エージェントID
            agent_info: エージェント情報
        """
        # ヘッダーウィジェットに選択されたエージェントの情報を表示
        if self.header_widget:
            self.header_widget.update_selected_agent(agent_id, agent_info)
