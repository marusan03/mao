"""
Dashboard Parser Mixin - CTOの応答からタスク・フィードバックを抽出
"""
from datetime import datetime
import asyncio
import re
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mao.ui.dashboard_interactive import InteractiveDashboard


class DashboardParserMixin:
    """CTOの応答をパースするミックスイン"""

    async def _handle_feedback_completion(self: "InteractiveDashboard", response: str) -> None:
        """Feedback完了を処理

        Args:
            response: CTOの応答テキスト
        """
        # PR URLとサマリーを抽出
        completion_pattern = r'\[FEEDBACK_COMPLETED\](.*?)\[/FEEDBACK_COMPLETED\]'
        match = re.search(completion_pattern, response, re.DOTALL)

        if match:
            completion_info = match.group(1)

            # PR URLを抽出
            pr_match = re.search(r'PR:\s*(.+)', completion_info)
            pr_url = pr_match.group(1).strip() if pr_match else "N/A"

            # サマリーを抽出
            summary_match = re.search(r'Summary:\s*(.+)', completion_info, re.DOTALL)
            summary = summary_match.group(1).strip() if summary_match else "完了"

            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    f"✅ Feedback改善が完了しました",
                    level="INFO",
                    agent_id="cto",
                )
                self.log_viewer_widget.add_log(
                    f"PR: {pr_url}",
                    level="INFO",
                    agent_id="cto",
                )

            if self.cto_chat_panel:
                self.cto_chat_panel.add_system_message(
                    f"✅ Feedback改善完了\nPR: {pr_url}\n\nMAOを終了します..."
                )

            # 数秒待ってから終了
            await asyncio.sleep(3)
            self.exit()

    async def _extract_agent_spawns(self: "InteractiveDashboard", text: str) -> None:
        """CTOの応答からエージェント起動リクエストを抽出（スキル経由）

        Args:
            text: CTOの応答テキスト
        """
        # [MAO_AGENT_SPAWN]...[/MAO_AGENT_SPAWN] パターンを検索
        pattern = r'\[MAO_AGENT_SPAWN\](.*?)\[/MAO_AGENT_SPAWN\]'
        matches = re.findall(pattern, text, re.DOTALL)

        if not matches:
            # 旧形式（Task N:）も試す
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    "⚠️ /spawn-agent スキルが使用されていません。旧形式のタスク抽出を試みます...",
                    level="WARN",
                    agent_id="cto",
                )
            # 旧形式の抽出を実行
            await self._extract_and_spawn_tasks(text)
            return

        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"🔍 エージェント起動リクエスト: {len(matches)}件",
                level="INFO",
                agent_id="cto",
            )

        # タスクサマリーを作成
        task_summaries = []

        for idx, match in enumerate(matches, 1):
            try:
                # JSONをパース
                agent_data = json.loads(match.strip())

                task_description = agent_data.get("task", "")
                role = agent_data.get("role")
                model = agent_data.get("model")  # Noneの場合はロールデフォルト使用
                priority = agent_data.get("priority", "medium")

                if not task_description or not role:
                    if self.log_viewer_widget:
                        self.log_viewer_widget.add_log(
                            f"⚠️ 無効なエージェントデータ: task={task_description}, role={role}",
                            level="WARN",
                            agent_id="cto",
                        )
                    continue

                # ロールが有効か確認
                if role not in self.available_roles:
                    if self.log_viewer_widget:
                        self.log_viewer_widget.add_log(
                            f"❌ エラー: 未知のロール '{role}'",
                            level="ERROR",
                            agent_id="cto",
                        )
                    continue

                # タスクをキューに追加
                self.task_queue.append({
                    'task_num': idx,
                    'description': task_description,
                    'role': role,
                    'model': model,
                    'priority': priority,
                    'status': 'queued',
                })

                task_summaries.append({
                    'num': idx,
                    'description': task_description,
                    'role': role,
                    'model': model or self.available_roles[role].get("model", "sonnet"),
                })

                if self.log_viewer_widget:
                    model_display = model or self.available_roles[role].get("model", "sonnet")
                    self.log_viewer_widget.add_log(
                        f"📋 タスク{idx}をキューに追加: {task_description[:50]}... ({role}/{model_display})",
                        level="INFO",
                        agent_id="cto",
                    )

            except json.JSONDecodeError as e:
                if self.log_viewer_widget:
                    self.log_viewer_widget.add_log(
                        f"❌ JSON解析エラー: {str(e)}",
                        level="ERROR",
                        agent_id="cto",
                    )
                continue

        # Task Infoを更新
        if self.header_widget and task_summaries:
            task_info_text = f"CTOが{len(task_summaries)}つのタスクに分解:\n"
            for task in task_summaries[:3]:
                short_desc = task['description'][:40]
                if len(task['description']) > 40:
                    short_desc += "..."
                task_info_text += f"  {task['num']}. {short_desc}\n"

            if len(task_summaries) > 3:
                task_info_text += f"  ... 他{len(task_summaries) - 3}件"

            self.header_widget.update_task_info(
                task_description=task_info_text.strip(),
                active_count=0,
                total_count=len(task_summaries),
            )

        # シーケンシャルモードの場合、最初のタスクを開始
        if self.sequential_mode and self.task_queue and len(matches) > 0:
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    f"🎯 シーケンシャルモード: タスク1/{len(self.task_queue)}を開始",
                    level="INFO",
                    agent_id="cto",
                )
            await self._start_next_task()

    async def _extract_and_spawn_tasks(self: "InteractiveDashboard", text: str) -> None:
        """CTOの応答からタスク指示を抽出してエージェントを起動

        Args:
            text: CTOの応答テキスト
        """
        # デバッグ: CTOの完全な応答をファイルに保存
        debug_dir = self.project_path / ".mao" / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        debug_file = debug_dir / f"cto_response_{timestamp}.txt"
        debug_file.write_text(text, encoding="utf-8")

        # デバッグ: テキストの一部を表示
        if self.log_viewer_widget:
            preview = text[:200].replace('\n', ' ')
            self.log_viewer_widget.add_log(
                f"🔍 CTO応答を解析中... (先頭200文字: {preview}...)",
                level="DEBUG",
                agent_id="cto",
            )
            self.log_viewer_widget.add_log(
                f"📝 完全な応答を保存: {debug_file}",
                level="DEBUG",
                agent_id="cto",
            )

        # タスクパターンを検索 (Task N: で始まる行)
        # 空行区切りでタスクブロックを分離（Role/Model行も含める）
        task_pattern = r'(?:Task|タスク)\s*(\d+)[:：]\s*(.+?)(?=\n\s*\n(?:Task|タスク)|\n\s*\n---|\Z)'
        tasks = re.findall(task_pattern, text, re.DOTALL | re.MULTILINE)

        # デバッグ: マッチ数を表示
        if self.log_viewer_widget:
            self.log_viewer_widget.add_log(
                f"🔍 タスクパターンマッチ数: {len(tasks)}件",
                level="DEBUG",
                agent_id="cto",
            )

        if not tasks:
            # タスクが検出されなかった場合、警告を表示
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    "⚠️ CTOの応答からタスクが検出されませんでした",
                    level="WARN",
                    agent_id="cto",
                )
                self.log_viewer_widget.add_log(
                    "ヒント: CTOが「Task 1: ...」形式でタスクを記述していない可能性があります",
                    level="WARN",
                    agent_id="cto",
                )
            return

        # タスクサマリーを作成してTask Infoを更新
        task_summaries = []

        for task_num, task_content in tasks:
            # Role/ロール を抽出（ハイフン付きロール名に対応）
            role_match = re.search(r'(?:Role|ロール)[:：]\s*(\S+)', task_content, re.IGNORECASE)
            role = role_match.group(1) if role_match else "general-purpose"

            # Model/モデル を抽出
            model_match = re.search(r'(?:Model|モデル)[:：]\s*(\S+)', task_content, re.IGNORECASE)
            model = model_match.group(1) if model_match else "sonnet"

            # タスク説明を抽出（最初の行）
            task_lines = task_content.strip().split('\n')
            task_description = task_lines[0].strip()

            # サマリーに追加
            task_summaries.append({
                'num': task_num,
                'description': task_description,
                'role': role,
            })

            # タスクをキューに追加
            self.task_queue.append({
                'task_num': int(task_num),
                'description': task_description,
                'role': role,
                'model': model,
                'status': 'queued',
            })

            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    f"📋 タスク{task_num}をキューに追加: {role} ({model})",
                    level="INFO",
                    agent_id="cto",
                )

        # Task Infoを更新
        if self.header_widget and task_summaries:
            # 簡潔なタスク説明を作成
            task_info_text = f"CTOが{len(task_summaries)}つのタスクに分解:\n"
            for task in task_summaries[:3]:  # 最大3件表示
                short_desc = task['description'][:40]
                if len(task['description']) > 40:
                    short_desc += "..."
                task_info_text += f"  {task['num']}. {short_desc}\n"

            if len(task_summaries) > 3:
                task_info_text += f"  ... 他{len(task_summaries) - 3}件"

            # ヘッダーを更新
            self.header_widget.update_task_info(
                task_description=task_info_text.strip(),
                active_count=0,
                total_count=len(task_summaries),
            )

        # シーケンシャルモードの場合、最初のタスクを開始
        if self.sequential_mode and self.task_queue:
            if self.log_viewer_widget:
                self.log_viewer_widget.add_log(
                    f"🎯 シーケンシャルモード: タスク1/{len(self.task_queue)}を開始",
                    level="INFO",
                    agent_id="cto",
                )
            await self._start_next_task()

    def _extract_feedbacks(self: "InteractiveDashboard", text: str) -> None:
        """テキストからフィードバックを抽出して保存

        Args:
            text: 検索対象のテキスト
        """
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
                        agent_id="cto",
                        session_id=self.session_manager.session_id,
                    )

                    # ユーザーに通知
                    if self.cto_chat_panel:
                        self.cto_chat_panel.add_system_message(
                            f"📝 フィードバックを記録しました: {title} (ID: {feedback.id[-12:]})"
                        )
            except Exception as e:
                # フィードバック抽出エラーは無視（作業を妨げない）
                pass
