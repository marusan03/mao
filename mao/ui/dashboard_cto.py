"""
Dashboard CTO Mixin - CTOとの通信
"""
import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from mao.orchestrator.state_manager import AgentStatus

if TYPE_CHECKING:
    from mao.ui.dashboard_interactive import InteractiveDashboard


class DashboardCTOMixin:
    """CTO通信を担当するミックスイン"""

    # CTOインタラクティブモード状態
    _cto_started: bool = False
    _cto_monitor_task: asyncio.Task = None
    _cto_log_file: Path = None

    async def send_to_cto_interactive(self: "InteractiveDashboard", message: str) -> None:
        """CTOにメッセージを送信（インタラクティブモード - tmuxペイン経由）

        tmuxが有効な場合のみ使用。CTOペインでclaudeをインタラクティブモードで起動し、
        プロンプトを送信する。出力はpipe-paneでログファイルにキャプチャされ、
        monitor_cto_outputで監視される。

        Args:
            message: CTOに送信するメッセージ
        """
        if not self.tmux_manager or "cto" not in self.tmux_manager.grid_panes:
            self.logger.error("CTO pane not available for interactive mode")
            # フォールバック: 従来の方法で実行
            await self.send_to_cto(message)
            return

        pane_id = self.tmux_manager.grid_panes["cto"]
        self._cto_log_file = self.project_path / ".mao" / "logs" / "cto_output.log"
        self._cto_log_file.parent.mkdir(parents=True, exist_ok=True)

        # CTOの状態を更新（実行中）
        await self.state_manager.update_state(
            agent_id="cto",
            role="cto",
            status=AgentStatus.THINKING,
            current_task=f"処理中: {message[:30]}...",
        )

        try:
            # 初回: claudeを起動
            if not self._cto_started:
                # ログファイルを初期化
                self._cto_log_file.write_text("", encoding="utf-8")

                success = self.tmux_manager.start_cto_with_output_capture(
                    pane_id=pane_id,
                    log_file=self._cto_log_file,
                    model=self.initial_model,
                    work_dir=self.work_dir,
                )

                if not success:
                    self.logger.error("Failed to start CTO in interactive mode")
                    # フォールバック
                    await self.send_to_cto(message)
                    return

                self._cto_started = True

                # 監視タスク開始
                self._cto_monitor_task = asyncio.create_task(
                    self._monitor_cto_output()
                )

                # claude起動待ち
                await asyncio.sleep(3)

            # ストリーミングメッセージを開始
            if self.cto_chat_panel:
                self.cto_chat_panel.chat_widget.start_streaming_message()

            # プロンプトを構築（CTO用の完全なプロンプト）
            full_prompt = self._build_cto_prompt(message)

            # プロンプトをペインに送信
            self.tmux_manager.send_prompt_to_claude_pane(pane_id, full_prompt)

            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    f"CTO（インタラクティブ）にメッセージ送信: {message[:50]}...",
                    level="INFO",
                    agent_id="cto",
                )

        except Exception as e:
            self.logger.error(f"Failed to send to CTO interactive: {e}")
            if self.cto_chat_panel:
                self.cto_chat_panel.add_system_message(f"エラー: {str(e)}")

    async def _monitor_cto_output(self: "InteractiveDashboard") -> None:
        """CTOログファイルを監視してダッシュボードに反映"""
        last_position = 0

        while self._cto_started:
            try:
                if self._cto_log_file and self._cto_log_file.exists():
                    with open(self._cto_log_file, 'r', encoding="utf-8", errors="ignore") as f:
                        f.seek(last_position)
                        new_content = f.read()

                        if new_content:
                            # ダッシュボードのCTOチャットに追加
                            if self.cto_chat_panel:
                                self.cto_chat_panel.chat_widget.append_streaming_chunk(new_content)

                            # [MAO_AGENT_SPAWN]ブロックをパース
                            await self._extract_agent_spawns(new_content)

                            # フィードバックを抽出
                            self._extract_feedbacks(new_content)

                            # Feedback完了を検知
                            if self.feedback_branch and "[FEEDBACK_COMPLETED]" in new_content:
                                await self._handle_feedback_completion(new_content)

                        last_position = f.tell()

                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring CTO output: {e}")
                await asyncio.sleep(1.0)

    def _build_cto_prompt(self: "InteractiveDashboard", message: str) -> str:
        """CTO用の完全なプロンプトを構築

        Args:
            message: ユーザーからのメッセージ

        Returns:
            完全なCTOプロンプト
        """
        # 会話履歴を取得
        conversation_history = []
        if self.cto_chat_panel and self.cto_chat_panel.chat_widget:
            conversation_history = self.cto_chat_panel.chat_widget.get_conversation_history()

        # 会話履歴をフォーマット
        history_text = ""
        if conversation_history:
            history_text = "\n以下は今までの会話履歴です:\n\n"
            for msg in conversation_history:
                role_name = "User" if msg["role"] == "user" else "Assistant"
                history_text += f"{role_name}: {msg['content']}\n\n"
            history_text += "---\n\n"

        # Worktree ワークフローの説明を追加
        worktree_instructions = ""
        task_type = "Feedback" if "feedback/" in str(self.feedback_branch) else "Improvement"

        if self.feedback_branch and self.worktree_manager:
            worktree_instructions = f"""
---
⚠️ **Git Worktree ワークフロー有効**

現在、{task_type}ブランチ `{self.feedback_branch}` で作業しています。
エージェントは独自の git worktree と branch で作業します。
---
"""

        # MAOロール一覧を動的生成
        role_descriptions = []
        for role_name, role_config in self.available_roles.items():
            role_desc = f"   - **{role_name}**: {role_config.get('display_name', role_name)}"
            role_descriptions.append(role_desc)

        roles_text = "\n".join(role_descriptions)

        return f"""あなたはMAOシステムのCTO（Chief Technology Officer）です。

{history_text}
現在のユーザーからの依頼: {message}
{worktree_instructions}

**利用可能なMAOロール:**
{roles_text}

タスクを分解し、`/spawn-agent` スキルでエージェントを起動してください。

## タスク完了時の報告

タスクが完了したら、必ず以下のマーカーを出力してください：

[MAO_TASK_COMPLETE]
status: success または failed
changed_files:
  - file1.py
  - file2.py
summary: 変更内容の要約
[/MAO_TASK_COMPLETE]
"""

    async def send_to_cto(self: "InteractiveDashboard", message: str):
        """CTOにメッセージを送信して応答を取得"""
        if not self.cto_chat_panel:
            return

        self.cto_active = True

        # ストリーミングメッセージを開始
        self.cto_chat_panel.chat_widget.start_streaming_message()

        # CTOの状態を更新（実行中）
        await self.state_manager.update_state(
            agent_id="cto",
            role="cto",
            status=AgentStatus.THINKING,
            current_task=f"処理中: {message[:30]}...",
        )

        try:
            # 会話履歴を取得
            conversation_history = []
            if self.cto_chat_panel and self.cto_chat_panel.chat_widget:
                conversation_history = self.cto_chat_panel.chat_widget.get_conversation_history()

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
            task_type = "Feedback" if "feedback/" in str(self.feedback_branch) else "Improvement"

            if self.feedback_branch and self.worktree_manager:
                worktree_instructions = f"""
---
⚠️ **Git Worktree ワークフロー有効**

現在、{task_type}ブランチ `{self.feedback_branch}` で作業しています。

**{task_type}タイプについて:**
- **Feedback**: MAOプロジェクト自体の改善（どのプロジェクトからでもfeedbackを作成可能、MAOでのみimprove実行）
- **Improvement**: 任意のプロジェクトの改善（プロジェクト固有の機能追加や改善）

**エージェントの作業フロー:**
1. 各エージェントは独自の git worktree と branch で作業します
2. Worktree は自動的に作成されます（例: `{self.feedback_branch}-agent-1`）
3. エージェントは自分のブランチで変更を commit します
4. **マージプロセス:**
   - エージェントが作業を完了したら、CTOに報告してください
   - CTO はエージェントのブランチを確認し、問題なければ merge を承認します
   - エージェントのブランチは `{self.feedback_branch}` にマージされます

**CTOの責任:**
- エージェントの作業進捗を監視
- 完了したエージェントのコードをレビュー
- マージの承認/却下を判断
- すべてのエージェントが完了したら、全体の統合を確認
---
"""

            # MAOロール一覧を動的生成
            role_descriptions = []
            for role_name, role_config in self.available_roles.items():
                role_desc = f"   - **{role_name}**: {role_config.get('display_name', role_name)}"

                # 責務を追加
                responsibilities = role_config.get('responsibilities', [])
                if responsibilities:
                    role_desc += f"\n     用途: {', '.join(responsibilities[:3])}"

                # デフォルトモデル
                default_model = role_config.get('model', 'sonnet')
                role_desc += f"\n     推奨モデル: {default_model}"

                role_descriptions.append(role_desc)

            roles_text = "\n".join(role_descriptions)

            # Claude Code経由でCTOに送信（スキルベース）
            result = await self.cto_executor.execute_agent(
                prompt=f"""あなたはMAOシステムのCTO（Chief Technology Officer）です。

# 役割と責務

システム全体の技術責任を持ち、エージェントの作業を監視・管理します。

{history_text}
現在のユーザーからの依頼: {message}
{worktree_instructions}

上記の会話履歴を踏まえて、以下の手順で作業してください：

0. **📚 ドキュメント確認（必須）**
   タスク分析の前に、必ず関連ドキュメントを読んでください：

   a. **追跡中のドキュメントを確認:**
      - `/doc-track-show` スキルで追跡セッションを確認
      - 追跡中のドキュメントがあれば、それらを優先的に読む

   b. **プロジェクトドキュメントを読む:**
      - README.md（プロジェクト概要、使用方法）
      - 関連する設計ドキュメント（docs/以下）
      - API仕様、アーキテクチャ図など

   c. **既存実装を確認:**
      - 関連するコードファイルを読む
      - テストコードを確認

   ⚠️ **ドキュメントを読まずにタスク分解を行わないでください。**
   実装の整合性を保つため、必ず既存のドキュメントと実装を理解してください。

1. **タスク分析と分解**
   ドキュメント確認を完了してから、ユーザーからのリクエストを分析し、
   適切な粒度のタスクに分解します（1-5個）。

2. **ロール選択**
   各タスクに最適なMAOロールを選択します。

   **利用可能なMAOロール:**
{roles_text}

3. **エージェント起動（重要！）**
   ⚠️ **`/spawn-agent` スキルを使用してエージェントを起動してください:**

   ```
   /spawn-agent --task "JWT認証を使ったログイン機能を実装" --role coder_backend --model sonnet
   /spawn-agent --task "ログイン機能の単体テストと統合テストを作成" --role tester --model sonnet
   ```

   **各タスクごとに1回 `/spawn-agent` を呼び出してください。**

   **モデル選択ガイド:**
   - **opus**: 複雑な実装、重要な判断、アーキテクチャ設計
   - **sonnet**: 通常の実装タスク（推奨、バランス型）
   - **haiku**: シンプルなタスク、軽微な修正、調査タスク
   - モデル指定が不要な場合は省略可能（ロールのデフォルトが使用されます）

   ❌ 悪い例（スキルを使わない）:
   - "まず、既存コードを調査します"
   - "Task 1: コード調査"（テキストのみ）

   ✅ 良い例（スキルを使う）:
   ```
   /spawn-agent --task "既存の認証システムを調査" --role researcher --model haiku
   /spawn-agent --task "認証機能を実装" --role coder_backend --model sonnet
   ```

回答は簡潔に、具体的に行ってください。
**タスクを割り当てる場合は、必ず `/spawn-agent` スキルを使用してください。**

---
**Feedback改善モード完了フロー:**

すべてのタスクが完了したら、以下の手順で仕上げを行ってください：

1. **変更をコミット:**
   `/commit` スキルを使用して変更をコミット・プッシュします。
   例: `/commit -m "Fix: 認証バグを修正"`

2. **Pull Requestを作成:**
   `/pr` スキルを使用してPRを作成します。
   例: `/pr --title "Fix: 認証バグ修正" --labels bug`

3. **完了を宣言:**
   以下のフォーマットで完了を報告してください：
   ```
   [FEEDBACK_COMPLETED]
   PR: <PR URL>
   Summary: 完了した作業の簡潔な要約
   [/FEEDBACK_COMPLETED]
   ```

これにより、MAOは自動的にクリーンアップを行い、次のfeedbackに進みます。

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

                logger = logging.getLogger("mao.ui.dashboard")
                logger.debug(f"[Dashboard] CTO response received: {len(response)} chars")

                # レスポンスをストリーミングバッファに追加
                if self.cto_chat_panel and response:
                    logger.debug("[Dashboard] Adding response to CTO chat widget")
                    self.cto_chat_panel.chat_widget.append_streaming_chunk(response)
                    self.cto_chat_panel.chat_widget.complete_streaming_message()
                    logger.debug("[Dashboard] CTO response added to widget")
                else:
                    logger.warning(f"[Dashboard] Cannot add CTO response: cto_chat_panel={self.cto_chat_panel is not None}, response_len={len(response)}")

                # CTOの応答をセッションに保存
                self.session_manager.add_message(role="cto", content=response)

                # フィードバックを抽出
                self._extract_feedbacks(response)

                # Feedback完了を検知
                if self.feedback_branch and "[FEEDBACK_COMPLETED]" in response:
                    await self._handle_feedback_completion(response)

                # スキル経由のエージェント起動を抽出（新方式）
                await self._extract_agent_spawns(response)

                # レガシー: テキスト形式のタスク指示を抽出（旧方式、非推奨）
                # await self._extract_and_spawn_tasks(response)

                if self.log_viewer_widget:
                    self.log_viewer_widget.add_log(
                        f"CTO応答完了",
                        level="INFO",
                        agent_id="cto",
                    )

                # CTOの状態を更新（完了）
                await self.state_manager.update_state(
                    agent_id="cto",
                    role="cto",
                    status=AgentStatus.IDLE,
                    current_task="待機中",
                    tokens_used=result.get("tokens_used", 0),
                    cost=result.get("cost", 0.0),
                )
            else:
                error = result.get("error", "不明なエラー")
                if self.cto_chat_panel:
                    # ストリーミングメッセージをキャンセル（完了させない）
                    self.cto_chat_panel.chat_widget._streaming_message = None
                    self.cto_chat_panel.chat_widget._streaming_buffer = ""
                    self.cto_chat_panel.add_system_message(f"エラー: {error}")

                # CTOの状態を更新（エラー）
                await self.state_manager.update_state(
                    agent_id="cto",
                    role="cto",
                    status=AgentStatus.ERROR,
                    current_task="エラー発生",
                    error_message=error,
                )

        except Exception as e:
            if self.cto_chat_panel:
                # ストリーミングメッセージをキャンセル
                self.cto_chat_panel.chat_widget._streaming_message = None
                self.cto_chat_panel.chat_widget._streaming_buffer = ""
                self.cto_chat_panel.add_system_message(f"エラー: {str(e)}")

            # CTOの状態を更新（エラー）
            await self.state_manager.update_state(
                agent_id="cto",
                role="cto",
                status=AgentStatus.ERROR,
                current_task="例外発生",
                error_message=str(e),
            )

        finally:
            self.cto_active = False
