"""
Agent execution engine using Claude API
"""
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, AsyncIterator
import os

from anthropic import Anthropic, AsyncAnthropic
from anthropic.types import Message, MessageStreamEvent

from mao.orchestrator.agent_logger import AgentLogger


class AgentExecutor:
    """エージェント実行エンジン（Claude API使用）"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Anthropic API key (環境変数 ANTHROPIC_API_KEY がなければ必須)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable must be set or api_key must be provided"
            )

        # 非同期クライアント
        self.client = AsyncAnthropic(api_key=self.api_key)

    async def execute_agent(
        self,
        prompt: str,
        model: str = "claude-sonnet-4-20250514",
        logger: Optional[AgentLogger] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        エージェントを実行（ストリーミングなし）

        Args:
            prompt: エージェントへのプロンプト
            model: 使用するClaude モデル
            logger: エージェント専用ロガー
            max_tokens: 最大トークン数
            temperature: 温度パラメータ
            system: システムプロンプト

        Returns:
            実行結果
        """
        if logger:
            logger.info("エージェント実行を開始")
            logger.api_request(model, max_tokens)

        try:
            # API呼び出し
            message = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else "",
                messages=[{"role": "user", "content": prompt}],
            )

            # 結果を抽出
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text

            # ログ記録
            if logger:
                logger.api_response(
                    tokens=message.usage.output_tokens,
                    cost=self._calculate_cost(model, message.usage),
                )
                logger.result(f"応答を受信しました（{message.usage.output_tokens} tokens）")

            return {
                "success": True,
                "response": response_text,
                "model": model,
                "usage": {
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                },
                "message_id": message.id,
                "stop_reason": message.stop_reason,
            }

        except Exception as e:
            if logger:
                logger.error(f"エージェント実行エラー: {str(e)}")

            return {
                "success": False,
                "error": str(e),
                "response": None,
            }

    async def execute_agent_streaming(
        self,
        prompt: str,
        model: str = "claude-sonnet-4-20250514",
        logger: Optional[AgentLogger] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        system: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        エージェントを実行（ストリーミング）

        Args:
            prompt: エージェントへのプロンプト
            model: 使用するClaude モデル
            logger: エージェント専用ロガー
            max_tokens: 最大トークン数
            temperature: 温度パラメータ
            system: システムプロンプト

        Yields:
            ストリーミングイベント
        """
        if logger:
            logger.info("エージェント実行を開始（ストリーミング）")
            logger.api_request(model, max_tokens)

        try:
            # ストリーミングAPI呼び出し
            async with self.client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else "",
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                response_text = ""

                async for event in stream:
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            chunk = event.delta.text
                            response_text += chunk

                            yield {
                                "type": "content",
                                "content": chunk,
                                "accumulated": response_text,
                            }

                    elif event.type == "message_start":
                        yield {
                            "type": "start",
                            "message_id": event.message.id,
                        }

                    elif event.type == "message_delta":
                        yield {
                            "type": "delta",
                            "stop_reason": event.delta.stop_reason,
                        }

                # 完了メッセージ
                message = await stream.get_final_message()

                if logger:
                    logger.api_response(
                        tokens=message.usage.output_tokens,
                        cost=self._calculate_cost(model, message.usage),
                    )
                    logger.result(f"応答完了（{message.usage.output_tokens} tokens）")

                yield {
                    "type": "complete",
                    "response": response_text,
                    "usage": {
                        "input_tokens": message.usage.input_tokens,
                        "output_tokens": message.usage.output_tokens,
                    },
                    "message_id": message.id,
                    "stop_reason": message.stop_reason,
                }

        except Exception as e:
            if logger:
                logger.error(f"ストリーミング実行エラー: {str(e)}")

            yield {
                "type": "error",
                "error": str(e),
            }

    def _calculate_cost(self, model: str, usage: Any) -> float:
        """
        概算コストを計算（2026年1月時点の価格）

        Args:
            model: モデル名
            usage: Usage オブジェクト

        Returns:
            概算コスト（USD）
        """
        # モデルごとの価格（per million tokens）
        pricing = {
            "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
            "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
            "claude-haiku-4-20250514": {"input": 0.25, "output": 1.25},
        }

        # デフォルト価格（Sonnet）
        price = pricing.get(
            model, {"input": 3.0, "output": 15.0}
        )

        input_cost = (usage.input_tokens / 1_000_000) * price["input"]
        output_cost = (usage.output_tokens / 1_000_000) * price["output"]

        return input_cost + output_cost

    async def execute_with_tools(
        self,
        prompt: str,
        tools: list,
        model: str = "claude-sonnet-4-20250514",
        logger: Optional[AgentLogger] = None,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        ツール使用を含むエージェント実行

        Args:
            prompt: エージェントへのプロンプト
            tools: 使用可能なツール定義
            model: 使用するモデル
            logger: ロガー
            max_tokens: 最大トークン数

        Returns:
            実行結果
        """
        if logger:
            logger.info("エージェント実行を開始（ツール使用）")
            logger.api_request(model, max_tokens)

        messages = [{"role": "user", "content": prompt}]

        try:
            # 最大10ターンまで（無限ループ防止）
            for turn in range(10):
                if logger:
                    logger.thinking(f"ターン {turn + 1}")

                # API呼び出し
                message = await self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    tools=tools,
                    messages=messages,
                )

                # ツール使用があるか確認
                tool_uses = [
                    block for block in message.content if block.type == "tool_use"
                ]

                if not tool_uses:
                    # ツール使用なし、完了
                    response_text = ""
                    for block in message.content:
                        if block.type == "text":
                            response_text += block.text

                    if logger:
                        logger.result("エージェント実行完了")

                    return {
                        "success": True,
                        "response": response_text,
                        "turns": turn + 1,
                        "usage": {
                            "input_tokens": message.usage.input_tokens,
                            "output_tokens": message.usage.output_tokens,
                        },
                    }

                # ツール実行
                if logger:
                    for tool_use in tool_uses:
                        logger.action(tool_use.name, str(tool_use.input))

                # アシスタントメッセージを追加
                messages.append({"role": "assistant", "content": message.content})

                # ツール結果を追加（実際のツール実行は省略、ダミー結果）
                tool_results = []
                for tool_use in tool_uses:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": "Tool execution placeholder",
                    })

                messages.append({"role": "user", "content": tool_results})

            # 最大ターン到達
            if logger:
                logger.warning("最大ターン数に到達しました")

            return {
                "success": False,
                "error": "最大ターン数（10）に到達しました",
                "turns": 10,
            }

        except Exception as e:
            if logger:
                logger.error(f"ツール使用エラー: {str(e)}")

            return {
                "success": False,
                "error": str(e),
            }


class AgentProcess:
    """エージェントプロセス（バックグラウンド実行）"""

    def __init__(
        self,
        agent_id: str,
        role_name: str,
        prompt: str,
        model: str,
        logger: AgentLogger,
        executor: AgentExecutor,
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
            self.logger.error(f"予期しないエラー: {str(e)}")
            self.result = {"success": False, "error": str(e)}

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
