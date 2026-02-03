# Agent Lifecycle Management - Testing Guide

**作成日**: 2026-02-02
**実装完了日**: 2026-02-02

---

## 📋 実装概要

エージェントライフサイクル管理機能が実装されました。タスク完了後、承認/却下時、およびセッション終了時に、エージェントのリソース（状態、worktree）を自動的にクリーンアップします。

### 実装されたフェーズ

- ✅ **Phase 1**: 承認時のクリーンアップ (`on_approve_request`)
- ✅ **Phase 2**: 却下時のクリーンアップ (`_retry_task_with_feedback`)
- ✅ **Phase 3**: セッション終了時のクリーンアップ (`action_quit`)

---

## 🧪 テスト手順

### 前提条件

```bash
# MAOがインストールされていること
which mao

# Gitリポジトリで作業していること
git status

# .maoディレクトリがクリーンな状態
rm -rf .mao/agent_states.db .mao/worktrees/* .mao/approval_queue/*
```

---

## Phase 1: 承認時のクリーンアップ

### テスト1.1: エージェント状態の削除確認

```bash
# 1. エージェント起動前の状態確認
sqlite3 .mao/agent_states.db "SELECT agent_id, status FROM agent_states;"
# → 空であること

# 2. タスク実行
mao start "簡単なPythonスクリプトを作成して、Hello Worldを出力"

# 3. エージェント完了後、状態確認
sqlite3 .mao/agent_states.db "SELECT agent_id, status FROM agent_states;"
# → エージェントが存在すること（例: agent-1 | COMPLETED）

# 4. ダッシュボードで承認操作（UIから承認ボタンをクリック）

# 5. 承認後の確認
sqlite3 .mao/agent_states.db "SELECT agent_id, status FROM agent_states;"
# → エージェントが削除されていること（空）
```

**期待結果**:
- ✅ エージェント状態が `agent_states` テーブルから削除される
- ✅ ログに「✅ agent-X を承認してクリーンアップしました」と表示される

---

### テスト1.2: Worktreeの削除確認

```bash
# 1. Worktree一覧を確認
ls -la .mao/worktrees/
# → エージェント用のworktreeが存在すること

# 2. 承認後に確認
ls -la .mao/worktrees/
# → エージェント用worktreeが削除されていること

# 3. gitコマンドでも確認
git worktree list
# → エージェント用worktreeがリストから消えていること
```

**期待結果**:
- ✅ エージェント用worktreeが物理削除される
- ✅ `git worktree list` にも表示されない

---

### テスト1.3: 承認キューからの削除確認

```bash
# 1. 承認前の確認
cat .mao/approval_queue/index.json
# → 承認アイテムが存在すること

# 2. 承認後の確認
cat .mao/approval_queue/index.json
# → 承認アイテムが削除されていること、または配列が空
```

**期待結果**:
- ✅ ApprovalQueue から承認アイテムが削除される

---

## Phase 2: 却下時のクリーンアップ

### テスト2.1: 却下とリトライの動作確認

```bash
# 1. エージェントを起動
mao start "計算間違いのあるコードを書く"

# 2. エージェント完了後、承認キューを確認
cat .mao/approval_queue/index.json
# → アイテムが存在すること

# 3. ダッシュボードで却下操作 + フィードバック入力
#    「計算ロジックを修正してください」

# 4. 前回のエージェント状態確認
sqlite3 .mao/agent_states.db "SELECT agent_id, status FROM agent_states;"
# → 前回のエージェント（agent-1）が削除され、新しいエージェント（agent-2）が起動していること

# 5. 前回のworktree確認
ls -la .mao/worktrees/
# → 前回のworktreeが削除されていること

# 6. ログ確認
tail -f .mao/logs/*.log
# → 「🔄 agent-1 を却下してクリーンアップしました」と表示されること
```

