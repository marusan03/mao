"""
Task Decomposer Mixin - タスク分解ロジック
"""
import re
import yaml
import logging
from pathlib import Path
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from mao.orchestrator.task_dispatcher import TaskDispatcher, SubTask


class TaskDecomposerMixin:
    """タスク分解を担当するミックスイン"""

    async def decompose_task_with_cto(
        self: "TaskDispatcher", task_id: str, task_description: str, num_agents: int
    ) -> List["SubTask"]:
        """CTOエージェントを使ってタスクを分解

        Args:
            task_id: 親タスクID
            task_description: タスクの説明
            num_agents: 使用するエージェント数

        Returns:
            SubTaskのリスト
        """
        # Managerプロンプトを読み込み
        cto_prompt_file = Path(__file__).parent.parent / "agents" / "cto_prompt.md"

        if not cto_prompt_file.exists():
            # フォールバック：シンプルな分解
            return self.decompose_task_to_agents(task_id, task_description, num_agents)

        with open(cto_prompt_file) as f:
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
            # AgentExecutorを使用（tmux経由のCTOは別フロー）
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
            logging.error(f"Error in decompose_task_with_cto: {e}")
            return self.decompose_task_to_agents(task_id, task_description, num_agents)

    def _extract_tasks_from_yaml(
        self: "TaskDispatcher", response: str, parent_task_id: str
    ) -> List["SubTask"]:
        """応答からYAMLを抽出してSubTaskリストに変換

        Args:
            response: マネージャーの応答
            parent_task_id: 親タスクID

        Returns:
            SubTaskのリスト
        """
        from mao.orchestrator.task_dispatcher import SubTask

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
        self: "TaskDispatcher",
        task_id: str,
        task_description: str,
        num_agents: int | None = None
    ) -> List["SubTask"]:
        """タスクを複数のエージェント用サブタスクに分解（シンプル版）

        Args:
            task_id: 親タスクID
            task_description: タスクの説明
            num_agents: 使用するエージェント数（Noneの場合は自動決定）

        Returns:
            SubTaskのリスト
        """
        from mao.orchestrator.task_dispatcher import SubTask

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
