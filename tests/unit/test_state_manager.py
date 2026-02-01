"""
Tests for StateManager
"""
import pytest
import asyncio
from pathlib import Path
from mao.orchestrator.state_manager import StateManager, AgentState, AgentStatus


class TestAgentState:
    """AgentState のテスト"""

    def test_agent_state_initialization(self):
        """AgentState の初期化"""
        state = AgentState(
            agent_id="agent-1",
            role="coder",
            status=AgentStatus.ACTIVE,
            current_task="Coding feature X",
            tokens_used=1234,
            cost=0.05,
            last_updated="2026-02-01T10:00:00",
        )

        assert state.agent_id == "agent-1"
        assert state.role == "coder"
        assert state.status == AgentStatus.ACTIVE
        assert state.current_task == "Coding feature X"
        assert state.tokens_used == 1234
        assert state.cost == 0.05
        assert state.last_updated == "2026-02-01T10:00:00"
        assert state.error_message is None

    def test_agent_state_to_dict(self):
        """to_dict() メソッドのテスト"""
        state = AgentState(
            agent_id="agent-1",
            role="coder",
            status=AgentStatus.THINKING,
            current_task="Thinking...",
            tokens_used=500,
            cost=0.02,
            last_updated="2026-02-01T10:00:00",
            error_message="Test error",
        )

        data = state.to_dict()

        assert data["agent_id"] == "agent-1"
        assert data["role"] == "coder"
        assert data["status"] == "THINKING"
        assert data["current_task"] == "Thinking..."
        assert data["tokens_used"] == 500
        assert data["cost"] == 0.02
        assert data["last_updated"] == "2026-02-01T10:00:00"
        assert data["error_message"] == "Test error"

    def test_agent_state_from_dict(self):
        """from_dict() メソッドのテスト"""
        data = {
            "agent_id": "agent-2",
            "role": "reviewer",
            "status": "IDLE",
            "current_task": "Waiting",
            "tokens_used": 0,
            "cost": 0.0,
            "last_updated": "2026-02-01T11:00:00",
            "error_message": None,
        }

        state = AgentState.from_dict(data)

        assert state.agent_id == "agent-2"
        assert state.role == "reviewer"
        assert state.status == AgentStatus.IDLE
        assert state.current_task == "Waiting"
        assert state.tokens_used == 0
        assert state.cost == 0.0


class TestStateManagerMemoryOnly:
    """StateManager のテスト（メモリのみ）"""

    @pytest.mark.asyncio
    async def test_initialization_memory_only(self, tmp_path):
        """メモリのみモードでの初期化"""
        manager = StateManager(project_path=tmp_path, use_sqlite=False)

        assert manager.project_path == tmp_path
        assert manager.use_sqlite is False
        assert manager.db_path is None
        assert manager.conn is None
        assert len(manager._states) == 0

    @pytest.mark.asyncio
    async def test_update_state(self, tmp_path):
        """状態の更新"""
        manager = StateManager(project_path=tmp_path, use_sqlite=False)

        await manager.update_state(
            agent_id="worker-1",
            role="coder",
            status=AgentStatus.ACTIVE,
            current_task="Writing tests",
            tokens_used=2000,
            cost=0.08,
        )

        state = await manager.get_state("worker-1")
        assert state is not None
        assert state.agent_id == "worker-1"
        assert state.role == "coder"
        assert state.status == AgentStatus.ACTIVE
        assert state.current_task == "Writing tests"
        assert state.tokens_used == 2000
        assert state.cost == 0.08

    @pytest.mark.asyncio
    async def test_get_all_states(self, tmp_path):
        """全状態の取得"""
        manager = StateManager(project_path=tmp_path, use_sqlite=False)

        await manager.update_state(
            agent_id="agent-1", role="coder", status=AgentStatus.ACTIVE
        )
        await manager.update_state(
            agent_id="agent-2", role="reviewer", status=AgentStatus.IDLE
        )
        await manager.update_state(
            agent_id="agent-3", role="tester", status=AgentStatus.THINKING
        )

        states = await manager.get_all_states()

        assert len(states) == 3
        agent_ids = {state.agent_id for state in states}
        assert agent_ids == {"agent-1", "agent-2", "agent-3"}

    @pytest.mark.asyncio
    async def test_clear_state(self, tmp_path):
        """状態のクリア"""
        manager = StateManager(project_path=tmp_path, use_sqlite=False)

        await manager.update_state(
            agent_id="agent-1", role="coder", status=AgentStatus.ACTIVE
        )
        await manager.update_state(
            agent_id="agent-2", role="reviewer", status=AgentStatus.IDLE
        )

        await manager.clear_state("agent-1")

        state1 = await manager.get_state("agent-1")
        state2 = await manager.get_state("agent-2")

        assert state1 is None
        assert state2 is not None

    @pytest.mark.asyncio
    async def test_clear_all_states(self, tmp_path):
        """全状態のクリア"""
        manager = StateManager(project_path=tmp_path, use_sqlite=False)

        await manager.update_state(
            agent_id="agent-1", role="coder", status=AgentStatus.ACTIVE
        )
        await manager.update_state(
            agent_id="agent-2", role="reviewer", status=AgentStatus.IDLE
        )

        await manager.clear_all_states()

        states = await manager.get_all_states()
        assert len(states) == 0

    @pytest.mark.asyncio
    async def test_get_stats(self, tmp_path):
        """統計情報の取得"""
        manager = StateManager(project_path=tmp_path, use_sqlite=False)

        await manager.update_state(
            agent_id="agent-1",
            role="coder",
            status=AgentStatus.ACTIVE,
            tokens_used=1000,
            cost=0.04,
        )
        await manager.update_state(
            agent_id="agent-2",
            role="reviewer",
            status=AgentStatus.THINKING,
            tokens_used=500,
            cost=0.02,
        )
        await manager.update_state(
            agent_id="agent-3",
            role="tester",
            status=AgentStatus.IDLE,
            tokens_used=200,
            cost=0.01,
        )

        stats = manager.get_stats()

        assert stats["total_agents"] == 3
        assert stats["active_agents"] == 2  # ACTIVE + THINKING
        assert stats["total_tokens"] == 1700
        assert stats["total_cost"] == 0.07

    @pytest.mark.asyncio
    async def test_update_existing_state(self, tmp_path):
        """既存の状態を更新"""
        manager = StateManager(project_path=tmp_path, use_sqlite=False)

        # 初回更新
        await manager.update_state(
            agent_id="agent-1",
            role="coder",
            status=AgentStatus.ACTIVE,
            tokens_used=1000,
            cost=0.04,
        )

        # 同じエージェントを更新
        await manager.update_state(
            agent_id="agent-1",
            role="coder",
            status=AgentStatus.COMPLETED,
            tokens_used=2000,
            cost=0.08,
        )

        state = await manager.get_state("agent-1")
        assert state.status == AgentStatus.COMPLETED
        assert state.tokens_used == 2000
        assert state.cost == 0.08

    @pytest.mark.asyncio
    async def test_error_message(self, tmp_path):
        """エラーメッセージの保存"""
        manager = StateManager(project_path=tmp_path, use_sqlite=False)

        await manager.update_state(
            agent_id="agent-1",
            role="coder",
            status=AgentStatus.ERROR,
            error_message="Connection timeout",
        )

        state = await manager.get_state("agent-1")
        assert state.status == AgentStatus.ERROR
        assert state.error_message == "Connection timeout"


