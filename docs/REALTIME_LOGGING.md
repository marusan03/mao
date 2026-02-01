# リアルタイムログ機能

**バージョン:** 1.0
**最終更新:** 2026-01-30

---

## 概要

マネージャーとワーカーの実行ログをリアルタイムで表示する機能を実装しました。

Claude Code CLIの標準出力・標準エラー出力を非同期で読み取り、ダッシュボードのログビューアに即座に表示します。

---

## 主要機能

### 1. リアルタイムストリーム読み取り

**実装:** `mao/orchestrator/claude_code_executor.py`

```python
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
```

### 2. ログコールバック機能

**execute_agent()** にログコールバックパラメータを追加:

```python
async def execute_agent(
    self,
    prompt: str,
    model: str = "claude-sonnet-4-20250514",
    logger: Optional[AgentLogger] = None,
    log_callback: Optional[callable] = None,  # ← 新規追加
    ...
) -> Dict[str, Any]:
```

### 3. ダッシュボード統合

**実装:** `mao/ui/dashboard_interactive.py`

```python
def on_log(log_line: str):
    """マネージャーの実行ログを受け取る"""
    if self.log_viewer_widget and log_line.strip():
        # [stderr] プレフィックスがある場合はERRORレベル
        if log_line.startswith("[stderr]"):
            self.log_viewer_widget.add_log(
                log_line.replace("[stderr] ", ""),
                level="ERROR",
                agent_id="manager",
            )
        else:
            # 通常のログはINFOレベル
            self.log_viewer_widget.add_log(
                log_line,
                level="INFO",
                agent_id="manager",
            )

result = await self.manager_executor.execute_agent(
    prompt=prompt,
    model=self.initial_model,
    log_callback=on_log,  # ← コールバック設定
)
```

### 4. 自動スクロール

**実装:** `mao/ui/widgets/log_viewer_simple.py`

```python
def refresh_display(self):
    """表示を更新"""
    # ... ログを表示 ...
    self.update(content)

    # 自動スクロールが有効なら最下部にスクロール
    if self.auto_scroll:
        self.scroll_end(animate=False)
```

---

## ログレベル

### 標準ログレベル

| レベル | カラー | 用途 |
|--------|--------|------|
| **INFO** | シアン | 一般的な情報メッセージ |
| **DEBUG** | グレー（dim） | デバッグ情報 |
| **WARN** | 黄色 | 警告メッセージ |
| **ERROR** | 赤 | エラーメッセージ |

### 拡張ログレベル

| レベル | カラー | 用途 |
|--------|--------|------|
| **TOOL** | マゼンタ | ツール使用（Read, Write, Bashなど） |
| **THINKING** | 青 | Claude の思考プロセス |
| **ACTION** | 緑 | アクション実行 |
| **RESULT** | 明るい緑 | 実行結果 |

---

## ログフォーマット

### 標準フォーマット

```
HH:MM:SS | LEVEL | [agent_id] message
```

### 例

```
18:30:45 | INFO  | [manager] エージェント実行を開始（Claude Code CLI経由）
18:30:46 | INFO  | [manager] 作業ディレクトリ: /tmp/mao_agent_xyz
18:30:46 | INFO  | [manager] モデル: sonnet
18:30:47 | INFO  | [manager] 実行コマンド: "claude-code" --print --model sonnet ...
18:30:50 | INFO  | [manager] タスクを3つのサブタスクに分解します
18:30:55 | RESULT| [manager] 応答を受信（1234文字）
```

### stderrの場合

```
18:31:00 | ERROR | [manager] Command failed: permission denied
```

---

## 実装の流れ

```
┌─────────────────┐
│ User Input      │
│ "タスクを実行"   │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────┐
│ Dashboard.send_to_manager()     │
│ - メッセージ送信                │
│ - on_log() コールバック設定      │
└────────┬────────────────────────┘
         │
         ↓
┌──────────────────────────────────┐
│ ClaudeCodeExecutor.execute_agent │
│ - プロセス起動                   │
│ - stdout/stderr 読み取り開始     │
└────────┬─────────────────────────┘
         │
         ↓
┌──────────────────────────────────┐
│ read_stream() (async)            │
│ - 1行ずつ読み取り                │
│ - log_callback() 呼び出し        │ ─┐
└──────────────────────────────────┘  │
                                      │
         ┌────────────────────────────┘
         │ リアルタイム
         ↓
┌──────────────────────────────────┐
│ on_log() callback                │
│ - ログレベル判定                 │
│ - ログビューアに追加             │
└────────┬─────────────────────────┘
         │
         ↓
┌──────────────────────────────────┐
│ SimpleLogViewer.add_log()        │
│ - ログエントリ作成               │
│ - デキューに追加                 │
│ - refresh_display()              │
└────────┬─────────────────────────┘
         │
         ↓
┌──────────────────────────────────┐
│ SimpleLogViewer.refresh_display()│
│ - ログ一覧表示                   │
│ - 色付け                         │
│ - 自動スクロール                 │
└──────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────┐
│ ユーザーに表示                   │
└──────────────────────────────────┘
```

---

## 技術的な詳細

### 非同期ストリーム処理

Claude Code CLIの出力を取得する際、`communicate()`を使うとプロセスが終了するまで出力が得られません。

