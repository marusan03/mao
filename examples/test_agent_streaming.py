#!/usr/bin/env python3
"""
Streaming agent execution test
"""
import asyncio
import os
from pathlib import Path

from mao.orchestrator.agent_executor import AgentExecutor
from mao.orchestrator.agent_logger import AgentLogger


async def main():
    """ストリーミングテスト"""
    # API key チェック
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("エラー: ANTHROPIC_API_KEY 環境変数を設定してください")
        print("例: export ANTHROPIC_API_KEY=your-api-key-here")
        return

    # ログディレクトリ
    log_dir = Path(".") / "test_logs"
    log_dir.mkdir(exist_ok=True)

    # エージェント実行エンジン
    executor = AgentExecutor()

    # ロガー
    logger = AgentLogger(
        agent_id="test-streaming-001",
        agent_name="StreamingAgent",
        log_dir=log_dir,
    )

    print("=" * 60)
    print("MAO エージェント実行テスト（ストリーミング）")
    print("=" * 60)
    print()

    prompt = """
Pythonで簡単なTODOリストアプリを作成する手順を教えてください。

以下を含めてください：
1. 必要なライブラリ
2. データ構造の設計
3. 基本的な機能（追加、削除、表示）
4. サンプルコード

段階的に説明してください。
"""

    print("プロンプト:")
    print("-" * 60)
    print(prompt.strip())
    print("-" * 60)
    print()
    print("応答（リアルタイム）:")
    print("-" * 60)

    # ストリーミング実行
    full_response = ""
    async for event in executor.execute_agent_streaming(
        prompt=prompt,
        model="claude-sonnet-4-20250514",
        logger=logger,
        max_tokens=2000,
    ):
        if event["type"] == "start":
            print(f"[開始] メッセージID: {event['message_id']}")

        elif event["type"] == "content":
            # リアルタイムで出力
            print(event["content"], end="", flush=True)
            full_response = event["accumulated"]

        elif event["type"] == "complete":
            print()
            print("-" * 60)
            print()
            print(f"使用トークン: {event['usage']['input_tokens']} 入力, {event['usage']['output_tokens']} 出力")
            print(f"停止理由: {event['stop_reason']}")
            print()
            print(f"ログファイル: {logger.log_file}")

        elif event["type"] == "error":
            print()
            print("-" * 60)
            print(f"エラー: {event['error']}")
            return

    print()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
