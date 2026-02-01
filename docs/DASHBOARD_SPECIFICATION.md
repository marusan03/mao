# MAO Dashboard 設計書

**バージョン:** 2.0
**最終更新:** 2026-01-30
**ステータス:** 設計中

---

## 目次

1. [概要](#概要)
2. [現状分析](#現状分析)
3. [設計方針](#設計方針)
4. [UI/UX設計](#uiux設計)
5. [技術仕様](#技術仕様)
6. [実装計画](#実装計画)
7. [変更履歴](#変更履歴)

---

## 概要

### 目的
Multi-Agent Orchestrator（MAO）のTextualベースダッシュボードを、シンプルで使いやすいUIに再設計する。

### ゴール
- エージェントの状態が一目でわかる
- ログがリアルタイムで見やすい
- 操作が直感的
- tmuxとの連携がスムーズ

---

## 現状分析

### 現在の問題点

1. **複雑すぎるUI**
   - 6つのウィジェット（AgentStatus, TaskProgress, Metrics, ApprovalPanel, Activity, LogViewer）
   - 何を見れば良いかわからない
   - 情報が分散している

2. **見た目の問題**
   - レイアウトが煩雑（3x5グリッド）
   - 色使いが統一されていない
   - 視認性が低い

3. **操作性の問題**
   - キーボード操作がわかりにくい
   - `q`キーが動作しない（修正済み）
   - フォーカス移動が複雑

4. **機能の問題**
   - 承認パネルが複雑すぎる
   - メトリクスが詳細すぎる
   - 本当に必要な情報が埋もれている

### 現在のファイル構成

```
mao/ui/
├── dashboard.py          # メインダッシュボード
└── widgets/
    ├── agent_status.py   # エージェント状態
    ├── task_progress.py  # タスク進捗
    ├── metrics.py        # メトリクス
    ├── approval.py       # 承認パネル
    ├── activity.py       # アクティビティ
    └── log_viewer.py     # ログビューア
```

---

## 設計方針

### 基本原則

1. **シンプル・イズ・ベスト**
   - 必要最小限の情報のみ表示
   - 複雑な機能は削除または簡略化

2. **視認性優先**
   - 大きな文字
   - 明確な色分け
   - 適切な余白

3. **直感的な操作**
   - わかりやすいキーバインド
   - ヘルプの常時表示
   - 即座のフィードバック

4. **tmux連携**
   - ダッシュボードは最小限
   - 詳細はtmuxで確認
   - 役割分担を明確化

### 削除する機能

- ❌ 承認パネル（ApprovalPanel）→ 複雑すぎる
- ❌ 詳細メトリクス（Metrics）→ 基本情報のみ残す
- ❌ アクティビティウィジェット（Activity）→ ログで十分
- ❌ タスクコントロールパネル → 簡略化

### 残す機能

- ✅ エージェント状態表示（簡略化）
- ✅ ログビューア（改善）
- ✅ タスク情報ヘッダー（新規）
- ✅ 基本メトリクス（簡略化）

---

## UI/UX設計

### レイアウト案

#### 案1: シンプル版（推奨）

```
┌─────────────────────────────────────────────────────┐
│ MAO - Multi-Agent Orchestrator                     │
│ Task: 認証システムを実装して                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│ [Agents] 3/8 active                                 │
│ ✓ manager     Completed      Tokens: 1,234         │
│ ⚙ worker-1    Coding...      Tokens: 3,456         │
│ ⚙ worker-2    Testing...     Tokens: 2,123         │
│ ⏸ worker-3    Waiting        Tokens: 0             │
│ ⏸ worker-4    Waiting        Tokens: 0             │
│                                                     │
├─────────────────────────────────────────────────────┤
│ [Log] worker-1                          18:30:45   │
│                                                     │
│ INFO  | Starting coding task                       │
│ DEBUG | Reading file: auth.py                      │
│ INFO  | Implementing login function                │
│ TOOL  | Edit(auth.py:45-60)                        │
│                                                     │
│                                                     │
│                                                     │
└─────────────────────────────────────────────────────┘
 q:Quit r:Refresh ↑↓:Agent ←→:Log Enter:Detail
```

**特徴:**
- 上部: タスク情報
- 中部: エージェント一覧（スクロール可能）
- 下部: ログ表示（選択したエージェント）
- 最下部: キーバインドヘルプ

#### 案2: 詳細版

```
┌─────────────────────────────────────────────────────┐
│ MAO - Multi-Agent Orchestrator        Cost: $0.45  │
│ Task: 認証システムを実装して                          │
│ Progress: [████████░░] 80%   Est: 5min remaining   │
├─────────────────────────────────────────────────────┤
│ [Agents] 3/8 active  Queue: 1                       │
│ ✓ manager     Completed      1,234 tok  $0.05      │
│ ⚙ worker-1    Coding...      3,456 tok  $0.15      │
│ ⚙ worker-2    Testing...     2,123 tok  $0.10      │
│ ⏸ worker-3    Waiting (blocked by worker-1)        │
├─────────────────────────────────────────────────────┤
│ [Live Log - worker-1]                   18:30:45   │
│ INFO  | Starting coding task                       │
│ DEBUG | Reading auth.py                            │
│ INFO  | Implementing login() function              │
│ TOOL  | Edit(auth.py:45-60) ✓                      │
│ INFO  | Running tests...                           │
│                                                     │
└─────────────────────────────────────────────────────┘
 q:Quit r:Refresh ↑↓:Agent ←→:Log Enter:Detail
```

**特徴:**
- 進捗バー表示
- コスト/時間情報
- より詳細なエージェント情報
- ブロック状態の表示

#### 案3: 超シンプル版

```
┌─────────────────────────────────────────────────────┐
│ MAO                                                 │
│ Task: 認証システムを実装して                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│ ⚙ 3 agents working...                              │
│                                                     │
│ Latest activity:                                    │
│ • worker-1: Implementing login function            │
│ • worker-2: Writing unit tests                     │
│ • worker-3: Reviewing code                         │
│                                                     │
│                                                     │
│                                                     │
│                                                     │
│                                                     │
└─────────────────────────────────────────────────────┘
 q:Quit  |  tmux attach -t mao で詳細確認
```

**特徴:**
- 最小限の情報
- tmuxへの誘導
- 状態確認のみ

### カラースキーム

```python
# ステータスカラー
STATUS_COLORS = {
    "completed": "green",      # ✓ 完了
    "running": "yellow",       # ⚙ 実行中
    "waiting": "dim",          # ⏸ 待機
    "error": "red",            # ✗ エラー
}

# ログレベルカラー
LOG_COLORS = {
    "INFO": "cyan",
    "DEBUG": "dim",
    "WARN": "yellow",
    "ERROR": "red",
    "TOOL": "magenta",
}

# テーマカラー
THEME = {
    "header": "bold cyan",
    "border": "blue",
    "highlight": "green",
    "text": "white",
    "dim": "dim white",
}
```

### アイコン

```python
ICONS = {
    "completed": "✓",
    "running": "⚙",
    "waiting": "⏸",
    "error": "✗",
    "info": "ℹ",
    "warning": "⚠",
}
```

---

## 技術仕様

### ウィジェット構成（新）

```
dashboard.py (App)
├── HeaderWidget          # タスク情報ヘッダー
├── AgentListWidget       # エージェント一覧（新規）
└── LogViewerWidget       # ログビューア（改良）
```

### キーバインド

| キー | アクション | 説明 |
|------|-----------|------|
| `q` | quit | アプリ終了 |
| `r` | refresh | 画面更新 |
| `↑` | select_prev | 前のエージェント選択 |
| `↓` | select_next | 次のエージェント選択 |
| `←` | log_prev | 前のエージェントのログ |
| `→` | log_next | 次のエージェントのログ |
| `Enter` | show_detail | エージェント詳細表示 |
| `Esc` | close_detail | 詳細を閉じる |
| `h` | help | ヘルプ表示 |

### データ構造

```python
# エージェント状態
@dataclass
class AgentState:
    agent_id: str
    role: str
    status: Literal["completed", "running", "waiting", "error"]
    current_task: str
    tokens_used: int
    cost: float
    start_time: datetime
    end_time: Optional[datetime] = None

# ログエントリ
@dataclass
class LogEntry:
    timestamp: datetime
    level: Literal["INFO", "DEBUG", "WARN", "ERROR", "TOOL"]
    message: str
    agent_id: str
```

### 状態管理

```python
class Dashboard(App):
    def __init__(self):
        self.agents: Dict[str, AgentState] = {}
        self.selected_agent_index: int = 0
        self.log_entries: List[LogEntry] = []
        self.task_info: Dict[str, Any] = {}
```

---

## 実装計画

### Phase 1: 基盤整備（優先度: 高）

**タスク:**
1. ✅ `action_quit()`メソッド追加
2. ✅ 空プロンプトのエラーハンドリング
3. ✅ tmuxステータスバー実装
4. ✅ グリッド表示簡略化
5. [ ] 新しいウィジェット設計

**成果物:**
- `HeaderWidget` - タスク情報表示
- `AgentListWidget` - エージェント一覧
- 改良版 `LogViewerWidget`

**期間:** 1日

### Phase 2: UI実装（優先度: 高）

**タスク:**
1. [ ] レイアウト1（シンプル版）実装
2. [ ] カラースキーム適用
3. [ ] キーバインド実装
4. [ ] レスポンシブ対応

**成果物:**
- 新ダッシュボードUI
- キーボード操作完全対応

**期間:** 2日

### Phase 3: 機能統合（優先度: 中）

**タスク:**
1. [ ] エージェント状態のリアルタイム更新
2. [ ] ログのストリーミング表示
3. [ ] エラーハンドリング強化
4. [ ] パフォーマンス最適化

**成果物:**
- 安定動作するダッシュボード
- リアルタイム更新機能

**期間:** 2日

### Phase 4: 拡張機能（優先度: 低）

**タスク:**
1. [ ] 進捗バー実装
2. [ ] コスト計算・表示
3. [ ] エージェント詳細モーダル
4. [ ] ログのフィルタリング

**成果物:**
- 拡張機能
- 詳細表示モーダル

**期間:** 2日

### Phase 5: テスト・ドキュメント（優先度: 中）

**タスク:**
1. [ ] ユニットテスト作成
2. [ ] E2Eテスト作成
3. [ ] ユーザーガイド更新
4. [ ] スクリーンショット追加

**成果物:**
- テストスイート
- 完全なドキュメント

**期間:** 1日

---

## ファイル構成（新）

```
mao/ui/
├── dashboard.py                    # メインアプリ（簡略化）
└── widgets/
    ├── __init__.py
    ├── header.py                   # 新規: ヘッダーウィジェット
    ├── agent_list.py               # 新規: エージェント一覧
    ├── log_viewer.py               # 改良: ログビューア
    └── detail_modal.py             # 新規: 詳細モーダル

docs/
├── DASHBOARD_SPECIFICATION.md      # この設計書
├── DASHBOARD_DESIGN.md             # デザイン案
└── USAGE.md                        # 使い方ガイド
```

---

## 実装ガイドライン

### コーディング規約

1. **型ヒント必須**
   ```python
   def update_agent_status(self, agent_id: str, status: str) -> None:
   ```

2. **Docstring必須**
   ```python
   def refresh_display(self) -> None:
       """画面を再描画してエージェント状態を更新"""
   ```

3. **定数は大文字**
   ```python
   MAX_LOG_LINES = 1000
   UPDATE_INTERVAL = 0.5  # seconds
   ```

4. **クラスはデータクラス優先**
   ```python
   @dataclass
   class AgentState:
       agent_id: str
       status: str
   ```

### パフォーマンス考慮事項

1. **ログの制限**
   - 最大1000行まで保持
   - 古いログは自動削除

2. **更新頻度**
   - ログ: 0.5秒ごと
   - エージェント状態: 1秒ごと

3. **非同期処理**
   - ログファイル読み込みは非同期
   - UI更新はメインスレッド

---

## テスト計画

### ユニットテスト

```python
# tests/unit/test_dashboard_widgets.py
def test_agent_list_widget_display():
    """エージェント一覧の表示テスト"""

def test_log_viewer_update():
    """ログビューアの更新テスト"""

def test_header_widget_task_info():
    """ヘッダーウィジェットのタスク情報表示テスト"""
```

### 統合テスト

```python
# tests/integration/test_dashboard_ui.py
def test_dashboard_startup():
    """ダッシュボード起動テスト"""

def test_dashboard_key_bindings():
    """キーバインドテスト"""

def test_dashboard_agent_selection():
    """エージェント選択テスト"""
```

---

## 変更履歴

### v2.0 - 2026-01-30（予定）
- [ ] シンプルなUIに全面刷新
- [ ] 不要なウィジェット削除
- [ ] キーバインド改善
- [ ] パフォーマンス改善

### v1.1 - 2026-01-30
- [x] `action_quit()`追加（qキーで終了）
- [x] 空プロンプトエラーハンドリング
- [x] tmuxステータスバー追加
- [x] グリッド表示簡略化

### v1.0 - 2026-01-28
- 初期実装
- 6つのウィジェット
- 基本的な機能

---

## 参考資料

### Textual ドキュメント
- https://textual.textualize.io/
- https://textual.textualize.io/widgets/

### デザイン参考
- htop
- lazygit
- k9s

### 関連ファイル
- `QUICKSTART.md` - クイックスタートガイド
- `USAGE.md` - 詳細な使い方
- `DASHBOARD_DESIGN.md` - デザイン案

---

## FAQ

### Q: なぜTextualを使うのか？
A: Pythonネイティブで、リッチなTUIを簡単に構築できるため。

### Q: tmuxとの役割分担は？
A: ダッシュボード=概要確認、tmux=詳細ログ確認

### Q: レイアウト案はどれを採用？
A: 案1（シンプル版）を推奨。必要に応じて案2の機能を追加。

### Q: 古いウィジェットは削除？
A: 段階的に移行。古いウィジェットは`deprecated/`に移動。

---

## TODO

- [ ] Phase 1実装開始
- [ ] ユーザーフィードバック収集
- [ ] デザイン最終決定
- [ ] 実装スケジュール確定

---

**次のアクション:**
1. レイアウト案の確定（ユーザー確認）
2. Phase 1タスクの開始
3. プロトタイプ作成

**レビュー予定:** 実装開始前にユーザーレビュー必須
