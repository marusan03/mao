#!/usr/bin/env python3
"""
Simple agent execution test
"""
import asyncio
import os
from pathlib import Path

from mao.orchestrator.agent_executor import AgentExecutor
from mao.orchestrator.agent_logger import AgentLogger


async def main():
    """テスト実行"""
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
        agent_id="test-agent-001",
        agent_name="TestAgent",
        log_dir=log_dir,
    )

    print("=" * 60)
    print("MAO エージェント実行テスト")
    print("=" * 60)
    print()

    # シンプルなプロンプト
    prompt = """
あなたはPythonのエキスパートです。

以下のタスクを実行してください：

タスク: FastAPIを使った簡単なREST APIの設計を提案してください。

要件：
- ユーザー管理機能（CRUD）
- 認証機能
- セキュアな実装

提案内容には以下を含めてください：
1. エンドポイント設計
2. データモデル
3. セキュリティ考慮事項
4. 実装のベストプラクティス

簡潔に、コードサンプルを含めて説明してください。
"""

    print("プロンプト:")
    print("-" * 60)
    print(prompt.strip())
    print("-" * 60)
    print()
    print("エージェント実行中...")
    print()

    # エージェント実行（ストリーミングなし）
    result = await executor.execute_agent(
        prompt=prompt,
        model="claude-sonnet-4-20250514",
        logger=logger,
        max_tokens=2000,
    )

    if result["success"]:
        print("=" * 60)
        print("実行成功！")
        print("=" * 60)
        print()
        print("応答:")
        print("-" * 60)
        print(result["response"])
        print("-" * 60)
        print()
        print(f"使用トークン: {result['usage']['input_tokens']} 入力, {result['usage']['output_tokens']} 出力")
        print(f"モデル: {result['model']}")
        print(f"停止理由: {result['stop_reason']}")
        print()
        print(f"ログファイル: {logger.log_file}")
    else:
        print("=" * 60)
        print("実行失敗")
        print("=" * 60)
        print(f"エラー: {result['error']}")

    print()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
