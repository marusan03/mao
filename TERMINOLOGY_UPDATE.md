# 用語統一: エージェントタイプ

**更新日**: 2026-02-02
**バージョン**: 0.2.1

---

## 🎯 変更の目的

実装とドキュメントの用語を「エージェントタイプ」に統一し、混乱を排除します。

## 📝 用語の変更

### Before（旧用語）
- ❌ "ワーカー" - 曖昧（実行主体なのか、タイプなのか不明）
- ❌ "ロール" - MAOロール定義（YAML）と混同
- ❌ "role" パラメータ - 意味が不明確

### After（新用語）
- ✅ "エージェント" - タスクを実行する主体
- ✅ "エージェントタイプ" - エージェントの種類（general-purpose, Explore, Bash, Plan）
- ✅ "agent_type" パラメータ - 明確な意味

---

## 🔄 変更内容

### 1. スキル定義の更新

**ファイル**: `.mao/skills/spawn-worker.yaml`

**変更点**:
```yaml
# Before
- name: role
  description: ワーカーのロール

# After
- name: agent-type
  description: エージェントタイプ
```

**使用例の更新**:
```bash
# Before
/spawn-worker --task "..." --role general-purpose --model sonnet

# After
/spawn-worker --task "..." --agent-type general-purpose --model sonnet
```

### 2. CTOプロンプトの更新

**ファイル**: `mao/ui/dashboard_interactive.py`

**変更箇所**:
- "ロール選択ガイド" → "エージェントタイプ選択ガイド"
- "ワーカーを起動" → "エージェントを起動"
- `--role` → `--agent-type`

**更新後のプロンプト**:
```
3. **エージェントタイプの選択**
   各タスクの性質に応じて、最適なエージェントタイプを選択してください：

   **エージェントタイプ選択ガイド:**
   - **general-purpose**: コード実装、ファイル編集、複雑なロジック
   - **Explore**: コードベース探索、ファイル検索、構造分析
   - **Bash**: コマンド実行、スクリプト実行、システム操作
   - **Plan**: 計画立案、アーキテクチャ設計、詳細なタスク分解

4. **エージェントを起動**
   /spawn-worker --task "..." --agent-type Explore --model haiku
```

### 3. JSONフォーマットの更新

**Before**:
```json
{
  "task": "タスク説明",
  "role": "general-purpose",
  "model": "sonnet"
}
```

**After**:
```json
{
  "task": "タスク説明",
  "agent_type": "general-purpose",
  "model": "sonnet"
}
```

**後方互換性**: `role` フィールドも引き続きサポート（fallback）

### 4. コードベースの更新

#### 変更されたフィールド名

| ファイル | Before | After |
|---------|--------|-------|
| `dashboard_interactive.py` | `worker_role` | `agent_type` |
| `approval_queue.py` | `role` | `agent_type` |
| `task_queue` dict | `'role'` | `'agent_type'` |

#### 更新されたメソッド

```python
# Before
async def _spawn_task_agent(
    self,
    task_description: str,
    worker_role: str,  # ❌
    model: str = "sonnet",
) -> None:
    ...

# After
async def _spawn_task_agent(
    self,
    task_description: str,
    agent_type: str,  # ✅
    model: str = "sonnet",
) -> None:
    ...
```

### 5. ドキュメントの更新

**ファイル**: `CTO_APPROVAL_WORKFLOW.md`
- 冒頭に用語定義を追加
- "ワーカー" → "エージェント" に統一

---

## 📊 利用可能なエージェントタイプ

MAOシステムで現在利用可能なエージェントタイプ：

### general-purpose
**用途**: コード実装、ファイル編集、複雑なロジック実装
**例**:
- 認証機能の実装
- APIエンドポイント作成
- バグ修正
- リファクタリング

### Explore
**用途**: コードベース探索、ファイル検索、構造分析
**例**:
- 既存の実装を調査
- 依存関係の把握
- アーキテクチャ理解
- 関連ファイルの特定

### Bash
**用途**: コマンド実行、スクリプト実行、システム操作
**例**:
- git操作
- ファイルのコピー/移動
- パッケージインストール
- テスト実行

### Plan
**用途**: 計画立案、アーキテクチャ設計、詳細なタスク分解
**例**:
- 実装方針の策定
- 技術選定
- 設計ドキュメント作成
- タスクの詳細化

---

## 🔄 移行ガイド

### 既存コードの更新

1. **スキル呼び出し**
```python
# Before
/spawn-worker --task "実装" --role general-purpose

# After
/spawn-worker --task "実装" --agent-type general-purpose
```

