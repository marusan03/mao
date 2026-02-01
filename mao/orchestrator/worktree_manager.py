"""
Git Worktree Manager - エージェント用の分離された作業環境を管理
"""
import logging
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime


class WorktreeManager:
    """Git worktree を管理するクラス"""

    def __init__(
        self,
        project_path: Path,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Args:
            project_path: プロジェクトのルートパス
            logger: ロガー
        """
        self.project_path = project_path
        self.logger = logger or logging.getLogger(__name__)
        self.worktrees_dir = project_path / ".mao" / "worktrees"
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)

    def is_git_repository(self) -> bool:
        """Git リポジトリかどうか確認

        Returns:
            True if git repository
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            self.logger.debug(f"Not a git repository: {e}")
            return False

    def create_worktree(
        self,
        agent_id: str,
        role: str,
        branch: Optional[str] = None,
    ) -> Optional[Path]:
        """エージェント用の worktree を作成

        Args:
            agent_id: エージェントID
            role: エージェントロール
            branch: ブランチ名（Noneの場合は現在のブランチから分岐）

        Returns:
            作成された worktree のパス、作成できない場合はNone
        """
        if not self.is_git_repository():
            self.logger.warning("Not a git repository, cannot create worktree")
            return None

        # Worktree名を生成
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        worktree_name = f"{role}_{agent_id}_{timestamp}"
        worktree_path = self.worktrees_dir / worktree_name

        # ブランチ名を生成
        if branch is None:
            branch = f"mao/{role}/{agent_id}"

        try:
            # Worktree を作成
            self.logger.info(f"Creating worktree: {worktree_path}")
            result = subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-b",
                    branch,
                    str(worktree_path),
                ],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )

            self.logger.info(f"Worktree created: {worktree_path}")
            self.logger.debug(f"Git output: {result.stdout}")

            return worktree_path

        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Failed to create worktree: {e.stderr}",
                exc_info=True,
            )
            return None
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Worktree creation timeout: {e}")
            return None

    def remove_worktree(self, worktree_path: Path) -> bool:
        """Worktree を削除

        Args:
            worktree_path: 削除する worktree のパス

        Returns:
            成功したかどうか
        """
        if not worktree_path.exists():
            self.logger.warning(f"Worktree does not exist: {worktree_path}")
            return False

        try:
            self.logger.info(f"Removing worktree: {worktree_path}")

            # Worktree を削除
            result = subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )

            self.logger.info(f"Worktree removed: {worktree_path}")
            self.logger.debug(f"Git output: {result.stdout}")

            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Failed to remove worktree: {e.stderr}",
                exc_info=True,
            )
            return False
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Worktree removal timeout: {e}")
            return False

    def cleanup_worktrees(self) -> int:
        """すべての worktree を削除

        Returns:
            削除した worktree の数
        """
        if not self.worktrees_dir.exists():
            return 0

        cleaned = 0
        for worktree_path in self.worktrees_dir.iterdir():
            if worktree_path.is_dir():
                if self.remove_worktree(worktree_path):
                    cleaned += 1

        self.logger.info(f"Cleaned up {cleaned} worktrees")
        return cleaned

    def list_worktrees(self) -> list[Path]:
        """アクティブな worktree のリストを取得

        Returns:
            Worktree パスのリスト
        """
        if not self.worktrees_dir.exists():
            return []

        return [
            path
            for path in self.worktrees_dir.iterdir()
            if path.is_dir()
        ]

    def get_worktree_info(self, worktree_path: Path) -> dict[str, str]:
        """Worktree の情報を取得

        Args:
            worktree_path: Worktree のパス

        Returns:
            Worktree 情報（ブランチ名など）
        """
        if not worktree_path.exists():
            return {}

        try:
            # ブランチ名を取得
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )

            branch = result.stdout.strip()

            return {
                "path": str(worktree_path),
                "branch": branch,
                "name": worktree_path.name,
            }

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            self.logger.error(f"Failed to get worktree info: {e}")
            return {}

    def create_feedback_worktree(
        self, feedback_id: str, branch_name: str
    ) -> Optional[Path]:
        """Feedbackタスク用のworktreeを作成

        Args:
            feedback_id: フィードバックID
            branch_name: ブランチ名（例: feedback/123_abc-description）

        Returns:
            作成されたworktreeのパス、失敗時はNone
        """
        if not self.is_git_repository():
            return None

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        worktree_name = f"feedback-{feedback_id}-{timestamp}"
        worktree_path = self.worktrees_dir / worktree_name

        try:
            # ブランチを作成してworktreeを追加
            result = subprocess.run(
                ["git", "worktree", "add", "-b", branch_name, str(worktree_path)],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                self.logger.info(f"Created feedback worktree: {worktree_path}")
                return worktree_path
            else:
                self.logger.error(f"Failed to create feedback worktree: {result.stderr}")
                return None

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            self.logger.error(f"Exception creating feedback worktree: {e}")
            return None

    def create_worker_worktree(
        self, parent_branch: str, worker_id: str
    ) -> Optional[Path]:
        """ワーカー用のworktreeを作成

        Args:
            parent_branch: 親ブランチ名（feedbackブランチ）
            worker_id: ワーカーID

        Returns:
            作成されたworktreeのパス、失敗時はNone
        """
        if not self.is_git_repository():
            return None

        worker_branch = f"{parent_branch}-{worker_id}"
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        worktree_name = f"worker-{worker_id}-{timestamp}"
        worktree_path = self.worktrees_dir / worktree_name

        try:
            # 親ブランチから新規ブランチを作成してworktreeを追加
            result = subprocess.run(
                ["git", "worktree", "add", "-b", worker_branch, str(worktree_path), parent_branch],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                self.logger.info(f"Created worker worktree: {worktree_path}")
                return worktree_path
            else:
                self.logger.error(f"Failed to create worker worktree: {result.stderr}")
                return None

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            self.logger.error(f"Exception creating worker worktree: {e}")
            return None

    def merge_branch(
        self, target_worktree: Path, source_branch: str, commit_message: str
    ) -> bool:
        """ブランチをマージ

        Args:
            target_worktree: マージ先worktreeパス
            source_branch: マージ元ブランチ名
            commit_message: マージコミットメッセージ

        Returns:
            成功時True
        """
        try:
            result = subprocess.run(
                ["git", "merge", "--no-ff", "-m", commit_message, source_branch],
                cwd=target_worktree,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                self.logger.info(f"Merged {source_branch} into {target_worktree.name}")
                return True
            else:
                self.logger.error(f"Merge failed: {result.stderr}")
                return False

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            self.logger.error(f"Exception during merge: {e}")
            return False

    def push_branch(self, worktree_path: Path, branch_name: str) -> bool:
        """ブランチをリモートにプッシュ

        Args:
            worktree_path: worktreeパス
            branch_name: ブランチ名

        Returns:
            成功時True
        """
        try:
            result = subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            return result.returncode == 0

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            self.logger.error(f"Failed to push branch: {e}")
            return False

    def create_pr(
        self, worktree_path: Path, title: str, body: str, base: str = "main"
    ) -> Optional[str]:
        """GitHub PRを作成

        Args:
            worktree_path: worktreeパス
            title: PRタイトル
            body: PR説明
            base: ベースブランチ（デフォルト: main）

        Returns:
            PR URL、失敗時はNone
        """
        try:
            # gh コマンドでPR作成
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "create",
                    "--title",
                    title,
                    "--body",
                    body,
                    "--base",
                    base,
                ],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                pr_url = result.stdout.strip().split('\n')[-1]
                self.logger.info(f"Created PR: {pr_url}")
                return pr_url
            else:
                self.logger.error(f"Failed to create PR: {result.stderr}")
                return None

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            self.logger.error(f"Exception creating PR: {e}")
            return None
