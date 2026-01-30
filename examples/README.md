# MAO Examples

エージェント実行のサンプルスクリプト集

## セットアップ

### 1. API キーの設定

```bash
export ANTHROPIC_API_KEY=your-api-key-here
```

### 2. 依存関係のインストール

```bash
cd /path/to/mao
pip install -e .
```

## サンプル

### 基本的なエージェント実行

通常の実行（応答を一度に取得）：

```bash
python examples/test_agent.py
```

### ストリーミング実行

リアルタイムでストリーミング受信：

```bash
python examples/test_agent_streaming.py
```

## 実行例

```bash
$ python examples/test_agent.py

============================================================
MAO エージェント実行テスト
============================================================

プロンプト:
------------------------------------------------------------
あなたはPythonのエキスパートです。

以下のタスクを実行してください：
...
------------------------------------------------------------

エージェント実行中...

============================================================
実行成功！
============================================================

応答:
------------------------------------------------------------
FastAPIを使ったREST API設計の提案...
（エージェントの応答がここに表示されます）
------------------------------------------------------------

使用トークン: 234 入力, 1567 出力
モデル: claude-sonnet-4-20250514
停止理由: end_turn

ログファイル: test_logs/test-agent-001.log
============================================================
```

## ログ確認

エージェントの実行ログは `test_logs/` ディレクトリに保存されます：

```bash
ls test_logs/
# test-agent-001.log
# test-streaming-001.log

# ログ内容を確認
cat test_logs/test-agent-001.log
```

## カスタマイズ

### プロンプトの変更

スクリプト内の `prompt` 変数を編集してください。

### モデルの変更

```python
# Opusを使用
result = await executor.execute_agent(
    prompt=prompt,
    model="claude-opus-4-20250514",  # ← ここを変更
    logger=logger,
)

# Haikuを使用（高速・低コスト）
result = await executor.execute_agent(
    prompt=prompt,
    model="claude-haiku-4-20250514",  # ← ここを変更
    logger=logger,
)
```

### トークン数の調整

```python
result = await executor.execute_agent(
    prompt=prompt,
    model="claude-sonnet-4-20250514",
    max_tokens=4096,  # ← デフォルトは4096、最大8192
    logger=logger,
)
```

## トラブルシューティング

### API キーエラー

```
エラー: ANTHROPIC_API_KEY environment variable must be set
```

→ 環境変数を設定してください：

```bash
export ANTHROPIC_API_KEY=your-api-key-here
```

### インポートエラー

```
ModuleNotFoundError: No module named 'mao'
```

→ パッケージをインストールしてください：

```bash
pip install -e .
```

## 次のステップ

- [MAO Documentation](../README.md)
- [Agent Roles](../mao/roles/)
- [Dashboard Guide](../mao/ui/)
