"""
tmux session management for agent visualization
"""
import subprocess
import shlex
import logging
from typing import Optional, Dict
from pathlib import Path


class TmuxManager:
    """tmuxセッションを管理してエージェントごとにペインを作成"""

    def __init__(
        self,
        session_name: str = "mao",
        use_grid_layout: bool = False,
        grid_width: int = 240,
        grid_height: int = 60,
        num_agents: int = 8,
        logger: Optional[logging.Logger] = None,
    ):
        self.session_name = session_name
        self.use_grid_layout = use_grid_layout
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.num_agents = num_agents
        self.panes: Dict[str, str] = {}  # agent_id -> pane_id
        self.grid_panes: Dict[str, str] = {}  # role -> pane_id (grid mode)
        self.logger = logger or logging.getLogger(__name__)

    def is_tmux_available(self) -> bool:
        """tmuxが利用可能かチェック"""
        try:
            subprocess.run(["tmux", "-V"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def session_exists(self) -> bool:
        """セッションが存在するかチェック"""
        try:
            result = subprocess.run(
                ["tmux", "has-session", "-t", self.session_name], capture_output=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def create_session(self) -> bool:
        """tmuxセッションを作成"""
        if self.session_exists():
            self.logger.info(f"tmux session '{self.session_name}' already exists")
            return True

        if self.use_grid_layout:
            return self.create_session_with_grid()

        try:
            # デタッチ状態でセッション作成
            subprocess.run(
                [
                    "tmux",
                    "new-session",
                    "-d",  # detached
                    "-s",
                    self.session_name,
                    "-n",
                    "orchestrator",  # window name
                ],
                check=True,
            )

            # 最初のペインに説明を表示
            self._send_to_pane("0", self._get_header())

            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create tmux session: {e}")
            return False

    def create_session_with_grid(self) -> bool:
        """3×3グリッドレイアウトでセッションを作成（multi-agent-shogun風）"""
        try:
            # 1. セッション作成（大きめのウィンドウサイズで）
            subprocess.run(
                [
                    "tmux",
                    "new-session",
                    "-d",
                    "-s",
                    self.session_name,
                    "-n",
                    "multiagent",
                    "-x", str(self.grid_width),
                    "-y", str(self.grid_height),
                ],
                check=True,
            )

            # ペインの境界にタイトルを表示する設定
            subprocess.run(
                ["tmux", "set-option", "-t", self.session_name, "pane-border-status", "top"],
                check=True,
            )
            subprocess.run(
                ["tmux", "set-option", "-t", self.session_name, "pane-border-format",
                 "#[fg=cyan,bold] #{pane_title} "],
                check=True,
            )

            # 2. 3×3グリッド作成（9ペイン）
            # 方法: まず3行作成、次に各行を3列に分割

            # ステップ1: 縦に2回分割して3行作る
            subprocess.run(
                ["tmux", "split-window", "-v", "-t", f"{self.session_name}:0.0"],
                check=True,
            )
            subprocess.run(
                ["tmux", "split-window", "-v", "-t", f"{self.session_name}:0.0"],
                check=True,
            )

            # ステップ2: 各行を横に2回分割して3列にする
            # 1行目（pane 0）を3列に
            subprocess.run(
                ["tmux", "split-window", "-h", "-t", f"{self.session_name}:0.0"],
                check=True,
            )
            subprocess.run(
                ["tmux", "split-window", "-h", "-t", f"{self.session_name}:0.1"],
                check=True,
            )

            # 2行目（pane 3）を3列に
            subprocess.run(
                ["tmux", "split-window", "-h", "-t", f"{self.session_name}:0.3"],
                check=True,
            )
            subprocess.run(
                ["tmux", "split-window", "-h", "-t", f"{self.session_name}:0.4"],
                check=True,
            )

            # 3行目（pane 6）を3列に
            subprocess.run(
                ["tmux", "split-window", "-h", "-t", f"{self.session_name}:0.6"],
                check=True,
            )
            subprocess.run(
                ["tmux", "split-window", "-h", "-t", f"{self.session_name}:0.7"],
                check=True,
            )

            # 3. レイアウトを均等に調整
            subprocess.run(
                ["tmux", "select-layout", "-t", f"{self.session_name}:0", "tiled"],
                check=True,
            )

            # 4. 各ペインに役割を割り当て
            roles = ["manager"] + [f"agent-{i}" for i in range(1, self.num_agents + 1)]

            for idx, role in enumerate(roles):
                pane_id = f"{self.session_name}:0.{idx}"
                self.grid_panes[role] = pane_id

                # ペインタイトルを設定
                role_display = {
                    "manager": "📋 MANAGER",
                    "agent-1": "🔧 AGENT-1",
                    "agent-2": "🔧 AGENT-2",
                    "agent-3": "🔧 AGENT-3",
                    "agent-4": "🔧 AGENT-4",
                    "agent-5": "🔧 AGENT-5",
                    "agent-6": "🔧 AGENT-6",
                    "agent-7": "🔧 AGENT-7",
                    "agent-8": "🔧 AGENT-8",
                }.get(role, role.upper())

                subprocess.run(
                    ["tmux", "select-pane", "-t", pane_id, "-T", role_display],
                    check=True,
                )

                # ペインをクリア（何も表示しない）
                self._send_to_pane(pane_id, "clear")

            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create grid session: {e}")
            return False

    def create_pane_for_agent(
        self, agent_id: str, agent_name: str, log_file: Path
    ) -> Optional[str]:
        """エージェント用のペインを作成"""
        try:
            # 新しいペインを分割して作成
            result = subprocess.run(
                [
                    "tmux",
                    "split-window",
                    "-t",
                    f"{self.session_name}:0",
                    "-d",  # detached
                    "-P",  # print pane ID
                    "-F",
                    "#{pane_id}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            pane_id = result.stdout.strip()
            self.panes[agent_id] = pane_id

            # ペインにヘッダーと tail コマンドを送信
            header = f"""
╔════════════════════════════════════════╗
║  {agent_name:^38s}  ║
║  Agent ID: {agent_id:<28s} ║
╚════════════════════════════════════════╝

Waiting for agent to start...
"""
            self._send_to_pane(pane_id, f"clear && cat << 'EOF'\n{header}\nEOF")

            # ログファイルをtail（シェルインジェクション対策）
            safe_log_file = shlex.quote(str(log_file))
            self._send_to_pane(
                pane_id,
                f"tail -f {safe_log_file} 2>/dev/null || echo 'Waiting for log file...'",
            )

            # レイアウトを整理（tiled layout）
            subprocess.run(
                ["tmux", "select-layout", "-t", f"{self.session_name}:0", "tiled"]
            )

            return pane_id

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create pane for {agent_name}: {e}")
            return None

    def remove_pane(self, agent_id: str) -> None:
        """エージェントのペインを削除"""
        if agent_id in self.panes:
            pane_id = self.panes[agent_id]
            try:
                subprocess.run(["tmux", "kill-pane", "-t", pane_id])
                del self.panes[agent_id]
            except subprocess.CalledProcessError:
                pass

    def destroy_session(self) -> None:
        """セッションを破棄"""
        if self.session_exists():
            try:
                subprocess.run(["tmux", "kill-session", "-t", self.session_name])
                self.logger.info(f"✓ tmux session '{self.session_name}' destroyed")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to destroy session: {e}")

    def _send_to_pane(self, pane_id: str, command: str) -> None:
        """ペインにコマンドを送信"""
        subprocess.run(["tmux", "send-keys", "-t", pane_id, command, "C-m"])

    def _get_header(self) -> str:
        """最初のペイン用のヘッダー"""
        return """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     Multi-Agent Orchestrator - Agent Monitor              ║
║                                                           ║
║  This tmux session shows real-time logs from each agent   ║
║  Each pane represents one active agent                    ║
║                                                           ║
║  Controls:                                                ║
║    Ctrl+B then arrow keys - Navigate between panes        ║
║    Ctrl+B then z          - Zoom into a pane             ║
║    Ctrl+B then d          - Detach from session          ║
║                                                           ║
║  Main dashboard is running in another terminal            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

Waiting for agents to start...
"""


    def set_layout(self, layout: str = "tiled") -> None:
        """レイアウトを変更

        Args:
            layout: tiled, even-horizontal, even-vertical, main-horizontal, main-vertical
        """
        try:
            subprocess.run(
                ["tmux", "select-layout", "-t", f"{self.session_name}:0", layout]
            )
        except subprocess.CalledProcessError:
            pass

    def assign_agent_to_pane(self, role: str, agent_id: str, work_dir: Path) -> Optional[str]:
        """グリッドレイアウトでエージェントをペインに割り当て

        Args:
            role: エージェントのロール（manager, agent-1, etc.）
            agent_id: エージェントID
            work_dir: claude-codeの作業ディレクトリ

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

        # 準備完了メッセージを表示
        self._send_to_pane(
            pane_id,
            f"echo '🤖 Agent {role} ready. Waiting for tasks...'"
        )

        self.panes[agent_id] = pane_id
        return pane_id

    def execute_claude_code_in_pane(
        self,
        pane_id: str,
        prompt: str,
        model: str = "sonnet",
        work_dir: Optional[Path] = None,
        allow_unsafe: bool = False,
    ) -> bool:
        """tmuxペイン内でclaude-codeを実行

        Args:
            pane_id: 実行するペインID
            prompt: claude-codeに渡すプロンプト
            model: モデル名（sonnet, opus, haiku）
            work_dir: 作業ディレクトリ
            allow_unsafe: --dangerously-skip-permissions を使用するか

        Returns:
            コマンド送信成功したかどうか
        """
        try:
            # 一時ファイルにプロンプトを書き込む
            if work_dir:
                prompt_file = work_dir / f".mao_prompt_{pane_id.replace(':', '_')}.txt"
            else:
                prompt_file = Path(f"/tmp/.mao_prompt_{pane_id.replace(':', '_')}.txt")

            prompt_file.write_text(prompt, encoding="utf-8")

            # claude-codeコマンドを構築
            safe_prompt_file = shlex.quote(str(prompt_file))
            cmd_parts = [
                "cat", safe_prompt_file, "|",
                "claude-code", "--print",
                "--model", model,
            ]

            if allow_unsafe:
                cmd_parts.append("--dangerously-skip-permissions")

            if work_dir:
                safe_work_dir = shlex.quote(str(work_dir))
                cmd_parts.extend(["--add-dir", safe_work_dir])

            command = " ".join(cmd_parts)

            # tmuxペイン内でコマンドを実行
            # 重要: send-keysは2回に分けないとEnterが効かない（Zenn記事の知見）
            self._send_to_pane(pane_id, command)

            return True

        except Exception as e:
            self.logger.error(f"Failed to execute claude-code in pane: {e}")
            return False

    def execute_interactive_claude_code_in_pane(
        self,
        pane_id: str,
        model: str = "sonnet",
        work_dir: Optional[Path] = None,
        allow_unsafe: bool = False,
    ) -> bool:
        """tmuxペイン内でclaude-codeをインタラクティブモードで起動

        Args:
            pane_id: 実行するペインID
            model: モデル名（sonnet, opus, haiku）
            work_dir: 作業ディレクトリ
            allow_unsafe: --dangerously-skip-permissions を使用するか

        Returns:
            コマンド送信成功したかどうか
        """
        try:
            # claude-codeコマンドを構築（--printなし = インタラクティブ）
            cmd_parts = [
                "claude-code",
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
            self.logger.error(f"Failed to start interactive claude-code: {e}")
            return False

    def start_agent_loop_in_pane(
        self,
        pane_id: str,
        role: str,
        project_path: Path,
        model: str = "sonnet",
        poll_interval: float = 2.0,
        allow_unsafe: bool = False,
    ) -> bool:
        """tmuxペイン内でエージェントループを起動

        Args:
            pane_id: 実行するペインID
            role: エージェントロール（agent-1, agent-2, etc.）
            project_path: プロジェクトルートパス
            model: モデル名
            poll_interval: ポーリング間隔（秒）
            allow_unsafe: --dangerously-skip-permissions を使用するか

        Returns:
            コマンド送信成功したかどうか
        """
        try:
            # agent_loop.pyのパス
            agent_loop_script = Path(__file__).parent / "agent_loop.py"

            # コマンドを構築
            cmd_parts = [
                "python3",
                shlex.quote(str(agent_loop_script)),
                "--role", role,
                "--project-path", shlex.quote(str(project_path)),
                "--model", model,
                "--poll-interval", str(poll_interval),
            ]

            if allow_unsafe:
                cmd_parts.append("--allow-unsafe")

            command = " ".join(cmd_parts)

            # tmuxペイン内でコマンドを実行
            self._send_to_pane(pane_id, command)

            self.logger.info(f"Started agent loop for {role} in pane {pane_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start agent loop: {e}")
            return False

    def is_pane_busy(self, pane_id: str) -> bool:
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

    def get_pane_content(self, pane_id: str, lines: int = 100) -> str:
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

    def get_pane_status(self, pane_id: str) -> Dict[str, any]:
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
