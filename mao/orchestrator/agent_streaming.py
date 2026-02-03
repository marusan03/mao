"""
Agent Streaming Mixin - ストリーミング実行とツール使用
"""
from typing import Optional, Dict, Any, AsyncIterator, List, TYPE_CHECKING

if TYPE_CHECKING:
    from mao.orchestrator.agent_executor import AgentExecutor

from mao.orchestrator.agent_logger import AgentLogger
from mao.orchestrator.utils.model_utils import calculate_cost


class AgentStreamingMixin:
    """ストリーミング実行とツール使用を担当するミックスイン"""

    async def execute_agent_streaming(
        self: "AgentExecutor",
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
        if not self.is_available():
            error_msg = (
                "ANTHROPIC_API_KEY is not set. "
                "Please set the environment variable or provide an API key."
            )
            if logger:
                logger.error(error_msg)
            yield {"type": "error", "error": error_msg}
            return

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
                        cost=calculate_cost(model, message.usage),
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

        except ValueError as e:
            error_msg = f"Invalid parameter: {str(e)}"
            if logger:
                logger.error(error_msg)

            yield {
                "type": "error",
                "error": error_msg,
                "error_type": "validation",
            }
        except ConnectionError as e:
            error_msg = f"Connection error: {str(e)}"
            if logger:
                logger.error(error_msg)

            yield {
                "type": "error",
                "error": error_msg,
                "error_type": "connection",
            }
        except TimeoutError as e:
            error_msg = f"Request timeout: {str(e)}"
            if logger:
                logger.error(error_msg)

            yield {
                "type": "error",
                "error": error_msg,
                "error_type": "timeout",
            }
        except Exception as e:
            error_msg = f"Streaming execution error: {str(e)}"
            if logger:
                logger.error(f"{error_msg} (type: {type(e).__name__})")

            yield {
                "type": "error",
                "error": error_msg,
                "error_type": "api_error",
                "exception_class": type(e).__name__,
            }

    async def execute_with_tools(
        self: "AgentExecutor",
        prompt: str,
        tools: List[Dict[str, Any]],
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

        except ValueError as e:
            error_msg = f"Invalid tool parameter: {str(e)}"
            if logger:
                logger.error(error_msg)

            return {
                "success": False,
                "error": error_msg,
                "error_type": "validation",
            }
        except ConnectionError as e:
            error_msg = f"Connection error during tool use: {str(e)}"
            if logger:
                logger.error(error_msg)

            return {
                "success": False,
                "error": error_msg,
                "error_type": "connection",
            }
        except Exception as e:
            error_msg = f"Tool execution error: {str(e)}"
            if logger:
                logger.error(f"{error_msg} (type: {type(e).__name__})")

            return {
                "success": False,
                "error": error_msg,
                "error_type": "tool_error",
                "exception_class": type(e).__name__,
            }