**期待結果**:
- ✅ 前回のエージェント状態が削除される
- ✅ 前回のworktreeが削除される
- ✅ 新しいエージェントが起動する
- ✅ ログに両方のエージェント実行履歴が残る

---

### テスト2.2: ログタブの永続性確認

```bash
# 1. ダッシュボードのログタブを確認
#    - 前回のエージェント（agent-1）のログタブが存在すること
#    - 新しいエージェント（agent-2）のログタブが追加されること

# 2. 各ログタブで実行履歴が確認できること
#    - agent-1: 前回の失敗ログ
#    - agent-2: フィードバック付きの再実行ログ
```

**期待結果**:
- ✅ ログタブは削除されない（監査とデバッグのため）
- ✅ 両方のエージェント実行履歴が参照可能

---

## Phase 3: セッション終了時のクリーンアップ

### テスト3.1: 未承認タスクがある場合の警告

```bash
# 1. 複数タスクを実行
mao start "タスク1を実行"
mao start "タスク2を実行"

# 2. 一部は承認、一部は未承認のまま残す
#    → 例: タスク1は承認、タスク2は未承認

# 3. Ctrl+Q でMAOを終了

# 4. ログ確認
tail -20 .mao/logs/*.log
# → 「⚠️ 1件の未承認タスクがあります。終了します。」と表示されること
```

**期待結果**:
- ✅ 未承認タスクの警告が表示される

---

### テスト3.2: 全リソースのクリーンアップ

```bash
# 1. 複数エージェントが動いている状態で終了
#    （承認せずに Ctrl+Q）

# 2. エージェント状態確認
sqlite3 .mao/agent_states.db "SELECT * FROM agent_states;"
# → 空であること

# 3. Worktree確認
ls -la .mao/worktrees/
# → 空であること（または .mao/worktrees/ 自体が削除されていても良い）

# 4. タスクキュー確認
ls -la .mao/queue/tasks/
# → 空であること
```

**期待結果**:
- ✅ すべてのエージェント状態が削除される
- ✅ すべてのworktreeが削除される
- ✅ タスクキューが空になる
- ✅ 承認キューの承認済みアイテムが削除される

---

## 🐛 エッジケースのテスト

### ケース1: エージェントがエラー終了した場合

```bash
# 1. 意図的にエラーを起こすタスクを実行
mao start "存在しないファイルを読み込むコードを書く"

# 2. エラー終了後、状態確認
sqlite3 .mao/agent_states.db "SELECT agent_id, status FROM agent_states;"
# → エージェントがERROR状態で残っていること

# 3. セッション終了（Ctrl+Q）

# 4. エージェント状態確認
sqlite3 .mao/agent_states.db "SELECT agent_id, status FROM agent_states;"
# → 空であること（ERROR状態のエージェントもクリーンアップされる）
```

**期待結果**:
- ✅ ERROR状態のエージェントもセッション終了時にクリーンアップされる

---

### ケース2: 承認前にセッション終了

```bash
# 1. タスクを実行して完了まで待つ
mao start "簡単なタスク"

# 2. 承認せずにセッション終了（Ctrl+Q）

# 3. リソース確認
sqlite3 .mao/agent_states.db "SELECT * FROM agent_states;"
ls -la .mao/worktrees/
ls -la .mao/approval_queue/
# → すべて空であること
```

**期待結果**:
- ✅ 承認待ちのエージェントもクリーンアップされる
- ✅ 警告メッセージが表示される

---

### ケース3: Worktree削除の失敗

```bash
# 1. エージェント実行中にworktreeを手動でロック
# （実際にはテストしにくいが、ログでエラーハンドリングを確認）

# 2. 承認時のログを確認
#    → エラーが記録されるが、クラッシュしないこと
```

**期待結果**:
- ✅ worktree削除失敗時もクラッシュしない
- ✅ エラーがログに記録される

---

## 📊 パフォーマンステスト

### テスト: 大量エージェントのクリーンアップ

