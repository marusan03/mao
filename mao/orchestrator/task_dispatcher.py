"""
Task dispatcher for launching agents
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime
import logging

if TYPE_CHECKING:
    from mao.orchestrator.agent_executor import AgentExecutor
    from mao.orchestrator.agent_logger import AgentLogger

from mao.orchestrator.message_queue import MessageQueue
from mao.orchestrator.skill_manager import SkillManager
from mao.orchestrator.skill_formatter import SkillFormatter
from mao.orchestrator.task_decomposer import TaskDecomposerMixin
from mao.orchestrator.task_reporter import TaskReporterMixin


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


class TaskDispatcher(TaskDecomposerMixin, TaskReporterMixin):
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
        self.executor = executor  # AgentExecutor（オプション）

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

        # スキル管理
        self.skill_manager = SkillManager(self.project_path) if self.project_path else None
        self.skill_formatter = SkillFormatter()

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

    def _build_skills_section(self) -> str:
        """スキル情報をプロンプト用に構築"""
        if not self.skill_manager:
            return ""

        try:
            skills = self.skill_manager.list_skills()
            if not skills:
                return ""
            return self.skill_formatter.format_all_skills(skills)
        except Exception as e:
            logging.warning(f"Failed to load skills for prompt: {e}")
            return ""

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

        # スキルセクション構築
        skills_section = self._build_skills_section()

        # 最終プロンプト構築
        full_prompt = f"""
{base_prompt}

{coding_standards}

{lang_config}

{additional_context}

{skills_section}

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
