"""
Agent state management system
"""
import asyncio
import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import logging


class AgentStatus(str, Enum):
    """エージェントの状態"""

    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    THINKING = "THINKING"
    WAITING = "WAITING"
    ERROR = "ERROR"
    COMPLETED = "COMPLETED"


@dataclass
class AgentState:
    """エージェント状態"""

    agent_id: str
    role: str
    status: AgentStatus
    current_task: str = ""
    tokens_used: int = 0
    cost: float = 0.0
    last_updated: str = ""
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """辞書に変換"""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "status": self.status.value if isinstance(self.status, AgentStatus) else self.status,
            "current_task": self.current_task,
            "tokens_used": self.tokens_used,
            "cost": self.cost,
            "last_updated": self.last_updated,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        """辞書から作成"""
        # statusをEnumに変換
        if isinstance(data.get("status"), str):
            data["status"] = AgentStatus(data["status"])
        return cls(**data)


class StateManager:
    """エージェント状態管理マネージャー"""

    def __init__(
        self,
        project_path: Optional[Path] = None,
        use_sqlite: bool = True,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Args:
            project_path: プロジェクトパス（.maoディレクトリの親）
            use_sqlite: SQLiteを使用するか（Falseの場合はメモリのみ）
            logger: ロガー
        """
        self.project_path = project_path or Path.cwd()
        self.use_sqlite = use_sqlite
        self.logger = logger or logging.getLogger(__name__)

        # メモリ内状態（高速アクセス用）
        self._states: Dict[str, AgentState] = {}
        self._lock = asyncio.Lock()

        # SQLite接続
        self.db_path: Optional[Path] = None
        self.conn: Optional[sqlite3.Connection] = None

        if self.use_sqlite:
            self._init_database()

    def _init_database(self) -> None:
        """データベースを初期化"""
        mao_dir = self.project_path / ".mao"
        mao_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = mao_dir / "agent_states.db"

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # テーブル作成
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_states (
                agent_id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                current_task TEXT,
                tokens_used INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0,
                last_updated TEXT,
                error_message TEXT
            )
            """
        )
        self.conn.commit()

        # 既存データを読み込み
        self._load_from_database()

    def _load_from_database(self) -> None:
        """データベースから状態を読み込み"""
        if not self.conn:
            return

        cursor = self.conn.execute("SELECT * FROM agent_states")
        for row in cursor:
            state = AgentState(
                agent_id=row["agent_id"],
                role=row["role"],
                status=AgentStatus(row["status"]),
                current_task=row["current_task"] or "",
                tokens_used=row["tokens_used"] or 0,
                cost=row["cost"] or 0.0,
                last_updated=row["last_updated"] or "",
                error_message=row["error_message"],
            )
            self._states[state.agent_id] = state

    async def update_state(
        self,
        agent_id: str,
        role: str,
        status: AgentStatus,
        current_task: str = "",
        tokens_used: int = 0,
        cost: float = 0.0,
        error_message: Optional[str] = None,
    ) -> None:
        """エージェント状態を更新

        Args:
            agent_id: エージェントID
            role: ロール名
            status: ステータス
            current_task: 現在のタスク
            tokens_used: 使用トークン数
            cost: コスト
            error_message: エラーメッセージ
        """
        async with self._lock:
            state = AgentState(
                agent_id=agent_id,
                role=role,
                status=status,
                current_task=current_task,
                tokens_used=tokens_used,
                cost=cost,
                last_updated=datetime.utcnow().isoformat(),
                error_message=error_message,
            )

            self._states[agent_id] = state

            # SQLiteに保存
            if self.use_sqlite and self.conn:
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO agent_states
                    (agent_id, role, status, current_task, tokens_used, cost, last_updated, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        agent_id,
                        role,
                        status.value,
                        current_task,
                        tokens_used,
                        cost,
                        state.last_updated,
                        error_message,
                    ),
                )
                self.conn.commit()

    async def get_state(self, agent_id: str) -> Optional[AgentState]:
        """エージェント状態を取得

        Args:
            agent_id: エージェントID

        Returns:
            エージェント状態（存在しない場合はNone）
        """
        async with self._lock:
            return self._states.get(agent_id)

    async def get_all_states(self) -> List[AgentState]:
        """全エージェント状態を取得

        Returns:
            エージェント状態のリスト
        """
        async with self._lock:
            return list(self._states.values())

    async def clear_state(self, agent_id: str) -> None:
        """エージェント状態をクリア

        Args:
            agent_id: エージェントID
        """
        async with self._lock:
            if agent_id in self._states:
                del self._states[agent_id]

            if self.use_sqlite and self.conn:
                self.conn.execute("DELETE FROM agent_states WHERE agent_id = ?", (agent_id,))
                self.conn.commit()

    async def clear_all_states(self) -> None:
        """全エージェント状態をクリア"""
        async with self._lock:
            self._states.clear()

            if self.use_sqlite and self.conn:
                self.conn.execute("DELETE FROM agent_states")
                self.conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得

        Returns:
            統計情報
        """
        total_tokens = sum(state.tokens_used for state in self._states.values())
        total_cost = sum(state.cost for state in self._states.values())

        active_count = sum(
            1
            for state in self._states.values()
            if state.status in (AgentStatus.ACTIVE, AgentStatus.THINKING)
        )

        return {
            "total_agents": len(self._states),
            "active_agents": active_count,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
        }

    def close(self) -> None:
        """リソースをクリーンアップ"""
        if self.conn:
            self.conn.close()
            self.conn = None
