"""
Agent execution engine using multiple Claude Code instances
"""
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import json
import time

from mao.orchestrator.agent_logger import AgentLogger


class ClaudeCodeExecutor:
    """エージェント実行エンジン（Claude Code CLI使用）"""

    def __init__(self):
        """Claude Code CLIを使用するエージェント実行エンジン"""
        # claude-code コマンドが利用可能かチェック
        self.claude_code_path = shutil.which("claude-code") or shutil.which("claude")

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
    ) -> Dict[str, Any]:
        """
        エージェントを実行（Claude Code CLI経由）

        Args:
            prompt: エージェントへのプロンプト
            model: 使用するClaude モデル（短縮名: opus, sonnet, haiku）
            logger: エージェント専用ロガー
            max_tokens: 最大トークン数（未使用、互換性のため）
            temperature: 温度パラメータ（未使用、互換性のため）
            system: システムプロンプト（プロンプトに統合）
            work_dir: 作業ディレクトリ（Noneの場合は一時ディレクトリ）

        Returns:
            実行結果
        """
        if logger:
            logger.info("エージェント実行を開始（Claude Code CLI経由）")

        # モデル名を短縮名に変換
        model_short = self._convert_model_name(model)

        # 作業ディレクトリを作成
        if work_dir is None:
            work_dir = Path(tempfile.mkdtemp(prefix="mao_agent_"))
            cleanup_work_dir = True
        else:
            work_dir.mkdir(parents=True, exist_ok=True)
            cleanup_work_dir = False

        try:
            # システムプロンプトとユーザープロンプトを統合
            full_prompt = prompt
            if system:
                full_prompt = f"{system}\n\n{prompt}"

            # プロンプトをファイルに保存
            prompt_file = work_dir / "prompt.txt"
            prompt_file.write_text(full_prompt)

            # 出力ファイル
            output_file = work_dir / "output.txt"
            error_file = work_dir / "error.txt"

            if logger:
                logger.info(f"作業ディレクトリ: {work_dir}")
                logger.info(f"モデル: {model_short}")

            # Claude Code CLIを実行
            # --cwd で作業ディレクトリを指定
            # プロンプトを標準入力から渡す
            process = await asyncio.create_subprocess_exec(
                self.claude_code_path,
                "--model", model_short,
                "--cwd", str(work_dir),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # プロンプトを送信
            stdout, stderr = await process.communicate(input=full_prompt.encode())

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                if logger:
                    logger.error(f"Claude Code CLI実行エラー: {error_msg}")

                return {
                    "success": False,
                    "error": error_msg,
                    "model": model,
                }

            # 出力を取得
            response_text = stdout.decode().strip()

            if logger:
                logger.result(f"応答を受信（{len(response_text)}文字）")
                logger.info(f"作業ディレクトリ: {work_dir}")

            # 使用量は推定（Claude Code CLIからは取得できない）
            estimated_input_tokens = len(full_prompt) // 4  # 概算
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

        except Exception as e:
            if logger:
                logger.error(f"例外が発生: {str(e)}")

            return {
                "success": False,
                "error": str(e),
                "model": model,
            }
        finally:
            # 一時ディレクトリの場合はクリーンアップ
            if cleanup_work_dir:
                try:
                    shutil.rmtree(work_dir)
                except Exception:
                    pass

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

    def _convert_model_name(self, model: str) -> str:
        """モデル名を短縮名に変換

        Args:
            model: フルモデル名

        Returns:
            短縮名（opus, sonnet, haiku）
        """
        model_lower = model.lower()
        if "opus" in model_lower:
            return "opus"
        elif "sonnet" in model_lower:
            return "sonnet"
        elif "haiku" in model_lower:
            return "haiku"
        else:
            # デフォルトはsonnet
            return "sonnet"

    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """コストを計算（概算）

        Args:
            model: モデル名
            usage: トークン使用量

        Returns:
            コスト（USD）
        """
        # 価格表（$per 1M tokens）
        pricing = {
            "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
            "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
            "claude-haiku-4-20250514": {"input": 0.25, "output": 1.25},
        }

        price = pricing.get(model, {"input": 3.0, "output": 15.0})

        input_cost = usage.get("input_tokens", 0) / 1_000_000 * price["input"]
        output_cost = usage.get("output_tokens", 0) / 1_000_000 * price["output"]

        return input_cost + output_cost


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
