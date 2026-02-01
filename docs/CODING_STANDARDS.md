# Coding Standards

MAO プロジェクトのコーディング規約

## 🎯 基本原則

1. **型安全性**: すべてに型アノテーションを付ける
2. **データ構造**: Pydantic モデルと Enum を使用
3. **イミュータブル**: dict は原則禁止、ミュータブルなデフォルト引数は完全禁止
4. **明示性**: 暗黙的な動作を避け、明示的にする

## 📦 データ構造定義

### ✅ 必須: Pydantic モデルを使用

```python
from pydantic import BaseModel, Field
from enum import Enum

# Enum で状態を定義
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# Pydantic でデータ構造を定義
class Task(BaseModel):
    id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = Field(default=1, ge=1, le=10)
    tags: list[str] = Field(default_factory=list)  # ✅ default_factory を使用
    metadata: dict[str, str] = Field(default_factory=dict)  # やむを得ない場合のみ

    class Config:
        frozen = True  # イミュータブルにする（推奨）
```

### ❌ 禁止: dict を直接使用

```python
# ❌ NG: 生の dict
def process_task(task: dict) -> dict:
    return {"status": "done"}

# ❌ NG: TypedDict も避ける（Pydantic を使う）
from typing import TypedDict

class TaskDict(TypedDict):
    id: str
    name: str
```

### ✅ OK: dict が許容される例外的なケース

```python
# JSONデータの一時的な保持（すぐ Pydantic に変換）
def load_config(path: str) -> Config:
    raw_data: dict[str, Any] = json.load(open(path))
    return Config.model_validate(raw_data)  # すぐ変換

# 動的キーの場合のみ（型を明示）
def get_env_vars() -> dict[str, str]:
    return dict(os.environ)
```

## 🚫 ミュータブルなデフォルト引数の完全禁止

### ❌ すべて禁止

```python
# ❌ NG: 直接のミュータブルデフォルト
def bad1(items: list[str] = []):
    pass

# ❌ NG: None パターンも禁止
def bad2(items: list[str] | None = None):
    if items is None:
        items = []
    pass

# ❌ NG: 空 dict
def bad3(config: dict[str, Any] = {}):
    pass

# ❌ NG: None + dict パターンも禁止
def bad4(config: dict[str, Any] | None = None):
    if config is None:
        config = {}
    pass
```

### ✅ 正しいパターン

#### パターン1: デフォルトなし（推奨）

```python
# ✅ OK: 呼び出し側で明示的に渡す
def process_items(items: list[str]) -> None:
    for item in items:
        print(item)

# 使用例
process_items([])  # 空リストを明示的に渡す
process_items(["a", "b"])
```

#### パターン2: Pydantic モデル

```python
# ✅ OK: Pydantic の default_factory
class ProcessConfig(BaseModel):
    items: list[str] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)

def process(config: ProcessConfig) -> None:
    pass

# 使用例
process(ProcessConfig())  # デフォルト値を使用
process(ProcessConfig(items=["a", "b"]))
```

#### パターン3: クラスメソッド（ファクトリパターン）

```python
# ✅ OK: クラスメソッドでファクトリを提供
class ItemProcessor:
    def __init__(self, items: list[str]):
        self._items = items

    @classmethod
    def create_empty(cls) -> "ItemProcessor":
        """空のプロセッサを作成"""
        return cls([])

    @classmethod
    def from_list(cls, items: list[str]) -> "ItemProcessor":
        """リストからプロセッサを作成"""
        return cls(items)

# 使用例
processor = ItemProcessor.create_empty()
processor = ItemProcessor.from_list(["a", "b"])
```

## 📋 Enum の使用

### ✅ 必須: 文字列の代わりに Enum

```python
from enum import Enum

# ✅ OK: Enum で定義
class AgentRole(str, Enum):
    MANAGER = "manager"
    WORKER = "worker"
    REVIEWER = "reviewer"

# ✅ OK: 使用例
class Agent(BaseModel):
    role: AgentRole
    name: str

agent = Agent(role=AgentRole.MANAGER, name="Manager-1")
```