```bash
# 1. 10個のタスクを連続実行
for i in {1..10}; do
  mao start "テストタスク $i"
done

# 2. すべて承認せずにセッション終了
# Ctrl+Q

# 3. クリーンアップ時間を測定
#    → 数秒以内に終了すること
```

**期待結果**:
- ✅ 大量のエージェントも高速にクリーンアップされる
- ✅ メモリリークが発生しない

---

## ✅ テスト完了チェックリスト

### Phase 1
- [ ] エージェント状態が削除される
- [ ] Worktreeが削除される
- [ ] ApprovalQueueから削除される
- [ ] ログに承認メッセージが表示される

### Phase 2
- [ ] 前回のエージェント状態が削除される
- [ ] 前回のworktreeが削除される
- [ ] 新しいエージェントが起動する
- [ ] ログタブは削除されない

### Phase 3
- [ ] 未承認タスクの警告が表示される
- [ ] 全エージェント状態が削除される
- [ ] 全worktreeが削除される
- [ ] タスクキューが空になる

### エッジケース
- [ ] ERROR状態のエージェントもクリーンアップされる
- [ ] 承認前のセッション終了でもクリーンアップされる
- [ ] worktree削除失敗時もクラッシュしない

---

## 🎯 期待される効果

1. **メモリリーク防止**
   - エージェント完了後、状態が永続的に残らない
   - 長時間実行でもメモリ使用量が増加しない

2. **ディスク使用量削減**
   - 不要なworktreeが削除される
   - `.mao/` ディレクトリが肥大化しない

3. **リトライの改善**
   - 却下時に前回の状態が正しくクリアされる
   - フィードバック付きで再実行できる

4. **ログの保持**
   - 監査とデバッグのため、ログは残る
   - 過去のエージェント実行履歴を確認できる

---

## 🔧 デバッグ用コマンド

```bash
# エージェント状態を確認
sqlite3 .mao/agent_states.db "SELECT * FROM agent_states;"

# Worktree一覧
git worktree list
ls -la .mao/worktrees/

# 承認キュー確認
cat .mao/approval_queue/index.json | jq '.'

# ログ確認
tail -f .mao/logs/*.log

# タスクキュー確認
ls -la .mao/queue/tasks/
```

---

## 📝 トラブルシューティング

### 問題: エージェント状態が削除されない

**確認事項**:
1. `on_approve_request` が正しく呼ばれているか
2. `state_manager.clear_state()` がエラーを出していないか
3. ログで確認: `grep "を承認してクリーンアップ" .mao/logs/*.log`

**解決策**:
- ログにエラーがあれば修正
- StateManagerのコネクションを確認

---

### 問題: Worktreeが削除されない

**確認事項**:
1. `worktree_manager` が初期化されているか
2. `remove_worktree()` がエラーを返していないか
3. `git worktree list` でworktreeが残っているか

**解決策**:
```bash
# 手動でworktreeを削除
git worktree remove --force .mao/worktrees/<worktree_name>
```

---

## 🚀 次のステップ

テストが完了したら：

1. **CHANGELOG.md を確認**
   - 変更内容が正しく記載されているか

2. **ドキュメント更新**
   - 必要に応じて README.md や docs/ を更新

3. **コミット**
   ```bash
   git add .
   git commit -m "feat: Implement agent lifecycle management with automatic cleanup

   - Phase 1: Cleanup on approval (state, worktree, approval queue)
   - Phase 2: Cleanup on rejection before retry
   - Phase 3: Comprehensive cleanup on session exit
   - Add async callback support to ApprovalQueueWidget
   - Preserve logs for debugging and audit trail

   Fixes memory leaks and disk space issues from abandoned agent resources."
   ```

4. **PRを作成**（Feedback改善モードの場合）
   ```bash
   mao improve pr
   ```

---

**テスト担当者**: Claude Code
**テスト日**: 2026-02-02
**ステータス**: 実装完了、テスト準備完了
