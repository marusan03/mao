"""
Agent execution engine using Claude API
"""
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, AsyncIterator, List, Callable
import os
import subprocess

from anthropic import Anthropic, AsyncAnthropic
from anthropic.types import Message, MessageStreamEvent

from mao.orchestrator.agent_logger import AgentLogger
from mao.orchestrator.utils.model_utils import calculate_cost


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


class AgentExecutor:
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
