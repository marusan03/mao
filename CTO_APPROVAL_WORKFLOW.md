# CTO承認ワークフロー - 実装完了

## 📋 概要

CTOがエージェントの作業を監視し、完了後に承認/却下を行う機能を実装しました。

**用語**: 本ドキュメントでは、タスクを実行する主体を「エージェント」、その種類を「MAOロール」と呼びます。MAOロールは YAML定義されたロール（coder_backend, reviewer, tester, planner, researcher, auditor 等）を指します。

## 🎯 実装した機能

### 1. ワーカー完了検知
- **ファイル**: `mao/orchestrator/tmux_manager.py`
- **機能**:
  - `is_pane_busy()`: ペインでプロセスが実行中か確認
  - `get_pane_content()`: ペインの出力を取得
  - `get_pane_status()`: 詳細ステータス取得

### 2. 承認キューシステム
- **ファイル**: `mao/orchestrator/approval_queue.py`
- **機能**:
  - 完了タスクの承認待ちキュー管理
  - approve/reject機能
  - 変更ファイル・出力の記録

### 3. シーケンシャル実行
- **ファイル**: `mao/ui/dashboard_interactive.py`
- **機能**:
  - タスクを順番に1つずつ実行
  - ワーカー完了を自動検知
  - 承認後に次のタスクを自動開始

### 4. CTOレビューコマンド
- **コマンド**:
  - `/approve <id> [feedback]`: タスクを承認して次へ
  - `/reject <id> <feedback>`: タスクを却下してフィードバック付きで再実行
  - `/diff <id>`: 変更内容の差分を表示

### 5. UI更新
- **ファイル**: `mao/ui/widgets/approval_widget.py`
- **機能**:
  - 承認待ちタスクの表示
  - ワーカーID、タスク説明、変更ファイル数を表示

## 🔄 ワークフロー

```
1. ユーザーがCTOにタスクを依頼
   ↓
2. CTOがタスクを分解（Task 1, Task 2, ...）
   ↓
3. タスクキューに追加し、Task 1を開始
   ↓
4. ワーカー1が作業を実行
   ↓
5. 完了検知 → 承認キューに追加
   ↓
6. CTOが承認待ちリストで確認
   ├─ /diff <id> で差分確認
   ├─ /approve <id> → Task 2を開始
   └─ /reject <id> "修正内容" → フィードバック付きで再実行
   ↓
7. 全タスク完了 → フィードバック送信/PR作成
```

## 🧪 テスト手順

### 準備
```bash
cd /Users/marusan/Work/claude/mao

# 設定確認（allow_unsafe_operations: true であること）
cat .mao/config.yaml

# tmuxが利用可能か確認
tmux -V
```

### テスト1: 基本的なタスク実行と承認

1. **ダッシュボード起動**
```bash
mao start --interactive "簡単なPythonスクリプトを作成してテストする"
```

2. **CTOの応答を確認**
   - CTOがタスクを分解（Task 1, Task 2, ...）
   - デバッグログで「📋 タスク1をキューに追加」を確認
   - 「🎯 シーケンシャルモード: タスク1/N を開始」を確認

3. **ワーカーの実行を確認**
   - Agentsパネルに worker-1 が表示される
   - Logsパネルでワーカーの進捗を確認

4. **完了検知を確認**
   - ワーカーが終了すると「✅ worker-1 完了 - 承認待ち」ログが表示
   - Approval Queueパネルに承認待ちタスクが表示

5. **承認**
```
/approve <id>
```
   - 「✅ タスク <id> を承認しました」メッセージ
   - 次のタスクが自動開始

### テスト2: 却下とフィードバック

1. **ワーカー完了後、差分確認**
```
/diff <id>
```

2. **却下してフィードバック**
```
/reject <id> エラーハンドリングを追加してください
```
   - 同じタスクがフィードバック付きで再実行される
   - ワーカーがフィードバックを反映して修正

3. **再度完了後、承認**
```
/approve <id> 修正を確認しました
```

### テスト3: 複数タスクの順次実行

1. **複数タスクを含む依頼**
```
以下の3つのタスクを実行してください：
1. utils.pyを作成
2. main.pyを作成してutilsを使用
3. テストを実行
```

2. **各タスクの完了を確認**
   - Task 1完了 → 承認 → Task 2開始
   - Task 2完了 → 承認 → Task 3開始
   - Task 3完了 → 承認 → 全完了

## 📊 デバッグ情報

### ログファイル
- **CTO応答**: `.mao/debug/cto_response_*.txt`
- **承認キュー**: `.mao/approval_queue/index.json`
- **セッション**: `.mao/sessions/<session_id>/messages.jsonl`

### 確認コマンド
```bash
# CTO応答を確認
cat .mao/debug/cto_response_*.txt

# 承認キューを確認
cat .mao/approval_queue/index.json | jq

# タスク抽出のテスト
python3 -c "
import re
text = '''
Task 1: テストファイルを作成
Role: general-purpose
Model: sonnet

Task 2: テストを実行
Role: Bash
Model: haiku
'''
pattern = r'(?:Task|タスク)\s*(\d+)[:：]\s*(.+?)(?=\n\s*\n(?:Task|タスク)|\n\s*\n---|\Z)'
tasks = re.findall(pattern, text, re.DOTALL | re.MULTILINE)
for num, content in tasks:
    print(f'Task {num}:')
    print(content[:100])
    print('---')
"
```

## ✅ チェックリスト

- [ ] tmuxが起動している
- [ ] `.mao/config.yaml`の`allow_unsafe_operations: true`
- [ ] ダッシュボードが起動する
- [ ] CTOがタスクを分解する
- [ ] ワーカーが表示される
- [ ] ワーカー完了が検知される
- [ ] 承認キューに追加される
- [ ] `/approve`で次のタスクが開始
- [ ] `/reject`で再実行される
- [ ] `/diff`で差分が表示される

## 🐛 トラブルシューティング

### ワーカーが表示されない
1. デバッグログを確認: 「🔍 タスクパターンマッチ数: 0件」
2. CTO応答を確認: `.mao/debug/cto_response_*.txt`
3. CTOプロンプトを確認して正しいフォーマットを要求

### 承認キューに追加されない
1. ワーカーが完了しているか確認（プロセスが終了）
2. `task_number`が設定されているか確認
3. シーケンシャルモードが有効か確認: `self.sequential_mode = True`

### tmuxペインが見えない
```bash
# tmuxセッションに接続
tmux attach -t mao

# ペインを切り替え
Ctrl+B → 矢印キー
```

## 📝 制限事項

1. **並列実行は未対応**: 現在はシーケンシャルモードのみ
2. **worktreeなしの場合**: 変更ファイル検出ができない
3. **長時間実行タスク**: 1秒ごとのポーリングで検知（遅延あり）

## 🚀 今後の改善案

1. **並列実行サポート**: 依存関係を指定して並列実行
2. **自動承認オプション**: 低リスクタスクは自動承認
3. **リアルタイム通知**: WebSocketで即座に完了通知
4. **詳細な差分表示**: ファイルごとの差分、統計情報
5. **承認履歴**: 承認/却下の履歴を記録

---

実装完了日: 2026-02-02
バージョン: 0.2.1