**以前（ブロッキング）:**
```python
stdout, stderr = await process.communicate(input=prompt.encode())
# ↑ プロセス終了まで待機、リアルタイム表示不可
```

**現在（ノンブロッキング）:**
```python
# stdinにプロンプトを書き込む
if process.stdin:
    process.stdin.write(prompt.encode())
    await process.stdin.drain()
    process.stdin.close()

# stdout/stderrを並行して読み取る
await asyncio.gather(
    read_stream(process.stdout, stdout_lines, ""),
    read_stream(process.stderr, stderr_lines, "[stderr] "),
)
# ↑ 1行ずつリアルタイムで読み取り
```

### コールバック設計

ログコールバックは `callable` 型で、以下のシグネチャを想定:

```python
def log_callback(log_line: str) -> None:
    """
    Args:
        log_line: ログの1行（改行なし）
    """
    pass
```

ダッシュボード側で自由に処理できるよう、最小限のインターフェースにしています。

---

## パフォーマンス考慮事項

### メモリ使用量

- ログは `deque(maxlen=100)` で最大100行まで保持
- 古いログは自動的に削除される
- メモリリークの心配なし

### UI更新頻度

- ログが追加されるたびに `refresh_display()` を呼ぶ
- Textualの内部最適化により、過度な再描画は発生しない
- 必要に応じてバッファリング可能

### ストリーム読み取り

- `readline()` は非ブロッキング
- `asyncio.gather()` で並行処理
- CPU使用率は低い

---

## 拡張可能性

### 将来的な改善案

#### 1. ログのパース

Claude Code CLIの出力をパースして、構造化されたログを表示:

```python
def parse_log_level(line: str) -> str:
    """ログレベルを自動判定"""
    if "thinking" in line.lower():
        return "THINKING"
    elif "tool_use" in line.lower():
        return "TOOL"
    elif "error" in line.lower():
        return "ERROR"
    else:
        return "INFO"
```

#### 2. ログの永続化

```python
# セッションごとにログを保存
log_file = Path(f".mao/sessions/{session_id}/logs.jsonl")
with log_file.open("a") as f:
    f.write(json.dumps(log_entry) + "\n")
```

#### 3. ログ検索機能

```python
# ログビューアに検索バーを追加
def search_logs(self, query: str):
    """ログを検索"""
    return [log for log in self.logs if query in log]
```

#### 4. ログエクスポート

```bash
# ログをファイルに保存
mao export-logs --session <session_id> --output logs.txt
```

---

## トラブルシューティング

### ログが表示されない

**原因:** コールバックが設定されていない

**解決策:**
```python
# execute_agent() を呼ぶ際に log_callback を渡す
result = await executor.execute_agent(
    prompt=prompt,
    log_callback=on_log,  # ← これを忘れずに
)
```

### ログが遅れて表示される

**原因:** Claude Code CLIがバッファリングしている

**解決策:** 現在の実装では readline() で1行ずつ読み取っているため、
通常は遅延は発生しません。もし問題がある場合は、
Claude Code CLIの出力モードを確認してください。

### エラーログが赤く表示されない

**原因:** ログレベルの判定が正しくない

**解決策:**
```python
# stderrからの出力は自動的に ERROR レベルになる
if log_line.startswith("[stderr]"):
    level = "ERROR"
else:
    level = "INFO"
```

---

## 例: マネージャー実行時のログ

```
18:30:45 | INFO  | [manager] エージェント実行を開始（Claude Code CLI経由）
18:30:45 | INFO  | [manager] 作業ディレクトリ: /tmp/mao_agent_abc123
18:30:45 | INFO  | [manager] モデル: sonnet
18:30:46 | INFO  | [manager] 実行コマンド: "claude-code" --print --model sonnet --dangerously-skip-permissions --add-dir "/tmp/mao_agent_abc123"
18:30:46 | INFO  | [manager] プロンプト（stdin経由）: あなたはマネージャーエージェントです。...
18:30:50 | INFO  | [manager] タスクを以下の3つのサブタスクに分解します：
18:30:51 | INFO  | [manager] 1. ログイン機能の実装
18:30:51 | INFO  | [manager] 2. パスワードリセット機能の実装
18:30:52 | INFO  | [manager] 3. ユニットテストの作成
18:30:55 | RESULT| [manager] 応答を受信（1234文字）
18:30:55 | INFO  | [manager] 作業ディレクトリは保持: /tmp/mao_agent_abc123
```

---

## まとめ

リアルタイムログ機能により、以下が可能になりました:

✅ **透明性の向上**
- マネージャーが何をしているか即座に分かる
- デバッグが容易になる

✅ **ユーザー体験の向上**
- 待ち時間中に何が起きているか分かる
- 進捗状況が把握できる

✅ **問題の早期発見**
- エラーをリアルタイムで検出
- ログを見て原因を特定

✅ **拡張性**
- ログパース、検索、エクスポートなどの機能を追加可能
- ワーカーエージェントにも同様に適用可能

---

**次のステップ:**
- ワーカーエージェントのログもリアルタイム表示
- ログの永続化（セッションごと）
- ログ検索・フィルタリング機能

---

**作成日:** 2026-01-30
**更新予定:** 機能追加時