2. **JSON構造**
```python
# Before
{
    'task': '...',
    'role': 'Explore',  # ❌
    'model': 'haiku'
}

# After
{
    'task': '...',
    'agent_type': 'Explore',  # ✅
    'model': 'haiku'
}
```

3. **コード内部**
```python
# Before
agent_info = {
    'role': 'general-purpose',  # ❌
    'task': '...'
}

# After
agent_info = {
    'agent_type': 'general-purpose',  # ✅
    'task': '...'
}
```

### 後方互換性

- JSON内の `role` フィールドは引き続きサポート
- 内部的に `agent_type` に変換
- 段階的な移行が可能

---

## ✅ チェックリスト

実装完了項目:
- [x] spawn-worker.yamlスキル定義更新
- [x] CTOプロンプト更新（エージェントタイプガイド）
- [x] JSON抽出コード更新（agent_type対応）
- [x] _spawn_task_agent シグネチャ更新
- [x] approval_queue.py フィールド名更新
- [x] task_queue構造更新
- [x] ドキュメント更新（用語統一）
- [x] 後方互換性確保（role → agent_type fallback）

---

## 🎯 効果

### 明確性の向上
- ✅ 用語の意味が明確
- ✅ MAOロール（YAML）との混同を回避
- ✅ コードの可読性向上

### 保守性の向上
- ✅ 一貫した命名規則
- ✅ 新規開発者の理解が容易
- ✅ APIの意図が明確

### 拡張性の確保
- ✅ 将来的なエージェントタイプ追加が容易
- ✅ MAOロールシステムとの明確な分離
- ✅ カスタムエージェントタイプの追加余地

---

## 📚 参考資料

### 関連ドキュメント
- `IMPLEMENTATION_AUDIT.md` - 実装監査レポート
- `CTO_APPROVAL_WORKFLOW.md` - 承認ワークフロー
- `.mao/skills/spawn-worker.yaml` - スキル定義

### コードベース
- `mao/ui/dashboard_interactive.py` - CTOとエージェント管理
- `mao/orchestrator/approval_queue.py` - 承認キュー
- `mao/orchestrator/claude_code_executor.py` - エージェント実行エンジン

---

---

## 🔄 2026-02-02 修正: MAOロールへの完全移行

### 変更理由

当初の用語統一で「エージェントタイプ」に統一したが、元々の設計では**MAOロール**（YAML定義）を使用する予定だった。
Claude Codeのエージェントタイプ（general-purpose, Explore, Bash, Plan）は一時的な実装であり、正式なMAOロールに置き換える。

### 最終的な用語

- ✅ **role** パラメータ - MAOロール名（coder_backend, reviewer, tester, planner, researcher, auditor等）
- ✅ **MAOロール** - YAML定義されたロール（8種類）
- ❌ ~~agent_type~~ - 削除
- ❌ ~~エージェントタイプ~~ - 削除
- ❌ ~~後方互換性~~ - 削除

### MAOロール一覧

| ロール名 | 層 | 用途 | モデル |
|---------|---|------|-------|
| auditor | Governance | セキュリティ監査 | opus |
| planner | Planning | タスク計画 | sonnet |
| researcher | Planning | 技術調査 | sonnet |
| coder_backend | Development | バックエンド実装 | sonnet |
| reviewer | Quality | コードレビュー | sonnet |
| tester | Quality | テスト作成 | sonnet |
| skill_extractor | Integration | スキル抽出 | sonnet |
| skill_reviewer | Integration | スキルレビュー | sonnet |

### 実装された変更

1. **spawn-worker.yaml**
   - パラメータ名: `agent-type` → `role`
   - choices: Claude Codeタイプ → MAOロール名
   - JSON形式: `agent_type` → `role`

2. **dashboard_interactive.py**
   - TaskDispatcher統合: ロール定義自動読み込み
   - CTOプロンプト: MAOロール一覧を動的生成
   - JSONパース: 後方互換性削除、ロール検証追加
   - ワーカー起動: ロール定義ベースのプロンプト構築

3. **approval_queue.py**
   - ApprovalItem: `agent_type` → `role` フィールド
   - add_item(): パラメータ名変更

4. **使用例の更新**
   ```bash
   # 変更前
   /spawn-worker --task "実装" --agent-type general-purpose --model sonnet

   # 変更後
   /spawn-worker --task "実装" --role coder_backend --model sonnet
   ```

### 削除されたコード

- 後方互換性fallback: `worker_data.get("agent_type", worker_data.get("role", ...))`
- Claude Codeエージェントタイプの記述
- すべての`agent_type`フィールドとパラメータ

---

**更新者**: Claude Code (Sonnet 4.5)
**更新日**: 2026-02-02