class TestStateManagerSQLite:
    """StateManager のテスト（SQLite有効）"""

    @pytest.mark.asyncio
    async def test_initialization_with_sqlite(self, tmp_path):
        """SQLiteモードでの初期化"""
        manager = StateManager(project_path=tmp_path, use_sqlite=True)

        assert manager.use_sqlite is True
        assert manager.db_path is not None
        assert manager.db_path.exists()
        assert manager.conn is not None

        manager.close()

    @pytest.mark.asyncio
    async def test_persistence_across_instances(self, tmp_path):
        """インスタンス間でのデータ永続化"""
        # 最初のインスタンスで状態を保存
        manager1 = StateManager(project_path=tmp_path, use_sqlite=True)
        await manager1.update_state(
            agent_id="agent-1",
            role="coder",
            status=AgentStatus.ACTIVE,
            tokens_used=1500,
            cost=0.06,
        )
        manager1.close()

        # 2番目のインスタンスで読み込み
        manager2 = StateManager(project_path=tmp_path, use_sqlite=True)
        state = await manager2.get_state("agent-1")

        assert state is not None
        assert state.agent_id == "agent-1"
        assert state.tokens_used == 1500
        assert state.cost == 0.06

        manager2.close()

    @pytest.mark.asyncio
    async def test_clear_state_with_sqlite(self, tmp_path):
        """SQLiteでの状態クリア"""
        manager = StateManager(project_path=tmp_path, use_sqlite=True)

        await manager.update_state(
            agent_id="agent-1", role="coder", status=AgentStatus.ACTIVE
        )
        await manager.clear_state("agent-1")

        # 再読み込みして確認
        manager.close()
        manager2 = StateManager(project_path=tmp_path, use_sqlite=True)
        state = await manager2.get_state("agent-1")

        assert state is None

        manager2.close()

    @pytest.mark.asyncio
    async def test_clear_all_states_with_sqlite(self, tmp_path):
        """SQLiteでの全状態クリア"""
        manager = StateManager(project_path=tmp_path, use_sqlite=True)

        await manager.update_state(
            agent_id="agent-1", role="coder", status=AgentStatus.ACTIVE
        )
        await manager.update_state(
            agent_id="agent-2", role="reviewer", status=AgentStatus.IDLE
        )

        await manager.clear_all_states()

        # 再読み込みして確認
        manager.close()
        manager2 = StateManager(project_path=tmp_path, use_sqlite=True)
        states = await manager2.get_all_states()

        assert len(states) == 0

        manager2.close()
