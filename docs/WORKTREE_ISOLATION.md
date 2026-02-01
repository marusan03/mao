# Git Worktree による作業環境分離

各エージェントを独立したgit worktreeで実行し、作業を完全に分離します。

## 🎯 目的

- **分離**: 各エージェントが独立した作業環境を持つ
- **並列性**: 複数エージェントが同時に異なるブランチで作業可能
- **安全性**: メインの作業ディレクトリに影響しない
- **可視性**: どのエージェントがどのworktreeで作業中か一目瞭然

## 🌳 Git Worktree とは

Git worktree は、1つのリポジトリで複数の作業ディレクトリを作成する機能です。

```bash
# 通常の方法（1つの作業ディレクトリ）
git checkout feature-branch
# → メインの作業ディレクトリが切り替わる

# Worktree を使う方法（複数の作業ディレクトリ）
git worktree add ../feature-work feature-branch
# → 新しいディレクトリができ、そこで作業可能
# → メインの作業ディレクトリはそのまま
```

## 📋 MAO での使用方法

### 自動的に Worktree が作成される

```bash
# インタラクティブモードで起動
mao start "認証システムを実装"

# → Managerエージェント: メインディレクトリ
# → Worker-1エージェント: .mao/worktrees/worker_worker-1_20260201_120000/
# → Worker-2エージェント: .mao/worktrees/worker_worker-2_20260201_120001/
# ...
```

### エージェント一覧で確認

ダッシュボードのエージェント一覧で各エージェントの情報が表示されます:

```
[Agents] 3 active

❯ ⚙ manager      Running...
  │ Tokens: 1,234

  ⚙ worker-1     Running...    🌳 worker_worker-1_20260201
  │ Tokens: 567

  ⚙ worker-2     Running...    🌳 worker_worker-2_20260201
  │ Tokens: 891
```

表示内容:
- **Role**: エージェントのロール（manager, worker-1, etc.）
- **Status**: 実行状態（Running, Completed, etc.）
- **🌳**: Worktree アイコン（worktree使用中を示す）
- **Worktree名**: 作業ディレクトリ名
- **Tokens**: 使用トークン数

## 🏗️ Worktree の構造

### ディレクトリ構成

```
project/
├── .mao/
│   └── worktrees/
│       ├── worker_worker-1_20260201_120000/  # Worker-1の作業環境
│       │   ├── mao/
│       │   ├── tests/
│       │   └── ... (プロジェクト全体のコピー)
│       ├── worker_worker-2_20260201_120001/  # Worker-2の作業環境
│       └── ...
├── mao/
├── tests/
└── ...
```

### Worktree 名の規則

```
{role}_{agent_id}_{timestamp}

例: worker_worker-1_20260201_120000
     ↑      ↑          ↑
   ロール  エージェントID  作成日時
```

### ブランチ名の規則

```
mao/{role}/{agent_id}

例: mao/worker/worker-1
```

## 🔧 技術詳細

### WorktreeManager クラス

```python
from mao.orchestrator.worktree_manager import WorktreeManager

# 初期化
manager = WorktreeManager(project_path=Path("/path/to/project"))

# Worktree を作成
worktree_path = manager.create_worktree(
    agent_id="worker-1",
    role="worker",
)
# → Path("/path/to/project/.mao/worktrees/worker_worker-1_...")

# Worktree を削除
manager.remove_worktree(worktree_path)

# すべての Worktree を削除
manager.cleanup_worktrees()
```

### エージェント状態への統合

```python
from mao.orchestrator.state_manager import StateManager, AgentStatus

state_manager = StateManager(project_path)

# Worktree パスを含めて状態を更新
await state_manager.update_state(
    agent_id="worker-1",
    role="worker",
    status=AgentStatus.RUNNING,
    worktree_path="/path/to/worktree",
)

# 状態を取得
state = await state_manager.get_state("worker-1")
print(state.worktree_path)  # Worktree パス
```

## 🎨 UI への反映

### AgentListWidget の更新

```python
from mao.ui.widgets.agent_list import AgentListWidget

agent_list = AgentListWidget()

# Worktree 情報を含めてエージェントを更新
agent_list.update_agent(
    agent_id="worker-1",
    status="running",
    role="worker",
    worktree_path="/path/to/.mao/worktrees/worker_worker-1_...",
)
```

### 表示される情報

1. **Role**: ロール名（manager, worker-1, etc.）
2. **Status**: 状態（Running, Completed, etc.）
3. **Worktree indicator**: 🌳 アイコン（使用中の場合のみ）
4. **Worktree name**: 短縮されたworktree名
5. **Tokens**: トークン使用量（2行目）

## 🧹 クリーンアップ

### 自動クリーンアップ

セッション終了時に自動的に worktree が削除されます。

### 手動クリーンアップ

```bash
# すべての worktree を削除
cd project/
python -c "
from pathlib import Path
from mao.orchestrator.worktree_manager import WorktreeManager

manager = WorktreeManager(Path.cwd())
cleaned = manager.cleanup_worktrees()
print(f'Cleaned {cleaned} worktrees')
"
```

### Git コマンドで確認

```bash
# アクティブな worktree を表示
git worktree list

# Worktree を手動削除（緊急時）
git worktree remove .mao/worktrees/worker_worker-1_...
```

## ⚠️ 注意事項

### Git リポジトリが必要

Worktree を使用するには、プロジェクトが Git リポジトリである必要があります。

- **Git リポジトリの場合**: Worktree が自動作成される
- **Git リポジトリでない場合**: メインディレクトリで実行される

### ディスク容量

各 worktree はプロジェクト全体のコピーを作成するため、ディスク容量を消費します。

```
プロジェクトサイズ: 100MB
エージェント数: 8

必要容量: 100MB × 8 = 800MB
```

### 同時実行の制限

Git の worktree は同じブランチを複数の worktree でチェックアウトできません。

MAO では各エージェント用に別々のブランチを作成するため、この制限は回避されます。

## 🚀 利点

### 1. 完全な分離

各エージェントが独立した作業環境を持つため:
- ファイルの競合がない
- 並列実行が安全
- 他のエージェントに影響しない

### 2. デバッグが容易

各エージェントの作業内容を個別に確認できる:

```bash
# Worker-1 の作業を確認
cd .mao/worktrees/worker_worker-1_.../
git diff
git log
```

### 3. ロールバックが簡単

問題があれば worktree を削除するだけ:

```bash
git worktree remove .mao/worktrees/worker_worker-1_...
```

### 4. 可視性

ダッシュボードで各エージェントがどこで作業中か一目瞭然。

## 📊 パフォーマンス

### 作成時間

Worktree の作成は高速（通常 < 1秒）:

```
プロジェクトサイズ: 100MB
作成時間: ~0.5秒
```

### メモリ使用量

各 worktree は独立しているため、メモリ使用量は増加しません。

### ディスクI/O

Git は内部で効率的にファイルを共有するため、実際のディスク使用量はプロジェクトサイズ × エージェント数より少なくなります。

## 🔗 参考

- [Git Worktree Documentation](https://git-scm.com/docs/git-worktree)
- [Git Worktree Tutorial](https://git-scm.com/book/en/v2/Git-Tools-Advanced-Merging#_git_worktree)
