# MAO アーキテクチャ

**バージョン:** 2.0
**最終更新:** 2026-02-03

---

## 概要

MAO (Multi-Agent Orchestrator) は、**tmux上での複数Claude Code CLIの並列実行**をコア機能とする、CTO主導のマルチエージェントシステムです。

## 設計思想

### コア機能（本質）

**tmux上での複数Claude Code CLIの並列実行**

- 全エージェントはtmuxペイン内でインタラクティブに動作
- CTOはペイン0で動作し、他エージェントを統括
- エージェント間はYAMLファイルベースで非同期通信
- `--print`オプション禁止（すべてインタラクティブモード）

### 補助機能

- **ダッシュボード**: 進捗確認用（オプション）
  - インタラクティブモードだけでは見づらい情報を表示
  - `mao dashboard` または `mao start --dashboard` で起動

## システム構成

### アーキテクチャ図

```
ユーザー
  ↓ (mao start "タスク")
CTO (tmuxペイン0: インタラクティブClaude Code)
  ├→ Agent-1 (tmuxペイン1: インタラクティブClaude Code)
  ├→ Agent-2 (tmuxペイン2: インタラクティブClaude Code)
  └→ ... (必要に応じて動的に起動)

[補助] ダッシュボード: 進捗・ログ表示
```

### 通信フロー

```
CTO                          Agent-1
 │                              │
 │ 1. タスクYAML作成             │
 │────────────────────────────→│
 │  .mao/queue/tasks/agent-1.yaml
 │                              │
 │                              │ 2. タスク実行
 │                              ↓
 │                          (作業中)
 │                              │
 │ 3. 結果YAML確認              │
 │←────────────────────────────│
 │  .mao/queue/reports/agent-1.yaml
 │                              │
```

## コンポーネント

| コンポーネント | 役割 | 実装ファイル |
|---------------|------|-------------|
| CLI | MAOの起動・設定 | `mao/cli_start.py` |
| TmuxManager | tmuxセッション管理 | `mao/orchestrator/tmux_manager.py` |
| TmuxExecutorMixin | ペイン内でのclaude起動 | `mao/orchestrator/tmux_executor.py` |
| TmuxGridMixin | 3x3グリッドレイアウト | `mao/orchestrator/tmux_grid.py` |
| TaskQueue | YAMLベースのタスクキュー | `mao/orchestrator/task_queue.py` |
| Dashboard | TUI（補助機能） | `mao/ui/dashboard_interactive.py` |

## 実行フロー

### 1. MAO起動

```bash
mao start "認証システムを実装"
```

実行される処理：
1. tmuxセッション作成（3x3グリッド）
2. CTOペイン（pane 0）でclaude起動
3. 初期タスクをCTOに送信

### 2. CTOがタスク分解

CTOは受け取ったタスクを分析し、YAMLファイルを作成してエージェントにタスクを割り当て：

```yaml
# .mao/queue/tasks/agent-1.yaml
task_id: task-001
role: agent-1
prompt: |
  ログイン機能のバックエンドAPIを実装してください。
  - POST /api/login エンドポイント
  - JWT認証
model: sonnet
status: ASSIGNED
assigned_at: 1706918400.0
```

### 3. エージェントがタスク実行

各エージェントはtmuxペイン内でインタラクティブに動作。
完了すると結果をYAMLで報告：

```yaml
# .mao/queue/reports/agent-1.yaml
task_id: task-001
role: agent-1
status: COMPLETED
result: |
  ログインAPIを実装しました。
  - src/api/auth.py を作成
  - テストを追加
completed_at: 1706920000.0
```

### 4. CTOが結果確認

CTOは結果を確認し、承認/追加作業指示/ユーザーへのエスカレーションを判断。

## ディレクトリ構造

```
your-project/
├── .mao/
│   ├── queue/
│   │   ├── tasks/           # CTOからエージェントへのタスク
│   │   │   ├── agent-1.yaml
│   │   │   └── agent-2.yaml
│   │   └── reports/         # エージェントからCTOへの報告
│   │       ├── agent-1.yaml
│   │       └── agent-2.yaml
│   ├── logs/                # ログファイル
│   │   ├── cto_20260203_120000.log
│   │   └── agent-1_20260203_120100.log
│   ├── sessions/            # セッション情報
│   └── state.db             # 状態DB（SQLite）
└── ...
```

## tmux統合

### セッション構成

```
┌─ CTO ─────────┬─ Agent-1 ─────┬─ Agent-2 ─────┐
│               │               │               │
│ Claude Code   │ Claude Code   │ Claude Code   │
│ (インタラクティブ)│ (インタラクティブ)│ (インタラクティブ)│
│               │               │               │
├───────────────┼───────────────┼───────────────┤
│ Agent-3       │ Agent-4       │ Agent-5       │
│               │               │               │
│ Claude Code   │ Claude Code   │ Claude Code   │
│ (待機中)       │ (待機中)       │ (待機中)       │
│               │               │               │
└───────────────┴───────────────┴───────────────┘
```

### 操作方法

```bash
# MAO起動
mao start "タスク"

# tmuxにアタッチ
tmux attach -t mao

# ペイン間移動
Ctrl+B → 矢印キー

# ペインズーム
Ctrl+B → z

# セッションからデタッチ
Ctrl+B → d
```

## CLI コマンド

| コマンド | 説明 |
|---------|------|
| `mao start "タスク"` | MAOを起動しCTOにタスクを送信 |
| `mao start --dashboard "タスク"` | ダッシュボード付きで起動 |
| `mao dashboard` | 既存セッションのダッシュボードを起動 |
| `mao init` | プロジェクト初期化 |

### オプション

```
mao start [OPTIONS] [PROMPT]

Options:
  -p, --project-dir PATH    プロジェクトディレクトリ
  -t, --task TEXT          タスク（PROMPT の代替）
  --model [sonnet|opus|haiku]  CTOのモデル
  -n, --num-agents INTEGER  エージェントペイン数（デフォルト: 4）
  --dashboard              ダッシュボードも起動
  -s, --session TEXT       継続するセッションID
  --new-session            新規セッション作成
```

## 設計原則

### 1. tmux中心

tmuxがすべてのエージェントプロセスを管理。ダッシュボードは補助機能。

### 2. インタラクティブモード必須

`--print`オプションは使用禁止。すべてのClaude Codeはインタラクティブモードで動作。

### 3. YAMLベース通信

エージェント間の通信はYAMLファイル経由。シンプルで監査可能。

### 4. CTO主導

CTOがすべてのタスク分配とレビューを担当。エージェントは独立して動作。

## 削除されたコンポーネント

以下のコンポーネントは新アーキテクチャで不要になりました：

- `claude_code_executor.py` - `--print`モード用
- `agent_loop.py` - ポーリングベースの実行
- `dashboard.py` - 旧ダッシュボード

---

## 参考

- [WORKFLOW.md](./WORKFLOW.md) - ワークフロー詳細
- [TMUX_ARCHITECTURE.md](./TMUX_ARCHITECTURE.md) - tmux統合詳細
