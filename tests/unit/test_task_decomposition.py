"""
Tests for task decomposition functionality
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from mao.orchestrator.task_dispatcher import TaskDispatcher, SubTask


class TestExtractTasksFromYAML:
    """_extract_tasks_from_yaml() のテスト"""

    def test_extract_tasks_from_valid_yaml(self):
        """有効なYAMLからタスク抽出"""
        dispatcher = TaskDispatcher()

        response = """
Here are the decomposed tasks:

```yaml
tasks:
  - id: task-1
    title: Implement login
    role: coder_backend
    priority: high
    description: Implement user login functionality
  - id: task-2
    title: Create UI
    role: coder_frontend
    priority: medium
    description: Create login UI components
```
"""

        subtasks = dispatcher._extract_tasks_from_yaml(response, "parent-1")

        assert len(subtasks) == 2
        assert subtasks[0].subtask_id == "task-1"
        assert subtasks[0].description == "Implement user login functionality"
        assert subtasks[0].role == "coder_backend"
        assert subtasks[0].priority == "high"
        assert subtasks[1].subtask_id == "task-2"
        assert subtasks[1].role == "coder_frontend"

    def test_extract_tasks_without_yaml_markers(self):
        """YAMLマーカーなしの応答"""
        dispatcher = TaskDispatcher()

        response = """
tasks:
  - id: task-1
    title: Test task
    description: Test description
"""

        # YAMLマーカーがないので抽出できない
        subtasks = dispatcher._extract_tasks_from_yaml(response, "parent-1")
        assert len(subtasks) == 0

    def test_extract_tasks_with_title_only(self):
        """titleのみのタスク"""
        dispatcher = TaskDispatcher()

        response = """
```yaml
tasks:
  - id: task-1
    title: Simple task
    role: general
```
"""

        subtasks = dispatcher._extract_tasks_from_yaml(response, "parent-1")

        assert len(subtasks) == 1
        assert subtasks[0].description == "Simple task"  # titleがdescriptionになる

    def test_extract_tasks_with_auto_generated_id(self):
        """IDが指定されていないタスク"""
        dispatcher = TaskDispatcher()

        response = """
```yaml
tasks:
  - title: Task 1
    description: First task
  - title: Task 2
    description: Second task
```
"""

        subtasks = dispatcher._extract_tasks_from_yaml(response, "parent-1")

        assert len(subtasks) == 2
        assert subtasks[0].subtask_id == "parent-1-1"
        assert subtasks[1].subtask_id == "parent-1-2"

    def test_extract_tasks_with_invalid_yaml(self):
        """無効なYAML"""
        dispatcher = TaskDispatcher()

        response = """
```yaml
tasks:
  - id: task-1
    title: Task
  invalid: [broken yaml
```
"""

        # エラーを投げずに空リストを返す
        subtasks = dispatcher._extract_tasks_from_yaml(response, "parent-1")
        assert len(subtasks) == 0

    def test_extract_tasks_without_tasks_key(self):
        """tasksキーがないYAML"""
        dispatcher = TaskDispatcher()

        response = """
```yaml
items:
  - name: Not a task
```
"""

        subtasks = dispatcher._extract_tasks_from_yaml(response, "parent-1")
        assert len(subtasks) == 0

    def test_extract_tasks_with_multiple_yaml_blocks(self):
        """複数のYAMLブロック"""
        dispatcher = TaskDispatcher()

        response = """
First attempt:
```yaml
tasks:
  - id: task-1
    description: First task
```

Revised:
```yaml
tasks:
  - id: task-2
    description: Second task
```
"""

        subtasks = dispatcher._extract_tasks_from_yaml(response, "parent-1")

        # 両方のブロックから抽出
        assert len(subtasks) == 2
        assert subtasks[0].subtask_id == "task-1"
        assert subtasks[1].subtask_id == "task-2"


class TestDecomposeTaskWithManager:
    """decompose_task_with_manager() のテスト"""

    @pytest.mark.asyncio
    async def test_decompose_with_executor(self, tmp_path):
        """executorを使ったタスク分解"""
        # Executorをモック
        mock_executor = AsyncMock()
        mock_executor.execute_agent = AsyncMock(return_value={
            "success": True,
            "response": """
```yaml
tasks:
  - id: auth-1
    title: Backend implementation
    role: coder_backend
    priority: high
    description: Implement authentication backend
  - id: auth-2
    title: Frontend implementation
    role: coder_frontend
    priority: medium
    description: Create login UI
```
"""
        })

        dispatcher = TaskDispatcher(
            project_path=tmp_path,
            executor=mock_executor,
        )

        # タスク分解を実行
        subtasks = await dispatcher.decompose_task_with_manager(
            task_id="main-task",
            task_description="Implement authentication system",
            num_workers=2,
        )

        # マネージャーが呼ばれたことを確認
        mock_executor.execute_agent.assert_called_once()

        # タスクが抽出されたことを確認
        assert len(subtasks) == 2
        assert subtasks[0].subtask_id == "auth-1"
        assert subtasks[0].role == "coder_backend"
        assert subtasks[1].subtask_id == "auth-2"
        assert subtasks[1].role == "coder_frontend"

    @pytest.mark.asyncio
    async def test_decompose_without_executor(self, tmp_path):
        """executorなしでのフォールバック"""
        dispatcher = TaskDispatcher(project_path=tmp_path)

        subtasks = await dispatcher.decompose_task_with_manager(
            task_id="main-task",
            task_description="Test task",
            num_workers=3,
        )

        # フォールバック（decompose_task_to_workers）が呼ばれる
        assert len(subtasks) == 3  # num_workersの数だけ作成される

    @pytest.mark.asyncio
    async def test_decompose_with_executor_error(self, tmp_path):
        """executorエラー時のフォールバック"""
        mock_executor = AsyncMock()
        mock_executor.execute_agent = AsyncMock(return_value={
            "success": False,
            "error": "Connection error",
        })

        dispatcher = TaskDispatcher(
            project_path=tmp_path,
            executor=mock_executor,
        )

        subtasks = await dispatcher.decompose_task_with_manager(
            task_id="main-task",
            task_description="Test task",
            num_workers=2,
        )

        # エラー時もフォールバックでタスクが作成される
        assert len(subtasks) == 2


class TestSubTask:
    """SubTask クラスのテスト"""

    def test_subtask_initialization(self):
        """SubTask の初期化"""
        subtask = SubTask(
            subtask_id="task-1",
            parent_task_id="parent-1",
            description="Test task",
            role="coder",
            priority="high",
        )

        assert subtask.subtask_id == "task-1"
        assert subtask.parent_task_id == "parent-1"
        assert subtask.description == "Test task"
        assert subtask.role == "coder"
        assert subtask.priority == "high"
        assert subtask.status == "pending"
        assert subtask.worker_id is None

    def test_subtask_to_dict(self):
        """to_dict() メソッドのテスト"""
        subtask = SubTask(
            subtask_id="task-1",
            parent_task_id="parent-1",
            description="Test task",
        )

        data = subtask.to_dict()

        assert data["subtask_id"] == "task-1"
        assert data["parent_task_id"] == "parent-1"
        assert data["description"] == "Test task"
        assert data["status"] == "pending"
        assert "created_at" in data
