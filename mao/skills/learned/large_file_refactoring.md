# Skill: Large File Refactoring with Mixin Pattern

## 概要

500行を超える大規模Pythonファイルを、Mixinパターンを使用して責務ごとに分割するスキル。

## 適用条件

- ファイルが500行を超えている
- 単一クラスに複数の責務が混在している
- メソッドが論理的なグループに分けられる

## 分割手順

### Step 1: 現状分析

```bash
# 行数確認
wc -l target_file.py

# クラス・メソッド構造を把握
grep -n "class \|def " target_file.py
```

### Step 2: 責務の分類

メソッドを以下の観点でグループ化：
1. **コア機能** - クラスの本質的な責務
2. **入出力処理** - パース、シリアライズ
3. **状態管理** - 状態の更新、監視
4. **イベント処理** - ハンドラ、コールバック
5. **外部連携** - API呼び出し、プロセス管理

### Step 3: Mixinファイル作成

```python
# mixin_example.py
"""
Example Mixin - 特定の責務を担当
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main_module import MainClass

class ExampleMixin:
    """特定の責務を担当するミックスイン"""

    def method_a(self: "MainClass", arg: str) -> str:
        """
        TYPE_CHECKINGで型ヒントを提供しつつ
        循環インポートを回避
        """
        # self.xxxで親クラスの属性にアクセス可能
        return self.some_attribute + arg
```

### Step 4: メインクラス更新

```python
# main_module.py
from .mixin_a import MixinA
from .mixin_b import MixinB
from .mixin_c import MixinC

class MainClass(MixinA, MixinB, MixinC, BaseClass):
    """
    メインクラス（コア機能のみ保持）

    継承順序: 左から右へ優先度が下がる
    MRO (Method Resolution Order) に注意
    """

    def __init__(self):
        # コア初期化のみ
        pass
```

### Step 5: 後方互換性の維持

```python
# main_module.py
from .helper_module import HelperClass, helper_function

# Re-export for backward compatibility
__all__ = [
    "MainClass",
    "HelperClass",      # 移動したクラス
    "helper_function",  # 移動した関数
]
```

## 検証チェックリスト

```bash
# 1. 構文チェック
python3 -m py_compile main_module.py mixin_*.py

# 2. インポートテスト
python3 -c "from package.main_module import MainClass; print('OK')"

# 3. 継承チェック
python3 -c "
from package.main_module import MainClass
from package.mixin_a import MixinA
assert issubclass(MainClass, MixinA)
print('Inheritance OK')
"

# 4. メソッド存在チェック
python3 -c "
from package.main_module import MainClass
obj = MainClass()
assert hasattr(obj, 'method_from_mixin_a')
print('Methods OK')
"
```

## 実例: MAOリファクタリング

### dashboard_interactive.py (2118行 → 6ファイル)

| ファイル | 行数 | 責務 |
|---------|------|------|
| `dashboard_interactive.py` | 441行 | コアApp, CSS, compose |
| `dashboard_parser.py` | 347行 | CTO応答のパース |
| `dashboard_spawner.py` | 339行 | エージェント起動 |
| `dashboard_state.py` | 230行 | 状態更新 |
| `dashboard_cto.py` | 292行 | CTO通信 |
| `dashboard_handlers.py` | 558行 | イベントハンドラ |

### agent_executor.py (578行 → 3ファイル)

| ファイル | 行数 | 責務 |
|---------|------|------|
| `agent_executor.py` | 203行 | コア実行 |
| `agent_streaming.py` | 276行 | ストリーミング |
| `agent_process.py` | 134行 | プロセス管理 |

## 注意点

### TYPE_CHECKINGの活用

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # 実行時にはインポートされない
    # 型チェッカーのみが参照
    from .main_module import MainClass
```

これにより：
- 循環インポートを回避
- IDEの補完・型チェックは有効
- 実行時のオーバーヘッドなし

### MRO（Method Resolution Order）

```python
class Main(MixinA, MixinB, Base):
    pass

# MROの確認
print(Main.__mro__)
# (<class 'Main'>, <class 'MixinA'>, <class 'MixinB'>, <class 'Base'>, <class 'object'>)
```

同名メソッドがある場合、左側のMixinが優先される。

### self の型ヒント

```python
def method(self: "MainClass", arg: str) -> str:
    # selfの型をMainClassとして明示
    # Mixin単体では不完全だが、継承後は正しく動作
    return self.main_class_attribute + arg
```

## アンチパターン

### ❌ 過度な分割

```python
# 悪い例: 1メソッド1ファイル
class SingleMethodMixin:
    def only_method(self):
        pass
```

### ❌ 相互依存するMixin

```python
# 悪い例: MixinAがMixinBのメソッドを直接呼ぶ
class MixinA:
    def method_a(self):
        self.method_b()  # MixinBに依存 - NG
```

### ❌ Mixinに状態を持たせる

```python
# 悪い例: Mixinが__init__で状態を初期化
class BadMixin:
    def __init__(self):
        self.mixin_state = {}  # NG - 親クラスの__init__と競合
```

## 推奨される分割サイズ

| 分割後のファイル | 推奨行数 |
|----------------|---------|
| メインクラス | 200-400行 |
| 各Mixin | 100-300行 |
| ヘルパー/ユーティリティ | 50-150行 |

合計が元のファイルより10-20%増加するのは正常（import文、docstring等の重複）。
