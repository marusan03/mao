"""
Tmux Executor Mixin - 実行・ログ管理
"""
import subprocess
import shlex
import re
from pathlib import Path
from typing import Dict, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mao.orchestrator.tmux_manager import TmuxManager


class TmuxExecutorMixin:
    """実行・ログ管理を担当するミックスイン"""

    def assign_agent_to_pane(
        self: "TmuxManager",
        role: str,
        agent_id: str,
        work_dir: Path,
        log_file: Optional[Path] = None
    ) -> Optional[str]:
        """グリッドレイアウトでエージェントをペインに割り当て

        Args:
            role: エージェントのロール（manager, agent-1, etc.）
            agent_id: エージェントID
            work_dir: claudeの作業ディレクトリ
            log_file: ログファイルパス（指定時はpipe-pane有効化）

        Returns:
            割り当てられたpane_id、失敗時はNone
        """
        if not self.use_grid_layout:
            return None

        if role not in self.grid_panes:
            self.logger.warning(f"Role {role} not found in grid layout")
            return None

        pane_id = self.grid_panes[role]

        # ペインをクリア
        self._send_to_pane(pane_id, "clear")

        # 作業ディレクトリに移動
        safe_work_dir = shlex.quote(str(work_dir))
        self._send_to_pane(pane_id, f"cd {safe_work_dir}")

        # pipe-pane 有効化（ログファイル指定がある場合）
        if log_file:
            self.enable_pane_logging(pane_id, log_file)

        # 準備完了メッセージを表示
        self._send_to_pane(
            pane_id,
            f"echo '🤖 Agent {role} ready. Waiting for tasks...'"
        )

        self.panes[agent_id] = pane_id
        return pane_id

    def execute_claude_in_pane(
        self: "TmuxManager",
        pane_id: str,
        model: str = "sonnet",
        work_dir: Optional[Path] = None,
        allow_unsafe: bool = False,
    ) -> bool:
        """tmuxペイン内でclaudeをインタラクティブモードで起動

        Args:
            pane_id: 実行するペインID
            model: モデル名（sonnet, opus, haiku）
            work_dir: 作業ディレクトリ
            allow_unsafe: --dangerously-skip-permissions を使用するか

        Returns:
            コマンド送信成功したかどうか
        """
        try:
            # claudeコマンドを構築（--printなし = インタラクティブ）
            cmd_parts = [
                "claude",
                "--model", model,
            ]

            if allow_unsafe:
                cmd_parts.append("--dangerously-skip-permissions")

            if work_dir:
                safe_work_dir = shlex.quote(str(work_dir))
                cmd_parts.extend(["--add-dir", safe_work_dir])

            command = " ".join(cmd_parts)

            # tmuxペイン内でコマンドを実行
            self._send_to_pane(pane_id, command)

            return True

        except Exception as e:
            self.logger.error(f"Failed to start interactive claude: {e}")
            return False

    def is_pane_busy(self: "TmuxManager", pane_id: str) -> bool:
        """ペインでプロセスが実行中かチェック

        Args:
            pane_id: ペインID

        Returns:
            プロセス実行中ならTrue
        """
        try:
            # tmux display-message でペインの実行状態を取得
            # pane_in_mode: コピーモードなど特殊モードにいるか
            # pane_current_command: 現在実行中のコマンド
            result = subprocess.run(
                ["tmux", "display-message", "-p", "-t", pane_id, "#{pane_current_command}"],
                capture_output=True,
                text=True,
                check=True
            )
            current_command = result.stdout.strip()

            # シェル以外のコマンドが実行中ならbusy
            # bash, zsh, sh などはアイドル状態
            idle_shells = ["bash", "zsh", "sh", "fish", "ksh"]
            return current_command not in idle_shells

        except subprocess.CalledProcessError:
            return False

    def get_pane_content(self: "TmuxManager", pane_id: str, lines: int = 100) -> str:
        """ペインの内容を取得

        Args:
            pane_id: ペインID
            lines: 取得する行数

        Returns:
            ペインの内容
        """
        try:
            result = subprocess.run(
                ["tmux", "capture-pane", "-p", "-t", pane_id, "-S", f"-{lines}"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to capture pane content: {e}")
            return ""

    def get_pane_status(self: "TmuxManager", pane_id: str) -> Dict[str, Any]:
        """ペインの詳細ステータスを取得

        Args:
            pane_id: ペインID

        Returns:
            ステータス情報の辞書
        """
        try:
            # 複数の情報を一度に取得
            result = subprocess.run(
                [
                    "tmux", "display-message", "-p", "-t", pane_id,
                    "#{pane_current_command}|||#{pane_pid}|||#{pane_active}|||#{pane_dead}"
                ],
                capture_output=True,
                text=True,
                check=True
            )

            parts = result.stdout.strip().split("|||")
            if len(parts) >= 4:
                return {
                    "current_command": parts[0],
                    "pid": int(parts[1]) if parts[1].isdigit() else None,
                    "active": parts[2] == "1",
                    "dead": parts[3] == "1",
                    "busy": parts[0] not in ["bash", "zsh", "sh", "fish", "ksh"]
                }

        except (subprocess.CalledProcessError, ValueError) as e:
            self.logger.error(f"Failed to get pane status: {e}")

        return {
            "current_command": None,
            "pid": None,
            "active": False,
            "dead": True,
            "busy": False
        }

    def enable_pane_logging(self: "TmuxManager", pane_id: str, log_file: Path) -> bool:
        """ペインの出力をログファイルにパイプ

        Args:
            pane_id: ペインID
            log_file: ログファイルパス

        Returns:
            成功したかどうか
        """
        try:
            safe_log_file = shlex.quote(str(log_file))

            # pipe-pane で出力を tee に送る
            # -o: 追記モード
            # tee -a: ログファイルに追記しつつ、ペインにも表示
            subprocess.run(
                [
                    "tmux", "pipe-pane", "-t", pane_id,
                    "-o", f"tee -a {safe_log_file}"
                ],
                check=True
            )

            self.logger.info(f"Enabled pipe-pane for {pane_id} -> {log_file}")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to enable pipe-pane: {e}")
            return False

    def disable_pane_logging(self: "TmuxManager", pane_id: str) -> bool:
        """ペインのパイプを無効化

        Args:
            pane_id: ペインID

        Returns:
            成功したかどうか
        """
        try:
            subprocess.run(
                ["tmux", "pipe-pane", "-t", pane_id],
                check=True
            )

            self.logger.info(f"Disabled pipe-pane for {pane_id}")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to disable pipe-pane: {e}")
            return False

    def send_prompt_to_claude_pane(
        self: "TmuxManager",
        pane_id: str,
        prompt: str,
    ) -> bool:
        """インタラクティブclaudeにプロンプトを送信

        Args:
            pane_id: ペインID
            prompt: 送信するプロンプト

        Returns:
            成功したかどうか
        """
        try:
            # プロンプトを一時ファイルに書き出し
            prompt_file = Path(f"/tmp/.mao_prompt_{pane_id.replace(':', '_')}.txt")
            prompt_file.write_text(prompt, encoding="utf-8")

            # claudeにファイルパスを送信（claudeはファイルを読み取ってくれる）
            # または直接テキストを送信（短いプロンプトの場合）
            if len(prompt) < 500:
                # 短いプロンプトは直接送信
                # エスケープ処理
                escaped_prompt = prompt.replace("'", "'\\''").replace("\n", " ")
                self._send_to_pane(pane_id, escaped_prompt)
            else:
                # 長いプロンプトはファイル経由で送信
                # claudeにファイルを読むよう指示
                self._send_to_pane(
                    pane_id,
                    f"Please read and follow the instructions in {prompt_file}"
                )

            self.logger.info(f"Sent prompt to claude in pane {pane_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send prompt to claude pane: {e}")
            return False

    def start_cto_with_output_capture(
        self: "TmuxManager",
        pane_id: str,
        log_file: Path,
        model: str = "sonnet",
        work_dir: Optional[Path] = None,
    ) -> bool:
        """CTOをインタラクティブモードで起動し、出力をキャプチャ

        Args:
            pane_id: ペインID
            log_file: ログファイルパス
            model: モデル名
            work_dir: 作業ディレクトリ

        Returns:
            成功したかどうか
        """
        try:
            # 1. pipe-paneでログファイルに出力
            self.enable_pane_logging(pane_id, log_file)

            # 2. インタラクティブclaudeを起動
            return self.execute_claude_in_pane(
                pane_id=pane_id,
                model=model,
                work_dir=work_dir,
                allow_unsafe=True,  # CTOは全権限
            )

        except Exception as e:
            self.logger.error(f"Failed to start CTO with output capture: {e}")
            return False

    def detect_task_completion(
        self: "TmuxManager",
        pane_id: str,
        log_file: Path,
    ) -> Optional[Dict[str, Any]]:
        """エージェントのタスク完了を検出

        Args:
            pane_id: ペインID
            log_file: ログファイルパス

        Returns:
            完了情報の辞書、未完了ならNone
        """
        try:
            # ログファイルから最新の出力を読み取り
            content = ""
            if log_file.exists():
                content = log_file.read_text(encoding="utf-8", errors="ignore")

            if not content:
                # ログファイルがない場合はペインから直接取得
                content = self.get_pane_content(pane_id, lines=200)

            # 完了パターンを検出
            completion_patterns = [
                r"\[MAO_TASK_COMPLETE\]",  # 明示的な完了マーカー
                r"タスクを完了しました",
                r"Task completed",
                r"変更をコミットしました",
                r"All changes have been committed",
            ]

            for pattern in completion_patterns:
                if re.search(pattern, content):
                    # 完了マーカーの詳細を抽出
                    task_complete_match = re.search(
                        r"\[MAO_TASK_COMPLETE\](.*?)\[/MAO_TASK_COMPLETE\]",
                        content,
                        re.DOTALL
                    )

                    completion_info = {
                        "completed": True,
                        "output": content,
                        "pattern_matched": pattern,
                    }

                    if task_complete_match:
                        # 構造化された完了情報をパース
                        marker_content = task_complete_match.group(1)
                        status_match = re.search(r"status:\s*(\w+)", marker_content)
                        summary_match = re.search(r"summary:\s*(.+?)(?:\n|$)", marker_content)
                        files_match = re.search(r"changed_files:\s*\n((?:\s*-\s*.+\n?)+)", marker_content)

                        if status_match:
                            completion_info["status"] = status_match.group(1)
                        if summary_match:
                            completion_info["summary"] = summary_match.group(1).strip()
                        if files_match:
                            files_text = files_match.group(1)
                            files = [f.strip().lstrip("- ") for f in files_text.strip().split("\n") if f.strip()]
                            completion_info["changed_files"] = files

                    return completion_info

            return None

        except Exception as e:
            self.logger.error(f"Failed to detect task completion: {e}")
            return None
