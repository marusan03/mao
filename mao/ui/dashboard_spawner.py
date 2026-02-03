"""
Dashboard Spawner Mixin - エージェントの起動・実行（tmux必須）
"""
from datetime import datetime
import asyncio
from typing import Optional, TYPE_CHECKING

from mao.orchestrator.state_manager import AgentStatus

if TYPE_CHECKING:
    from mao.ui.dashboard_interactive import InteractiveDashboard


class DashboardSpawnerMixin:
    """エージェント起動を担当するミックスイン"""

    async def _spawn_task_agent(
        self: "InteractiveDashboard",
        task_description: str,
        role: str,
        model: Optional[str] = None,
        task_number: Optional[int] = None,
    ) -> None:
        """Taskエージェントを起動する

        Args:
            task_description: タスクの説明
            role: MAOロール名 (coder_backend, reviewer, tester, planner, researcher, auditor, etc.)
            model: 使用するモデル（Noneの場合はロールのデフォルトモデルを使用）
            task_number: タスク番号（シーケンシャルモード用）
        """
        # ロール定義を取得
        role_config = self.available_roles.get(role)
        if not role_config:
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    f"❌ エラー: 未知のロール '{role}'",
                    level="ERROR",
                    agent_id="cto",
                )
            return

        # モデル決定（指定なしの場合はロールのデフォルト）
        if model is None:
            model = role_config.get("model", "claude-sonnet-4-20250514")

        # エージェントIDを生成
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        agent_num = len([a for a in self.agents if a.startswith("agent-")]) + 1
        agent_id = f"agent-{agent_num}"
        pane_role = f"agent-{agent_num}"  # tmux grid paneのロール名

        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"🚀 Starting {agent_id} ({role}): {task_description[:50]}...",
                level="INFO",
                agent_id="cto",
            )

        try:
            # エージェントの状態を登録
            await self.state_manager.update_state(
                agent_id=agent_id,
                role=role,
                status=AgentStatus.THINKING,
                current_task=task_description[:50] + "...",
            )

            # エージェント一覧に追加
            if self.agent_list_widget:
                self.agent_list_widget.update_agent(
                    agent_id=agent_id,
                    status="running",
                    task=task_description[:50] + "...",
                    role=role,
                )

            # Feedback モードの場合、エージェント用 worktree を作成
            agent_worktree = None
            agent_branch = None
            if self.feedback_branch and self.worktree_manager:
                agent_branch = f"{self.feedback_branch}-{agent_id}"
                agent_worktree = self.worktree_manager.create_worker_worktree(
                    parent_branch=self.feedback_branch,
                    agent_id=agent_id
                )

                if agent_worktree:
                    if self.log_viewer_widget:
                        self.log_viewer_widget.add_log(
                            f"📂 Created worktree for {agent_id}: {agent_worktree}",
                            level="INFO",
                            agent_id="cto",
                        )
                else:
                    if self.log_viewer_widget:
                        self.log_viewer_widget.add_log(
                            f"⚠️ Failed to create worktree for {agent_id}, using main worktree",
                            level="WARN",
                            agent_id="cto",
                        )

            # tmuxペインに割り当てて実行
            if self.tmux_manager:
                # エージェント作業ディレクトリ（worktree がある場合はそちらを使用）
                work_dir = agent_worktree if agent_worktree else self.work_dir

                # ログファイル作成
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                log_file = self.project_path / ".mao" / "logs" / f"{agent_id}_{timestamp}.log"
                log_file.parent.mkdir(parents=True, exist_ok=True)

                # ペインに割り当て（ログファイル指定）
                pane_id = self.tmux_manager.assign_agent_to_pane(
                    role=pane_role,
                    agent_id=agent_id,
                    work_dir=work_dir,
                    log_file=log_file
                )

                if pane_id:
                    # 完了指示を追加
                    completion_instruction = """

## タスク完了時の報告

タスクが完了したら、必ず以下のマーカーを出力してください：

[MAO_TASK_COMPLETE]
status: success または failed
changed_files:
  - file1.py
  - file2.py
summary: 変更内容の要約
[/MAO_TASK_COMPLETE]

このマーカーにより、MAOシステムが完了を検知して承認プロセスに移行します。
"""

                    # タスク説明に worktree 情報と完了指示を追加
                    enhanced_prompt = task_description
                    if agent_worktree:
                        enhanced_prompt = f"""⚠️ あなたは独自の git worktree で作業しています。
Worktree: {agent_worktree}
Branch: {agent_branch}

完了したら変更を commit してください。
マージは CTO が確認後に行います。

{task_description}
{completion_instruction}"""
                    else:
                        enhanced_prompt = f"""{task_description}
{completion_instruction}"""

                    # tmuxペイン内でclaude-codeをインタラクティブモードで実行
                    # 1. インタラクティブclaudeを起動
                    success = self.tmux_manager.execute_claude_in_pane(
                        pane_id=pane_id,
                        model=model,
                        work_dir=work_dir,
                        allow_unsafe=self.config.security.allow_unsafe_operations,
                    )

                    if not success:
                        if self.log_viewer_widget:
                            self.log_viewer_widget.add_log(
                                f"❌ Failed to start interactive claude in tmux pane {pane_id}",
                                level="ERROR",
                                agent_id="cto",
                            )
                        return

                    # 2. claude起動待ち
                    await asyncio.sleep(3)

                    # 3. プロンプトを送信
                    self.tmux_manager.send_prompt_to_claude_pane(pane_id, enhanced_prompt)

                    if self.log_viewer_widget:
                        self.log_viewer_widget.add_log(
                            f"✅ Successfully started interactive claude for {agent_id} in pane {pane_id}",
                            level="INFO",
                            agent_id="cto",
                        )

                    self.agents[agent_id] = {
                        "role": role,
                        "pane_id": pane_id,
                        "task": task_description,
                        "worktree": agent_worktree,
                        "branch": agent_branch,
                        "model": model,
                        "task_number": task_number,
                        "start_time": datetime.utcnow().isoformat(),
                        "log_file": log_file,
                    }

                    if self.log_viewer_widget:
                        self.log_viewer_widget.add_log(
                            f"✅ {agent_id} started in tmux pane {pane_id}",
                            level="INFO",
                            agent_id="cto",
                        )
                else:
                    if self.log_viewer_widget:
                        self.log_viewer_widget.add_log(
                            f"⚠️ Could not assign {agent_id} to tmux pane",
                            level="WARN",
                            agent_id="cto",
                        )
            else:
                # tmuxなしの場合はエラー（新アーキテクチャではtmux必須）
                if self.log_viewer_widget:
                    self.log_viewer_widget.add_log(
                        f"❌ tmux manager not available. tmux is required for agent execution.",
                        level="ERROR",
                        agent_id="cto",
                    )
                return

        except Exception as e:
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    f"❌ Failed to spawn agent {agent_id}: {str(e)}",
                    level="ERROR",
                    agent_id="cto",
                )

    async def _start_next_task(self: "InteractiveDashboard") -> None:
        """次のタスクを開始"""
        if self.current_task_index >= len(self.task_queue):
            # 全タスク完了
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    "🎉 全タスクが完了しました！",
                    level="INFO",
                    agent_id="cto",
                )
            return

        # 現在のタスクを取得
        current_task = self.task_queue[self.current_task_index]
        current_task['status'] = 'in_progress'

        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"▶️ タスク{current_task['task_num']}を開始: {current_task['description'][:50]}...",
                level="INFO",
                agent_id="cto",
            )

        # エージェントを起動
        try:
            await self._spawn_task_agent(
                task_description=current_task['description'],
                role=current_task['role'],
                model=current_task['model'],
                task_number=current_task['task_num'],
            )
        except Exception as e:
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    f"❌ タスク{current_task['task_num']}の起動に失敗: {str(e)}",
                    level="ERROR",
                    agent_id="cto",
                )
            import traceback
            traceback.print_exc()
