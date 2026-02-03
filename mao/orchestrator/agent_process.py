"""
Agent Process - バックグラウンド実行管理
"""
import asyncio
import subprocess
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mao.orchestrator.agent_executor import AgentExecutor
    from mao.orchestrator.agent_logger import AgentLogger


def escape_applescript(text: str) -> str:
    """
    AppleScript用に文字列をエスケープ

    Args:
        text: エスケープする文字列

    Returns:
        エスケープされた文字列
    """
    # バックスラッシュを最初にエスケープ（二重エスケープを防ぐ）
    text = text.replace('\\', '\\\\')
    # ダブルクォートをエスケープ
    text = text.replace('"', '\\"')
    return text


def send_mac_notification(title: str, message: str, sound: bool = True):
    """
    macOS通知を送信（一時的なデバッグ用）

    Args:
        title: 通知タイトル
        message: 通知メッセージ
        sound: サウンドを鳴らすか
    """
    try:
        # AppleScriptインジェクション対策
        safe_title = escape_applescript(title)
        safe_message = escape_applescript(message)

        sound_option = 'sound name "Basso"' if sound else ""
        script = f'display notification "{safe_message}" with title "{safe_title}" {sound_option}'
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=5,
            check=False,  # エラーを無視
        )
    except subprocess.TimeoutExpired:
        # タイムアウトは無視（通知は重要な処理ではない）
        pass
    except FileNotFoundError:
        # osascriptがない環境（非macOS）では無視
        pass
    except Exception:
        # その他のエラーも無視（通知は重要な処理ではない）
        pass


class AgentProcess:
    """エージェントプロセス（バックグラウンド実行）"""

    def __init__(
        self,
        agent_id: str,
        role_name: str,
        prompt: str,
        model: str,
        logger: "AgentLogger",
        executor: "AgentExecutor",
    ):
        self.agent_id = agent_id
        self.role_name = role_name
        self.prompt = prompt
        self.model = model
        self.logger = logger
        self.executor = executor
        self.task: Optional[asyncio.Task] = None
        self.result: Optional[Dict[str, Any]] = None
        self.status = "pending"  # pending, running, completed, failed

    async def start(self):
        """エージェント実行を開始"""
        self.status = "running"
        self.logger.info(f"{self.role_name} エージェントを開始")

        try:
            self.result = await self.executor.execute_agent(
                prompt=self.prompt,
                model=self.model,
                logger=self.logger,
            )

            if self.result["success"]:
                self.status = "completed"
                self.logger.result("エージェント実行完了")
            else:
                self.status = "failed"
                self.logger.error(f"エージェント実行失敗: {self.result.get('error')}")

        except Exception as e:
            self.status = "failed"
            error_msg = f"Unexpected error in agent process: {str(e)}"
            self.logger.error(f"{error_msg} (type: {type(e).__name__})")
            self.result = {
                "success": False,
                "error": error_msg,
                "error_type": "process_error",
                "exception_class": type(e).__name__,
            }

        return self.result

    def start_background(self):
        """バックグラウンドで実行開始"""
        self.task = asyncio.create_task(self.start())
        return self.task

    async def wait(self) -> Dict[str, Any]:
        """実行完了を待機"""
        if self.task:
            await self.task
        return self.result or {"success": False, "error": "Not started"}

    def is_running(self) -> bool:
        """実行中かどうか"""
        return self.status == "running"

    def is_completed(self) -> bool:
        """完了したかどうか"""
        return self.status in ("completed", "failed")
