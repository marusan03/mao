"""
Task dispatcher for launching agents
"""
import yaml
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime
import logging

if TYPE_CHECKING:
    from mao.orchestrator.agent_executor import AgentExecutor
    from mao.orchestrator.agent_logger import AgentLogger

from mao.orchestrator.message_queue import MessageQueue, MessageType, MessagePriority


class SubTask:
    """サブタスク（エージェントに割り当てるタスク）"""

    def __init__(
        self,
        subtask_id: str,
        parent_task_id: str,
        description: str,
        agent_id: Optional[str] = None,
        role: str = "general",
        priority: str = "medium",
    ):
        self.subtask_id = subtask_id
        self.parent_task_id = parent_task_id
        self.description = description
        self.agent_id = agent_id
        self.role = role  # エージェントの役割
        self.priority = priority  # タスクの優先度
        self.status = "pending"
        self.created_at = datetime.utcnow().isoformat()
        self.result: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """辞書に変換"""
        return {
            "subtask_id": self.subtask_id,
            "parent_task_id": self.parent_task_id,
            "description": self.description,
            "agent_id": self.agent_id,
            "role": self.role,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at,
            "result": self.result,
        }


class TaskDispatcher:
    """Claude Code の Task tool を使ってエージェントを起動"""

    def __init__(
        self,
        project_path: Optional[Path] = None,
        max_agents: int = 8,
        executor: Optional[Any] = None,
    ):
        self.roles = self._load_roles()
        self.max_agents = max_agents
        self.project_path = project_path or Path.cwd()
        self.executor = executor  # AgentExecutor or ClaudeCodeExecutor

        # キューディレクトリ
        if self.project_path:
            self.queue_dir = self.project_path / ".mao" / "queue"
            self.tasks_dir = self.queue_dir / "tasks"
            self.results_dir = self.queue_dir / "results"

            # ディレクトリ作成
            self.queue_dir.mkdir(parents=True, exist_ok=True)
            self.tasks_dir.mkdir(exist_ok=True)
            self.results_dir.mkdir(exist_ok=True)

        # 現在のタスク管理
        self.current_subtasks: List[SubTask] = []

        # メッセージキュー
        self.message_queue = MessageQueue(project_path=self.project_path)

    def _load_roles(self) -> Dict[str, Any]:
        """全ロール定義を読み込み"""
        roles = {}

        # まず組み込みロールを探す
        # パッケージインストール後は mao/roles/ から読み込む
        # 開発中は相対パスから読み込む
        roles_dir = Path(__file__).parent.parent / "roles"

        if not roles_dir.exists():
            # パッケージとしてインストールされている場合
            import mao
            package_path = Path(mao.__file__).parent
            roles_dir = package_path / "roles"

        if roles_dir.exists():
            for yaml_file in roles_dir.rglob("*.yaml"):
                try:
                    with open(yaml_file) as f:
                        role_config = yaml.safe_load(f)
                        if role_config and "name" in role_config:
                            roles[role_config["name"]] = role_config
                except Exception as e:
                    print(f"Warning: Failed to load role from {yaml_file}: {e}")

        return roles

    def build_agent_prompt(self, role_name: str, task: Dict) -> str:
        """ロール設定からプロンプトを構築"""
        if role_name not in self.roles:
            raise ValueError(f"Unknown role: {role_name}")

        role = self.roles[role_name]

        # ベースプロンプト読み込み
        prompt_file = Path(role["prompt_file"])
        if not prompt_file.exists():
            # 相対パスの場合、ロールディレクトリからの相対パスとして解決
            roles_dir = Path(__file__).parent.parent / "roles"
            prompt_file = roles_dir / role["prompt_file"]

        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {role['prompt_file']}")

        with open(prompt_file) as f:
            base_prompt = f.read()

        # コーディング規約読み込み（該当する場合）
        coding_standards = ""
        if "coding_standards" in role:
            standards = []
            for std_file in role["coding_standards"]:
                std_path = Path(std_file)
                if std_path.exists():
                    with open(std_path) as f:
                        standards.append(f.read())
            if standards:
                coding_standards = (
                    "\n\n# Coding Standards\n\n" + "\n\n---\n\n".join(standards)
                )

        # 言語設定読み込み（該当する場合）
        lang_config = ""
        if "language_config" in role:
            lang_config_path = Path(role["language_config"])
            if lang_config_path.exists():
                with open(lang_config_path) as f:
                    lang_config = (
                        "\n\n# Language Configuration\n\n```yaml\n"
                        + f.read()
                        + "\n```"
                    )

        # 追加コンテキスト読み込み
        additional_context = ""
        if "additional_context" in role:
            contexts = []
            for ctx_file in role["additional_context"]:
                ctx_path = Path(ctx_file)
                if ctx_path.exists():
                    with open(ctx_path) as f:
                        contexts.append(f.read())
            if contexts:
                additional_context = (
                    "\n\n# Additional Context\n\n" + "\n\n---\n\n".join(contexts)
                )

        # 最終プロンプト構築
        full_prompt = f"""
{base_prompt}

{coding_standards}

{lang_config}

{additional_context}

---

# Your Current Task

{task['description']}

## Task Details
- Task ID: {task['id']}
- Priority: {task.get('priority', 'normal')}

## Expected Output
{task.get('expected_output', 'Complete the task and report results.')}
"""
        return full_prompt

    async def dispatch_task(
        self,
        role_name: str,
        task: Dict,
        executor: Optional["AgentExecutor"] = None,
        logger: Optional["AgentLogger"] = None,
    ) -> Dict[str, Any]:
        """タスクを該当ロールのエージェントにディスパッチ

        Args:
            role_name: ロール名
            task: タスク情報
            executor: エージェント実行エンジン（オプション）
            logger: エージェントロガー（オプション）

        Returns:
            実行結果またはエージェント設定
        """
        role = self.roles[role_name]
        prompt = self.build_agent_prompt(role_name, task)

        # モデル名変換
        model_mapping = {
            "opus": "claude-opus-4-20250514",
            "sonnet": "claude-sonnet-4-20250514",
            "haiku": "claude-haiku-4-20250514",
        }
        model = model_mapping.get(role.get("model", "sonnet"), "claude-sonnet-4-20250514")

        agent_config = {
            "role_name": role_name,
            "display_name": role["display_name"],
            "model": model,
            "prompt": prompt,
            "task": task,
        }

        # エグゼキューターが提供されている場合は実行
        if executor:
            result = await executor.execute_agent(
                prompt=prompt,
                model=model,
                logger=logger,
            )
            agent_config["result"] = result

        return agent_config

    async def decompose_task_with_manager(
        self, task_id: str, task_description: str, num_agents: int
    ) -> List[SubTask]:
        """Managerエージェントを使ってタスクを分解

        Args:
            task_id: 親タスクID
            task_description: タスクの説明
            num_agents: 使用するエージェント数

        Returns:
            SubTaskのリスト
        """
        # Managerプロンプトを読み込み
        manager_prompt_file = Path(__file__).parent.parent / "agents" / "manager_prompt.md"

        if not manager_prompt_file.exists():
            # フォールバック：シンプルな分解
            return self.decompose_task_to_agents(task_id, task_description, num_agents)

        with open(manager_prompt_file) as f:
            manager_prompt = f.read()

        # Managerエージェントに問い合わせ
        full_prompt = f"""{manager_prompt}

---

# User Task

{task_description}

**Available Agents**: {num_agents}

Please analyze this task and provide the decomposition in YAML format following this structure:

```yaml
tasks:
  - id: task-1
    title: Task title
    role: agent_role
    priority: high|medium|low
    description: Detailed description
```
"""

        # Managerエージェントを呼び出し
        try:
            # AgentExecutorまたはClaudeCodeExecutorを使用
            if hasattr(self, "executor") and self.executor:
                # マネージャーを実行（asyncメソッドなので直接await）
                result = await self.executor.execute_agent(
                    prompt=full_prompt,
                    model="claude-sonnet-4-20250514",
                )

                if not result.get("success"):
                    logging.warning(f"Manager execution failed: {result.get('error')}")
                    return self.decompose_task_to_agents(task_id, task_description, num_agents)

                response = result.get("response", "")

                # YAMLを抽出
                subtasks = self._extract_tasks_from_yaml(response, task_id)

                if subtasks:
                    return subtasks
                else:
                    logging.warning("No valid tasks extracted from manager response")
                    return self.decompose_task_to_agents(task_id, task_description, num_agents)

            else:
                # Executorが設定されていない場合はフォールバック
                return self.decompose_task_to_agents(task_id, task_description, num_agents)

        except Exception as e:
            logging.error(f"Error in decompose_task_with_manager: {e}")
            return self.decompose_task_to_agents(task_id, task_description, num_agents)

    def _extract_tasks_from_yaml(self, response: str, parent_task_id: str) -> List[SubTask]:
        """応答からYAMLを抽出してSubTaskリストに変換

        Args:
            response: マネージャーの応答
            parent_task_id: 親タスクID

        Returns:
            SubTaskのリスト
        """
        subtasks = []

        # YAMLブロックを抽出（```yaml ... ``` または ``` ... ```）
        yaml_pattern = r'```(?:yaml)?\s*\n(.*?)\n```'
        yaml_matches = re.findall(yaml_pattern, response, re.DOTALL)

        for yaml_text in yaml_matches:
            try:
                data = yaml.safe_load(yaml_text)

                if not data or "tasks" not in data:
                    continue

                tasks_data = data["tasks"]
                if not isinstance(tasks_data, list):
                    continue

                for task_data in tasks_data:
                    if not isinstance(task_data, dict):
                        continue

                    # 必須フィールドチェック
                    if "title" not in task_data and "description" not in task_data:
                        continue

                    # SubTaskを作成
                    subtask_id = task_data.get("id", f"{parent_task_id}-{len(subtasks) + 1}")
                    description = task_data.get("description") or task_data.get("title", "")
                    role = task_data.get("role", "general")
                    priority = task_data.get("priority", "medium")

                    subtask = SubTask(
                        subtask_id=subtask_id,
                        parent_task_id=parent_task_id,
                        description=description,
                        role=role,
                        priority=priority,
                    )
                    subtasks.append(subtask)

            except yaml.YAMLError as e:
                logging.warning(f"Failed to parse YAML: {e}")
                continue

        return subtasks

    def decompose_task_to_agents(
        self, task_id: str, task_description: str, num_agents: Optional[int] = None
    ) -> List[SubTask]:
        """タスクを複数のエージェント用サブタスクに分解（シンプル版）

        Args:
            task_id: 親タスクID
            task_description: タスクの説明
            num_agents: 使用するエージェント数（Noneの場合は自動決定）

        Returns:
            SubTaskのリスト
        """
        if num_agents is None:
            num_agents = 1

        num_agents = min(num_agents, self.max_agents)
        subtasks = []

        for idx in range(num_agents):
            subtask_id = f"{task_id}-sub{idx + 1}"
            agent_id = f"agent-{idx + 1}"

            subtask = SubTask(
                subtask_id=subtask_id,
                parent_task_id=task_id,
                description=task_description,
                agent_id=agent_id,
            )
            subtasks.append(subtask)

        self.current_subtasks = subtasks
        return subtasks

    def assign_tasks_to_agents(self, subtasks: List[SubTask]) -> None:
        """サブタスクをエージェントに割り当て（YAMLファイルに書き込み）"""
        for subtask in subtasks:
            if subtask.agent_id:
                self._write_agent_task(subtask.agent_id, subtask)

    def _write_agent_task(self, agent_id: str, subtask: SubTask) -> None:
        """エージェント用のタスクファイルを書き込み"""
        task_file = self.tasks_dir / f"{agent_id}.yaml"

        task_data = {
            "task": subtask.to_dict(),
            "assigned_at": datetime.utcnow().isoformat(),
        }

        with open(task_file, "w") as f:
            yaml.dump(task_data, f, default_flow_style=False, allow_unicode=True)

    def read_agent_result(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """エージェントの結果を読み込み"""
        result_file = self.results_dir / f"{agent_id}.yaml"

        if not result_file.exists():
            return None

        with open(result_file) as f:
            return yaml.safe_load(f)

    def collect_agent_results(self) -> Dict[str, Any]:
        """すべてのエージェントの結果を収集"""
        results = {}

        for subtask in self.current_subtasks:
            if subtask.agent_id:
                result = self.read_agent_result(subtask.agent_id)
                if result:
                    results[subtask.agent_id] = result
                    subtask.status = "completed"
                    subtask.result = result.get("result")

        return results

    def update_dashboard(self, task_id: str, task_description: str, status: str) -> None:
        """ダッシュボードを更新"""
        if not self.project_path:
            return

        dashboard_file = self.project_path / ".mao" / "dashboard.md"

        content = f"""# MAO Dashboard

## Current Task
**ID:** {task_id}
**Status:** {status}
**Description:** {task_description}

## Agents
"""

        for subtask in self.current_subtasks:
            agent_status = subtask.status
            content += f"- **{subtask.agent_id}**: {agent_status}\n"
            content += f"  - Task: {subtask.description}\n"
            if subtask.result:
                content += f"  - Result: {subtask.result[:100]}...\n"

        content += f"\n---\nLast updated: {datetime.utcnow().isoformat()}\n"

        with open(dashboard_file, "w") as f:
            f.write(content)

    def clear_queue(self) -> None:
        """キューをクリア"""
        # タスクファイルを削除
        for task_file in self.tasks_dir.glob("*.yaml"):
            task_file.unlink()

        # 結果ファイルを削除
        for result_file in self.results_dir.glob("*.yaml"):
            result_file.unlink()

    async def report_task_started(
        self, agent_id: str, subtask_id: str, description: str
    ) -> None:
        """エージェントがタスク開始を報告

        Args:
            agent_id: エージェントID
            subtask_id: サブタスクID
            description: タスク説明
        """
        await self.message_queue.send_message(
            message_type=MessageType.TASK_STARTED,
            sender=agent_id,
            receiver="manager",
            content=f"タスクを開始しました: {description}",
            priority=MessagePriority.MEDIUM,
            metadata={
                "subtask_id": subtask_id,
                "description": description,
            },
        )

        # サブタスクの状態を更新
        for subtask in self.current_subtasks:
            if subtask.subtask_id == subtask_id:
                subtask.status = "in_progress"
                break

    async def report_task_progress(
        self, agent_id: str, subtask_id: str, progress: str, percentage: Optional[int] = None
    ) -> None:
        """エージェントがタスク進捗を報告

        Args:
            agent_id: エージェントID
            subtask_id: サブタスクID
            progress: 進捗内容
            percentage: 進捗率（0-100）
        """
        await self.message_queue.send_message(
            message_type=MessageType.TASK_PROGRESS,
            sender=agent_id,
            receiver="manager",
            content=progress,
            priority=MessagePriority.LOW,
            metadata={
                "subtask_id": subtask_id,
                "percentage": percentage,
            },
        )

    async def report_task_completed(
        self, agent_id: str, subtask_id: str, result: str
    ) -> None:
        """エージェントがタスク完了を報告

        Args:
            agent_id: エージェントID
            subtask_id: サブタスクID
            result: 実行結果
        """
        await self.message_queue.send_message(
            message_type=MessageType.TASK_COMPLETED,
            sender=agent_id,
            receiver="manager",
            content=f"タスクが完了しました: {result[:100]}",
            priority=MessagePriority.HIGH,
            metadata={
                "subtask_id": subtask_id,
                "result": result,
            },
        )

        # サブタスクの状態を更新
        for subtask in self.current_subtasks:
            if subtask.subtask_id == subtask_id:
                subtask.status = "completed"
                subtask.result = result
                break

    async def report_task_failed(
        self, agent_id: str, subtask_id: str, error: str
    ) -> None:
        """エージェントがタスク失敗を報告

        Args:
            agent_id: エージェントID
            subtask_id: サブタスクID
            error: エラー内容
        """
        await self.message_queue.send_message(
            message_type=MessageType.TASK_FAILED,
            sender=agent_id,
            receiver="manager",
            content=f"タスクが失敗しました: {error}",
            priority=MessagePriority.URGENT,
            metadata={
                "subtask_id": subtask_id,
                "error": error,
            },
        )

        # サブタスクの状態を更新
        for subtask in self.current_subtasks:
            if subtask.subtask_id == subtask_id:
                subtask.status = "failed"
                break

    async def request_task_reassignment(
        self, subtask_id: str, reason: str, new_priority: Optional[str] = None
    ) -> bool:
        """タスクの再割り当てをリクエスト

        Args:
            subtask_id: サブタスクID
            reason: 再割り当て理由
            new_priority: 新しい優先度

        Returns:
            成功したかどうか
        """
        # サブタスクを検索
        subtask = None
        for st in self.current_subtasks:
            if st.subtask_id == subtask_id:
                subtask = st
                break

        if not subtask:
            logging.warning(f"Subtask {subtask_id} not found for reassignment")
            return False

        # 優先度を更新
        if new_priority:
            subtask.priority = new_priority

        # ステータスをリセット
        old_worker = subtask.agent_id
        subtask.status = "pending"
        subtask.agent_id = None
        subtask.result = None

        # メッセージを送信
        await self.message_queue.send_message(
            message_type=MessageType.REASSIGN_REQUEST,
            sender="manager",
            receiver="manager",  # 自分自身
            content=f"タスク {subtask_id} を再割り当て: {reason}",
            priority=MessagePriority.HIGH,
            metadata={
                "subtask_id": subtask_id,
                "reason": reason,
                "old_worker": old_worker,
                "new_priority": new_priority,
            },
        )

        logging.info(f"Task {subtask_id} reassignment requested: {reason}")
        return True

    async def retry_failed_task(self, subtask_id: str, max_retries: int = 3) -> bool:
        """失敗したタスクをリトライ

        Args:
            subtask_id: サブタスクID
            max_retries: 最大リトライ回数

        Returns:
            リトライを開始したかどうか
        """
        # サブタスクを検索
        subtask = None
        for st in self.current_subtasks:
            if st.subtask_id == subtask_id:
                subtask = st
                break

        if not subtask or subtask.status != "failed":
            return False

        # メタデータからリトライ回数を取得
        retry_count = getattr(subtask, "retry_count", 0)

        if retry_count >= max_retries:
            logging.warning(f"Task {subtask_id} exceeded max retries ({max_retries})")
            return False

        # リトライ回数を更新
        subtask.retry_count = retry_count + 1  # type: ignore

        # 再割り当てをリクエスト
        await self.request_task_reassignment(
            subtask_id=subtask_id,
            reason=f"リトライ ({retry_count + 1}/{max_retries})",
            new_priority="high",
        )

        return True

    async def get_pending_tasks(self) -> List[SubTask]:
        """未割り当てのタスクを取得

        Returns:
            未割り当てタスクのリスト
        """
        return [st for st in self.current_subtasks if st.status == "pending"]

    async def get_task_summary(self) -> Dict[str, Any]:
        """タスク全体のサマリーを取得

        Returns:
            サマリー情報
        """
        total = len(self.current_subtasks)
        pending = sum(1 for st in self.current_subtasks if st.status == "pending")
        in_progress = sum(1 for st in self.current_subtasks if st.status == "in_progress")
        completed = sum(1 for st in self.current_subtasks if st.status == "completed")
        failed = sum(1 for st in self.current_subtasks if st.status == "failed")

        return {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "failed": failed,
            "progress_percentage": (completed / total * 100) if total > 0 else 0,
        }
