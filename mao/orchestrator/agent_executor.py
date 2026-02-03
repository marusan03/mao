"""
Agent execution engine using Claude API
"""
from typing import Optional, Dict, Any, List
import os

from anthropic import AsyncAnthropic

from mao.orchestrator.agent_logger import AgentLogger
from mao.orchestrator.utils.model_utils import calculate_cost
from mao.orchestrator.agent_streaming import AgentStreamingMixin
from mao.orchestrator.agent_process import (
    AgentProcess,
    escape_applescript,
    send_mac_notification,
)

# Re-export for backward compatibility
__all__ = [
    "AgentExecutor",
    "AgentProcess",
    "escape_applescript",
    "send_mac_notification",
]


class AgentExecutor(AgentStreamingMixin):
    """エージェント実行エンジン（Claude API使用）"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Anthropic API key (環境変数 ANTHROPIC_API_KEY または明示的に指定)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        # API keyがある場合のみクライアントを作成
        if self.api_key:
            self.client = AsyncAnthropic(api_key=self.api_key)
        else:
            self.client = None

    def is_available(self) -> bool:
        """API keyが設定されているかチェック

        Returns:
            True if API key is available
        """
        return self.client is not None

    async def execute_agent(
        self,
        prompt: str,
        model: str = "claude-sonnet-4-20250514",
        logger: Optional[AgentLogger] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
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
            tools: ツール定義
            tool_choice: ツール選択設定

        Returns:
            実行結果
        """
        if not self.is_available():
            error_msg = (
                "ANTHROPIC_API_KEY is not set. "
                "Please set the environment variable or provide an API key."
            )
            if logger:
                logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "model": model,
            }

        if logger:
            logger.info("エージェント実行を開始")
            logger.api_request(model, max_tokens)

        try:
            # API呼び出しのパラメータを構築
            api_params = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system if system else "",
                "messages": [{"role": "user", "content": prompt}],
            }

            # toolsがある場合は追加
            if tools:
                api_params["tools"] = tools

            # tool_choiceがある場合は追加
            if tool_choice:
                api_params["tool_choice"] = tool_choice

            # API呼び出し
            message = await self.client.messages.create(**api_params)

            # 結果を抽出
            response_text = ""
            tool_uses = []

            for block in message.content:
                if block.type == "text":
                    response_text += block.text
                elif block.type == "tool_use":
                    tool_uses.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            # ログ記録
            if logger:
                logger.api_response(
                    tokens=message.usage.output_tokens,
                    cost=calculate_cost(model, message.usage),
                )
                logger.result(f"応答を受信しました（{message.usage.output_tokens} tokens）")

                if tool_uses:
                    for tool_use in tool_uses:
                        logger.action(tool_use["name"], f"Tool called: {tool_use['input']}")

            return {
                "success": True,
                "response": response_text,
                "tool_uses": tool_uses,
                "model": model,
                "usage": {
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                },
                "message_id": message.id,
                "stop_reason": message.stop_reason,
            }

        except ValueError as e:
            # バリデーションエラー（不正なパラメータなど）
            error_msg = f"Invalid parameter: {str(e)}"
            if logger:
                logger.error(error_msg)

            return {
                "success": False,
                "error": error_msg,
                "error_type": "validation",
                "response": None,
            }
        except ConnectionError as e:
            # ネットワーク接続エラー
            error_msg = f"Connection error: {str(e)}"
            if logger:
                logger.error(error_msg)

            return {
                "success": False,
                "error": error_msg,
                "error_type": "connection",
                "response": None,
            }
        except TimeoutError as e:
            # タイムアウト
            error_msg = f"Request timeout: {str(e)}"
            if logger:
                logger.error(error_msg)

            return {
                "success": False,
                "error": error_msg,
                "error_type": "timeout",
                "response": None,
            }
        except Exception as e:
            # その他のエラー（API エラーなど）
            error_msg = f"Agent execution error: {str(e)}"
            if logger:
                logger.error(f"{error_msg} (type: {type(e).__name__})")

            return {
                "success": False,
                "error": error_msg,
                "error_type": "api_error",
                "exception_class": type(e).__name__,
                "response": None,
            }
