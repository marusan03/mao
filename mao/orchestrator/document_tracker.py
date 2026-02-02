"""
Document Tracker - 実装とドキュメントの同期を支援
"""
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging


class DocumentTracker:
    """ドキュメント追跡マネージャー

    実装に関連するドキュメントを追跡し、実装完了後に
    ドキュメントを自動的に更新するための情報を管理する。
    """

    def __init__(
        self,
        project_path: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Args:
            project_path: プロジェクトパス
            logger: ロガー
        """
        self.project_path = project_path or Path.cwd()
        self.logger = logger or logging.getLogger(__name__)

        # データベースパス
        self.db_dir = self.project_path / ".mao"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.db_dir / "document_tracking.db"

        # 接続
        self.conn: Optional[sqlite3.Connection] = None
        self._init_database()

    def _init_database(self) -> None:
        """データベース初期化"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # テーブル作成
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                document_path TEXT NOT NULL,
                reason TEXT,
                section TEXT,
                line_start INTEGER,
                line_end INTEGER,
                tracked_at TEXT NOT NULL,
                updated BOOLEAN DEFAULT 0,
                update_notes TEXT
            )
            """
        )

        # 既存のテーブルに行数カラムを追加（マイグレーション）
        try:
            self.conn.execute("ALTER TABLE document_tracking ADD COLUMN line_start INTEGER")
        except sqlite3.OperationalError:
            pass  # カラムが既に存在する場合

        try:
            self.conn.execute("ALTER TABLE document_tracking ADD COLUMN line_end INTEGER")
        except sqlite3.OperationalError:
            pass  # カラムが既に存在する場合

        # セッション情報テーブル
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tracking_sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT DEFAULT 'active'
            )
            """
        )

        self.conn.commit()

    def start_session(
        self,
        session_id: str,
        title: str,
        description: Optional[str] = None
    ) -> bool:
        """追跡セッションを開始

        Args:
            session_id: セッションID
            title: セッションタイトル
            description: セッション説明

        Returns:
            成功したかどうか
        """
        try:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO tracking_sessions
                (session_id, title, description, started_at, status)
                VALUES (?, ?, ?, ?, 'active')
                """,
                (session_id, title, description, datetime.utcnow().isoformat())
            )
            self.conn.commit()
            self.logger.info(f"Started tracking session: {session_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start session: {e}")
            return False

    def add_document(
        self,
        session_id: str,
        document_path: str,
        reason: str,
        section: Optional[str] = None,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None
    ) -> bool:
        """ドキュメントを追跡に追加

        Args:
            session_id: セッションID
            document_path: ドキュメントパス
            reason: 追跡理由
            section: 関連セクション
            line_start: 更新が必要な開始行番号（オプション）
            line_end: 更新が必要な終了行番号（オプション）

        Returns:
            成功したかどうか
        """
        try:
            self.conn.execute(
                """
                INSERT INTO document_tracking
                (session_id, document_path, reason, section, line_start, line_end, tracked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, document_path, reason, section, line_start, line_end, datetime.utcnow().isoformat())
            )
            self.conn.commit()
            self.logger.info(f"Added document to tracking: {document_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add document: {e}")
            return False

    def mark_updated(
        self,
        session_id: str,
        document_path: str,
        update_notes: Optional[str] = None
    ) -> bool:
        """ドキュメントを更新済みとしてマーク

        Args:
            session_id: セッションID
            document_path: ドキュメントパス
            update_notes: 更新メモ

        Returns:
            成功したかどうか
        """
        try:
            self.conn.execute(
                """
                UPDATE document_tracking
                SET updated = 1, update_notes = ?
                WHERE session_id = ? AND document_path = ?
                """,
                (update_notes, session_id, document_path)
            )
            self.conn.commit()
            self.logger.info(f"Marked document as updated: {document_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to mark document: {e}")
            return False

    def get_tracked_documents(self, session_id: str) -> List[Dict[str, Any]]:
        """追跡中のドキュメント一覧を取得

        Args:
            session_id: セッションID

        Returns:
            ドキュメントリスト
        """
        try:
            cursor = self.conn.execute(
                """
                SELECT * FROM document_tracking
                WHERE session_id = ?
                ORDER BY tracked_at
                """,
                (session_id,)
            )

            documents = []
            for row in cursor:
                documents.append({
                    "id": row["id"],
                    "document_path": row["document_path"],
                    "reason": row["reason"],
                    "section": row["section"],
                    "line_start": row["line_start"],
                    "line_end": row["line_end"],
                    "tracked_at": row["tracked_at"],
                    "updated": bool(row["updated"]),
                    "update_notes": row["update_notes"],
                })

            return documents
        except Exception as e:
            self.logger.error(f"Failed to get tracked documents: {e}")
            return []

    def get_pending_updates(self, session_id: str) -> List[Dict[str, Any]]:
        """未更新のドキュメント一覧を取得

        Args:
            session_id: セッションID

        Returns:
            未更新ドキュメントリスト
        """
        try:
            cursor = self.conn.execute(
                """
                SELECT * FROM document_tracking
                WHERE session_id = ? AND updated = 0
                ORDER BY tracked_at
                """,
                (session_id,)
            )

            documents = []
            for row in cursor:
                documents.append({
                    "id": row["id"],
                    "document_path": row["document_path"],
                    "reason": row["reason"],
                    "section": row["section"],
                    "line_start": row["line_start"],
                    "line_end": row["line_end"],
                    "tracked_at": row["tracked_at"],
                })

            return documents
        except Exception as e:
            self.logger.error(f"Failed to get pending updates: {e}")
            return []

    def complete_session(self, session_id: str) -> bool:
        """追跡セッションを完了

        Args:
            session_id: セッションID

        Returns:
            成功したかどうか
        """
        try:
            self.conn.execute(
                """
                UPDATE tracking_sessions
                SET status = 'completed', completed_at = ?
                WHERE session_id = ?
                """,
                (datetime.utcnow().isoformat(), session_id)
            )
            self.conn.commit()
            self.logger.info(f"Completed tracking session: {session_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to complete session: {e}")
            return False

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """セッション情報を取得

        Args:
            session_id: セッションID

        Returns:
            セッション情報
        """
        try:
            cursor = self.conn.execute(
                """
                SELECT * FROM tracking_sessions
                WHERE session_id = ?
                """,
                (session_id,)
            )

            row = cursor.fetchone()
            if row:
                return {
                    "session_id": row["session_id"],
                    "title": row["title"],
                    "description": row["description"],
                    "started_at": row["started_at"],
                    "completed_at": row["completed_at"],
                    "status": row["status"],
                }
            return None
        except Exception as e:
            self.logger.error(f"Failed to get session info: {e}")
            return None

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """アクティブなセッション一覧を取得

        Returns:
            セッションリスト
        """
        try:
            cursor = self.conn.execute(
                """
                SELECT * FROM tracking_sessions
                WHERE status = 'active'
                ORDER BY started_at DESC
                """
            )

            sessions = []
            for row in cursor:
                sessions.append({
                    "session_id": row["session_id"],
                    "title": row["title"],
                    "description": row["description"],
                    "started_at": row["started_at"],
                })

            return sessions
        except Exception as e:
            self.logger.error(f"Failed to get active sessions: {e}")
            return []

    def close(self) -> None:
        """データベース接続を閉じる"""
        if self.conn:
            self.conn.close()
            self.conn = None
