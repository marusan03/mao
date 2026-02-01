# MAO 使い方ガイド

## 🚀 クイックスタート

### 1. プロジェクトの初期化
```bash
cd your-project
mao init
```

### 2. エージェントを起動してタスクを実行

```bash
# タスクを指定して起動（推奨）
mao start "ログイン機能のテストを書いて"

# グリッドレイアウトで複数エージェント起動
mao start --grid "認証システムを実装して"
```

**重要**: タスクを指定すると、自動的にClaude Codeエージェントが起動して作業を開始します！

## 📺 画面の見方

### ダッシュボード（TUI画面）
`mao start`を実行すると、Textualダッシュボードが表示されます：

```
┌─────────────────────────────────────────┐
│ Multi-Agent Orchestrator                │
├──────────────┬──────────────┬───────────┤
│ Agent Status │ Task Progress│ Metrics   │
│              │              │           │
│ ・Manager: ⚙ │ ・Task 1: ✓ │ Tokens: X │
│ ・Worker-1:⚙│ ・Task 2: ⚙ │ Cost: $Y  │
│              │              │           │
├──────────────┴──────────────┴───────────┤
│ Log Viewer                              │
│ [エージェントのログがここに流れます]       │
└─────────────────────────────────────────┘
```

**キーボードショートカット**:
- `q`: 終了
- `r`: 画面更新
- `Ctrl+C`: 緊急停止

### tmuxグリッド（--grid使用時）

別ターミナルで`tmux attach -t mao`を実行すると、3x3グリッドが表示されます：

```
┌─ 📋 MANAGER ──┬─ 🔧 WORKER-1 ─┬─ 🔧 WORKER-2 ─┐
│               │               │               │
│ [ログ表示]     │ [ログ表示]     │ [ログ表示]     │
│               │               │               │
├───────────────┼───────────────┼───────────────┤
│ 🔧 WORKER-3   │ 🔧 WORKER-4   │ 🔧 WORKER-5   │
│               │               │               │
│ [ログ表示]     │ [ログ表示]     │ [ログ表示]     │
│               │               │               │
├───────────────┼───────────────┼───────────────┤
│ 🔧 WORKER-6   │ 🔧 WORKER-7   │ 🔧 WORKER-8   │
│               │               │               │
│ [ログ表示]     │ [ログ表示]     │ [ログ表示]     │
│               │               │               │
└───────────────┴───────────────┴───────────────┘
```

各ペインの上部にステータスバーでロール名が表示されます。

**tmux操作**:
- `tmux attach -t mao`: アタッチ
- `Ctrl+B` → `d`: デタッチ
- `Ctrl+B` → `矢印キー`: ペイン移動
- `Ctrl+B` → `z`: ペイン拡大/縮小

## 🎯 実際の使用例

### 例1: テストを書く
```bash
mao start "login.pyのテストをtests/test_login.pyに作成して"
```

### 例2: バグ修正
```bash
mao start --role coder_backend "API エンドポイント /users が500エラーを返す問題を修正"
```

### 例3: 複雑なタスクを複数エージェントで
```bash
mao start --grid "完全な認証システムを実装：ログイン、ログアウト、パスワードリセット"
```

### 例4: コードレビュー
```bash
mao start --role reviewer "最新のPRをレビューして改善点を提案"
```

## ⚙️ オプション

### ロールの指定
```bash
--role <role_name>
```

利用可能なロール:
- `coder_backend`: バックエンド開発
- `tester`: テスト作成
- `reviewer`: コードレビュー
- `planner`: タスク計画
- `researcher`: 技術調査

ロール一覧を確認:
```bash
mao roles
```

### モデルの指定
```bash
--model <sonnet|opus|haiku>
```

- `sonnet`: バランス型（デフォルト）
- `opus`: 高性能・複雑なタスク向け
- `haiku`: 高速・シンプルなタスク向け

### tmux無効化
```bash
--no-tmux
```

ダッシュボードのみで実行（tmuxセッションを作成しない）

## 🔍 トラブルシューティング

### エージェントが起動しない
1. API キーの確認:
   ```bash
   echo $ANTHROPIC_API_KEY
   ```

2. 設定ファイルの確認:
   ```bash
   cat .mao/config.yaml
   ```

### tmuxが見つからない
```bash
brew install tmux  # macOS
# または
apt install tmux   # Ubuntu
```

### ダッシュボードが見づらい
```bash
# tmuxのみで起動（ダッシュボードを最小化）
mao start --grid "タスク"
# 別ターミナルで
tmux attach -t mao
```

## 📚 その他のコマンド

```bash
mao config          # 設定表示
mao languages       # サポート言語一覧
mao skills list     # 利用可能なスキル
mao version         # バージョン情報
mao --help          # ヘルプ
```

## 💡 ベストプラクティス

1. **具体的なタスクを指定**: 「コードを書いて」ではなく「login.pyにユニットテストを追加」
2. **グリッドは複雑なタスクで**: 単純なタスクは通常モードで十分
3. **tmuxで進捗確認**: 長時間タスクはtmuxでログを確認
4. **適切なロールを選択**: タスクに合ったロールを指定すると精度向上
