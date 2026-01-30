"""
tmux session management for agent visualization
"""
import subprocess
from typing import Optional, Dict
from pathlib import Path


class TmuxManager:
    """tmuxセッションを管理してエージェントごとにペインを作成"""

    def __init__(self, session_name: str = "mao"):
        self.session_name = session_name
        self.panes: Dict[str, str] = {}  # agent_id -> pane_id

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
            print(f"tmux session '{self.session_name}' already exists")
            return True

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
            print(f"Failed to create tmux session: {e}")
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

            # ログファイルをtail
            self._send_to_pane(
                pane_id,
                f"tail -f {log_file} 2>/dev/null || echo 'Waiting for log file...'",
            )

            # レイアウトを整理（tiled layout）
            subprocess.run(
                ["tmux", "select-layout", "-t", f"{self.session_name}:0", "tiled"]
            )

            return pane_id

        except subprocess.CalledProcessError as e:
            print(f"Failed to create pane for {agent_name}: {e}")
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
                print(f"✓ tmux session '{self.session_name}' destroyed")
            except subprocess.CalledProcessError as e:
                print(f"Failed to destroy session: {e}")

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
