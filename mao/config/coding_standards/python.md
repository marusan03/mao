# Python コーディング規約

## 基本方針

- PEP 8 に従う
- 型ヒントを積極的に使用する
- docstring は Google スタイル
- Black でフォーマット（行長88文字）

## スタイルガイド

### インポート

```python
# 標準ライブラリ
import os
from pathlib import Path

# サードパーティ
import anthropic
from textual.app import App

# ローカル
from mao.orchestrator import AgentExecutor
```

### 型ヒント

```python
from typing import Optional, Dict, Any

def execute_agent(
    prompt: str,
    model: str = "claude-sonnet-4-20250514",
    logger: Optional[AgentLogger] = None,
) -> Dict[str, Any]:
    """エージェントを実行する

    Args:
        prompt: プロンプト
        model: モデル名
        logger: ロガー

    Returns:
        実行結果の辞書
    """
    pass
```

### エラーハンドリング

```python
# 具体的な例外を使用
try:
    result = await executor.execute_agent(prompt)
except anthropic.APIError as e:
    logger.error(f"API error: {e}")
    raise
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    return {"success": False, "error": str(e)}
```

### 非同期処理

```python
# async/await を活用
async def process_agents():
    tasks = [
        agent1.execute(),
        agent2.execute(),
        agent3.execute(),
    ]
    results = await asyncio.gather(*tasks)
    return results
```

## テスト

### pytest の使用

```python
import pytest
from mao.orchestrator import AgentExecutor

@pytest.fixture
def executor():
    return AgentExecutor()

async def test_execute_agent(executor):
    result = await executor.execute_agent("test prompt")
    assert result["success"] is True
    assert "response" in result
```

### カバレッジ目標

- 新規コード: 80%以上
- クリティカルパス: 100%

## ドキュメント

### モジュール docstring

```python
"""
Agent executor for MAO.

このモジュールはエージェント実行エンジンを提供します。
Claude API を使用して非同期でエージェントを実行できます。
"""
```

### クラス docstring

```python
class AgentExecutor:
    """エージェント実行エンジン

    Claude API を使用してエージェントを実行します。
    ストリーミングと非ストリーミングの両方をサポートします。

    Attributes:
        client: Anthropic クライアント
        default_model: デフォルトモデル名
    """
```

## ベストプラクティス

### ロギング

```python
import structlog

logger = structlog.get_logger()

# 構造化ログ
logger.info("agent_started", agent_id=agent_id, model=model)
logger.error("agent_failed", agent_id=agent_id, error=str(e))
```

### パス操作

```python
from pathlib import Path

# Path オブジェクトを使用
log_dir = Path.home() / ".mao" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

log_file = log_dir / f"{agent_id}.log"
```

### 設定管理

```python
from pydantic import BaseModel

class AgentConfig(BaseModel):
    """エージェント設定"""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 1.0

    class Config:
        frozen = True  # イミュータブル
```
