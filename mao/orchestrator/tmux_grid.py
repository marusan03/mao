"""
Tmux Grid Layout Mixin - グリッドレイアウト管理
"""
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mao.orchestrator.tmux_manager import TmuxManager


class TmuxGridMixin:
    """グリッドレイアウトを担当するミックスイン"""

    def create_session_with_grid(self: "TmuxManager") -> bool:
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
            roles = ["cto"] + [f"agent-{i}" for i in range(1, self.num_agents + 1)]

            for idx, role in enumerate(roles):
                pane_id = f"{self.session_name}:0.{idx}"
                self.grid_panes[role] = pane_id

                # ペインタイトルを設定
                role_display = {
                    "cto": "🛡️ CTO",
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

    def set_layout(self: "TmuxManager", layout: str = "tiled") -> None:
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
