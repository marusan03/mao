"""
Agent execution engine using multiple Claude Code instances
"""
import asyncio
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import json
import time

from mao.orchestrator.agent_logger import AgentLogger
from mao.orchestrator.utils.model_utils import calculate_cost, convert_model_name


class ClaudeCodeExecutor:
    """エージェント実行エンジン（Claude Code CLI使用）"""

    def __init__(self, allow_unsafe_operations: bool = False):
        """Claude Code CLIを使用するエージェント実行エンジン

        Args:
            allow_unsafe_operations: --dangerously-skip-permissions を使用するか
                                     (デフォルト: False - 安全モード)
        """
        # claude-code コマンドが利用可能かチェック
        self.claude_code_path = shutil.which("claude-code") or shutil.which("claude")
        self.allow_unsafe_operations = allow_unsafe_operations

        if not self.claude_code_path:
            raise ValueError(
                "claude-code command not found. "
                "Please install Claude Code: https://claude.ai/download"
            )

    def is_available(self) -> bool:
        """Claude Code CLIが利用可能かチェック

        Returns:
            True if Claude Code CLI is available
        """
        return self.claude_code_path is not None

    async def execute_agent(
        self,
        prompt: str,
        model: str = "claude-sonnet-4-20250514",
        logger: Optional[AgentLogger] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        system: Optional[str] = None,
        work_dir: Optional[Path] = None,
        log_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        エージェントを実行（Claude Code CLI経由）

        Args:
            prompt: エージェントへのプロンプト
            model: 使用するClaude モデル（短縮名: opus, sonnet, haiku）
            logger: エージェント専用ロガー
            max_tokens: 最大トークン数（未使用、互換性のため）
            temperature: 温度パラメータ（未使用、互換性のため）
            system: システムプロンプト（--append-system-promptで指定）
            work_dir: 作業ディレクトリ（Noneの場合は一時ディレクトリ）
            log_callback: リアルタイムログ出力を受け取るコールバック関数

        Returns:
            実行結果
        """
        if logger:
            logger.info("エージェント実行を開始（Claude Code CLI経由）")

        # プロンプトの検証
        if not prompt or not prompt.strip():
            error_msg = "プロンプトが空です"
            if logger:
                logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "model": model,
            }

        # モデル名を短縮名に変換
        model_short = convert_model_name(model)

        # 作業ディレクトリを作成
        if work_dir is None:
            work_dir = Path(tempfile.mkdtemp(prefix="mao_agent_"))
            cleanup_work_dir = True
        else:
            work_dir.mkdir(parents=True, exist_ok=True)
            cleanup_work_dir = False

        try:
            if logger:
                logger.info(f"作業ディレクトリ: {work_dir}")
                logger.info(f"モデル: {model_short}")

            # Claude CLIを実行
            # --print: 非対話的出力
            # --model: モデル指定
            # プロンプトはstdinから渡す
            cmd = [
                self.claude_code_path,
                "--print",
                "--model", model_short,
            ]

            # セキュリティ設定に基づいてパーミッションスキップ
            if self.allow_unsafe_operations:
                cmd.append("--dangerously-skip-permissions")
                if logger:
                    logger.warning("Running in unsafe mode: --dangerously-skip-permissions enabled")

            # 作業ディレクトリを追加
            if work_dir:
                cmd.extend(["--add-dir", str(work_dir)])

            # システムプロンプトがある場合
            if system:
                cmd.extend(["--append-system-prompt", system])

            if logger:
                # デバッグ用：完全なコマンドをログ出力
                cmd_str = ' '.join(f'"{c}"' if ' ' in str(c) else str(c) for c in cmd)
                logger.info(f"実行コマンド: {cmd_str}")
                logger.info(f"プロンプト（stdin経由）: {prompt[:50]}...")

            # プロンプトをstdin経由で渡す
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir),
            )

            # stdinにプロンプトを書き込む
            if process.stdin:
                process.stdin.write(prompt.encode())
                await process.stdin.drain()
                process.stdin.close()

            # リアルタイムでstdout/stderrを読み取る
            stdout_lines = []
            stderr_lines = []

            async def read_stream(stream, lines_list, prefix):
                """ストリームを読み取ってコールバックを呼ぶ"""
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    line_text = line.decode().rstrip()
                    lines_list.append(line_text)

                    # コールバックがあれば呼ぶ
                    if log_callback:
                        log_callback(f"{prefix}{line_text}")

                    # ロガーにも出力
                    if logger and line_text:
                        logger.info(f"{prefix}{line_text}")

            # stdout と stderr を並行して読み取る
            await asyncio.gather(
                read_stream(process.stdout, stdout_lines, ""),
                read_stream(process.stderr, stderr_lines, "[stderr] "),
            )

            # プロセスの終了を待つ
            await process.wait()

            if process.returncode != 0:
                error_msg = "\n".join(stderr_lines) if stderr_lines else "Unknown error"
                if logger:
                    logger.error(f"Claude Code CLI実行エラー: {error_msg}")

                return {
                    "success": False,
                    "error": error_msg,
                    "model": model,
                }

            # 出力を取得
            response_text = "\n".join(stdout_lines).strip()

            if logger:
                logger.result(f"応答を受信（{len(response_text)}文字）")
                logger.info(f"作業ディレクトリは保持: {work_dir}")

            # 使用量は推定（Claude Code CLIからは取得できない）
            estimated_input_tokens = len(prompt) // 4  # 概算
            estimated_output_tokens = len(response_text) // 4  # 概算

            return {
                "success": True,
                "response": response_text,
                "model": model,
                "work_dir": str(work_dir),
                "usage": {
                    "input_tokens": estimated_input_tokens,
                    "output_tokens": estimated_output_tokens,
                },
                "stop_reason": "end_turn",
            }

        except asyncio.TimeoutError:
            error_msg = "Claude Code CLI execution timeout"
            if logger:
                logger.error(error_msg)

            return {
                "success": False,
                "error": error_msg,
                "error_type": "timeout",
                "model": model,
            }
        except PermissionError as e:
            error_msg = f"Permission denied: {str(e)}"
            if logger:
                logger.error(error_msg)

            return {
                "success": False,
                "error": error_msg,
                "error_type": "permission",
                "model": model,
            }
        except FileNotFoundError as e:
            error_msg = f"File not found: {str(e)}"
            if logger:
                logger.error(error_msg)

            return {
                "success": False,
                "error": error_msg,
                "error_type": "file_not_found",
                "model": model,
            }
        except subprocess.SubprocessError as e:
            error_msg = f"Subprocess error: {str(e)}"
            if logger:
                logger.error(error_msg)

            return {
                "success": False,
                "error": error_msg,
                "error_type": "subprocess",
                "model": model,
            }
        except Exception as e:
            # その他の予期しないエラー
            error_msg = f"Unexpected error: {str(e)}"
            if logger:
                logger.error(f"{error_msg} (type: {type(e).__name__})")

            return {
                "success": False,
                "error": error_msg,
                "error_type": "unexpected",
                "exception_class": type(e).__name__,
                "model": model,
            }
        finally:
            # 一時ディレクトリの場合のみクリーンアップ
            # work_dirが指定されている場合は保持
            if cleanup_work_dir:
                try:
                    shutil.rmtree(work_dir)
                except OSError as e:
                    # クリーンアップ失敗は警告のみ（致命的ではない）
                    if logger:
                        logger.warning(f"Failed to cleanup temporary directory {work_dir}: {e}")
                except Exception as e:
                    # 予期しないエラーも記録
                    if logger:
                        logger.warning(f"Unexpected error during cleanup: {e}")

    async def execute_agent_streaming(
        self,
        prompt: str,
        model: str = "claude-sonnet-4-20250514",
        logger: Optional[AgentLogger] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        system: Optional[str] = None,
        work_dir: Optional[Path] = None,
    ):
        """
        エージェントを実行（ストリーミング）

        Note: Claude Code CLIはストリーミングをサポートしていないため、
        非ストリーミング版を呼び出してから結果を返す

        Yields:
            イベント辞書
        """
        if logger:
            logger.info("エージェント実行を開始（ストリーミングモード）")

        # 非ストリーミングで実行
        result = await self.execute_agent(
            prompt=prompt,
            model=model,
            logger=logger,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            work_dir=work_dir,
        )

        if result["success"]:
            # 開始イベント
            yield {"type": "message_start"}

            # コンテンツイベント
            yield {"type": "content", "content": result["response"]}

            # 終了イベント
            yield {
                "type": "message_stop",
                "usage": result.get("usage", {}),
                "stop_reason": result.get("stop_reason", "end_turn"),
            }
        else:
            # エラーイベント
            yield {"type": "error", "error": result.get("error", "Unknown error")}



class AgentProcess:
    """エージェントプロセス（バックグラウンド実行）"""

    def __init__(
        self,
        agent_id: str,
        role_name: str,
        prompt: str,
        model: str,
        logger: AgentLogger,
        executor: ClaudeCodeExecutor,
        work_dir: Optional[Path] = None,
    ):
        self.agent_id = agent_id
        self.role_name = role_name
        self.prompt = prompt
        self.model = model
        self.logger = logger
        self.executor = executor
        self.work_dir = work_dir
        self._task = None
        self._result = None

    async def start(self) -> Dict[str, Any]:
        """エージェントを開始"""
        self.logger.info(f"エージェント {self.agent_id} を起動")

        # 実行
        self._result = await self.executor.execute_agent(
            prompt=self.prompt,
            model=self.model,
            logger=self.logger,
            work_dir=self.work_dir,
        )

        return self._result

    def is_running(self) -> bool:
        """実行中かどうか"""
        if self._task is None:
            return False
        return not self._task.done()

    def get_result(self) -> Optional[Dict[str, Any]]:
        """実行結果を取得"""
        return self._result