### ❌ 禁止: リテラル文字列

```python
# ❌ NG: 文字列リテラル
class Agent(BaseModel):
    role: str  # "manager" | "worker" など

# ❌ NG: Literal も避ける（Enum を使う）
from typing import Literal

class Agent(BaseModel):
    role: Literal["manager", "worker", "reviewer"]
```

## 🔒 イミュータビリティ

### ✅ 推奨: frozen モデル

```python
# ✅ OK: frozen で変更不可にする
class Config(BaseModel):
    name: str
    value: int

    class Config:
        frozen = True

config = Config(name="test", value=1)
# config.value = 2  # エラー: frozen
```

### ✅ 推奨: dataclass の frozen

```python
from dataclasses import dataclass

# ✅ OK: frozen dataclass
@dataclass(frozen=True)
class Point:
    x: float
    y: float
```

## 📝 型アノテーション

### ✅ 必須: すべての関数に型アノテーション

```python
# ✅ OK: 完全な型アノテーション
def process_task(
    task: Task,
    options: ProcessOptions,
) -> TaskResult:
    """タスクを処理"""
    ...

# ✅ OK: 戻り値なしは None
def log_message(message: str) -> None:
    print(message)
```

### ❌ 禁止: 型アノテーションなし

```python
# ❌ NG: 型がない
def process(task):
    return task

# ❌ NG: 戻り値の型がない
def get_config():
    return Config()
```

## 🔍 型チェック

### Pyright 設定

```toml
[tool.pyright]
typeCheckingMode = "basic"  # または "strict"
reportMissingTypeStubs = false
reportUnknownParameterType = true
reportUnknownArgumentType = true
reportUnknownMemberType = true
```

## 📚 実例

### 良い例: タスク管理システム

```python
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(BaseModel):
    """タスク定義"""
    id: str
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        frozen = True

class TaskManager:
    """タスクマネージャー"""

    def __init__(self, tasks: list[Task]):
        """
        Args:
            tasks: タスクリスト（デフォルトなし）
        """
        self._tasks = tasks

    @classmethod
    def create_empty(cls) -> "TaskManager":
        """空のマネージャーを作成"""
        return cls([])

    def add_task(self, task: Task) -> "TaskManager":
        """タスクを追加（イミュータブル）"""
        return TaskManager(self._tasks + [task])

    def get_by_status(self, status: TaskStatus) -> list[Task]:
        """ステータスでフィルタ"""
        return [t for t in self._tasks if t.status == status]

# 使用例
manager = TaskManager.create_empty()
task = Task(
    id="task-1",
    title="Implement feature",
    description="Add new feature",
    priority=TaskPriority.HIGH,
)
manager = manager.add_task(task)
pending_tasks = manager.get_by_status(TaskStatus.PENDING)
```

## 🛠️ 自動チェック

### Ruff ルール

以下のルールで自動検出：

- **B006**: ミュータブルなデフォルト引数検出
- **B008**: 関数呼び出しのデフォルト引数検出
- **RUF013**: 暗黙的な Optional 検出
- **PYI**: 型スタブの問題検出
- **ARG**: 未使用引数検出

### 実行

```bash
# チェック
mise run quality

# 自動修正（型アノテーションは手動）
mise run quality-fix
```

## 📖 参考

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Enum](https://docs.python.org/3/library/enum.html)
- [Type Hints Cheat Sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)

## ✅ チェックリスト

新しいコードを書く前に：

- [ ] データ構造は Pydantic モデルで定義した？
- [ ] 状態や選択肢は Enum で定義した？
- [ ] dict を直接使っていない？（やむを得ない場合を除く）
- [ ] ミュータブルなデフォルト引数を使っていない？（None パターン含む）
- [ ] すべての関数に型アノテーションを付けた？
- [ ] `mise run quality` でエラーなし？
