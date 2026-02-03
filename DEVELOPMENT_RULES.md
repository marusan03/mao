# MAO Development Rules

**作成日**: 2026-02-02

> **Note**: Claude Code（AI開発アシスタント）向けのクイックガイドは [CLAUDE.md](./CLAUDE.md) を参照してください。

このドキュメントは、MAOシステムの開発・改修時に遵守すべきルールを定義します。

---

## 🔴 必須ルール

### 1. **改修時は必ず動作確認を実施する**

コードの変更を行った後は、**必ず動作確認を実施**してからコミットすること。

#### 動作確認の手順

1. **静的チェック**
   ```bash
   # 構文チェック
   python3 -m py_compile <変更したファイル>

   # 全ファイルの構文チェック
   find mao -name "*.py" -exec python3 -m py_compile {} \;
   ```

2. **インポートテスト**
   ```bash
   python3 -c "from mao.ui.widgets import CTOChatWidget; print('✅ Import OK')"
   ```

3. **静的解析**
   ```bash
   # 変更箇所の確認
   python3 scripts/verify_changes.py
   ```

4. **実際の動作確認**
   ```bash
   # MAOを起動して動作確認
   mao start "簡単なテストタスク"

   # エラーログを確認
   tail -f .mao/logs/*.log
   ```

5. **tmux統合の確認**（tmux関連の変更時）
   ```bash
   # tmuxにアタッチして表示を確認
   tmux attach -t mao

   # ペイン名を確認
   tmux list-panes -t mao -F "#{pane_index}: #{pane_title}"
   ```

#### チェックリスト

改修後、以下を全て確認すること：

- [ ] 構文エラーがない
- [ ] インポートエラーがない
- [ ] 実行時エラーが発生しない
- [ ] 既存機能が壊れていない（または破壊的変更を明記）
- [ ] 新機能が意図通り動作する
- [ ] 古い形式のコードが完全に削除されている
- [ ] ログにエラーが出ていない

---

### 2. **段階的な変更を心がける**

大規模な変更は、以下のように段階的に実施する：

1. **Phase 1**: ファイル名の変更
2. **Phase 2**: クラス名・変数名の変更
3. **Phase 3**: 各ファイルの統合
4. **Phase 4**: 動作確認
5. **Phase 5**: ドキュメント更新

各フェーズの後に、**必ず動作確認を実施**すること。

---

### 3. **変更の影響範囲を明確にする**

変更前に、影響範囲を調査・文書化する：

```bash
# 影響を受けるファイルを特定
grep -r "変更する文字列" mao/ --include="*.py"

# 参照元を確認
grep -r "クラス名\|変数名" mao/ --include="*.py" -n
```

影響範囲をドキュメント化：
- どのファイルを変更するか
- どのクラス/メソッドが影響を受けるか
- 後方互換性への影響

---

### 4. **後方互換性は基本的にNG（クリーンブレイク原則）**

**原則**: 後方互換性を保つためのコードは、基本的に追加しない。

#### なぜ後方互換性はNGか

1. **コードの複雑化**: 古い形式のサポートコードが残り、保守が困難になる
2. **バグの温床**: 複数の形式が混在すると、予期しないバグが発生しやすい
3. **移行の遅延**: 古い形式を削除するタイミングを逃し、技術的負債が蓄積する

#### 正しいアプローチ

```python
# ✅ 良い例: クリーンブレイク（古い形式は完全に削除）
elif msg.role == "cto":
    self.cto_chat_panel.chat_widget.add_cto_message(msg.content)

# ❌ 悪い例: 後方互換性のサポート（禁止）
elif msg.role == "cto" or msg.role == "manager":  # ← NG
    self.cto_chat_panel.chat_widget.add_cto_message(msg.content)
```

#### 既存データの扱い

古い形式のデータがある場合：

1. **セッションの破棄を推奨**
   ```bash
   # 古いセッションを削除
   rm -rf .mao/sessions/*

   # MAOを再起動
   mao start
   ```

2. **マイグレーションスクリプトの提供（必要に応じて）**
   ```python
   # scripts/migrate_sessions.py
   def migrate_manager_to_cto(session_file):
       """古いセッションデータをCTO形式に変換"""
       data = json.load(session_file)
       for msg in data['messages']:
           if msg['role'] == 'manager':
               msg['role'] = 'cto'  # 一括変換
       return data
   ```

3. **CHANGELOG.mdに破壊的変更を明記**
   ```markdown
   ## [BREAKING CHANGES] v1.1.0

   - `role="manager"` → `role="cto"` に変更
   - 既存セッションは削除して再作成してください
   ```

#### 例外: 後方互換性が許容されるケース

以下の場合のみ、後方互換性を考慮しても良い：

- **外部API**: ユーザーが制御できないシステムとの連携
- **設定ファイル**: デフォルト値を提供して移行を容易にする
- **公開ライブラリ**: 他のプロジェクトから使用されている場合

それ以外は、**クリーンブレイク（破壊的変更）を選択する**。

---

### 5. **テストケースを作成する**

重要な変更には、テストケースを作成する：

```python
# tests/unit/test_cto_chat.py
def test_cto_chat_widget():
    """CTOChatWidgetの基本動作をテスト"""
    widget = CTOChatWidget()

    # メソッドが存在することを確認
    assert hasattr(widget, 'add_cto_message')
    assert hasattr(widget, 'add_user_message')

    # 古いメソッドが削除されていることを確認
    assert not hasattr(widget, 'add_manager_message')
```

---

### 6. **ドキュメントを更新する**

コード変更時は、関連ドキュメントも更新する：

- `README.md`: 機能追加・変更
- `CHANGELOG.md`: 変更履歴
- `*.md`: 技術ドキュメント
- コメント: コード内のコメント

---

## 🟡 推奨ルール

### 1. **ファイルサイズ制限**

1ファイルのコードは**約500行**を目安とする。超える場合は責務ごとに分割する。

#### 分割パターン

```python
# Mixinパターンを使用した分割例
# main_module.py
from .mixin_a import MixinA
from .mixin_b import MixinB

class MainClass(MixinA, MixinB):
    """メインクラス（コア機能のみ）"""
    pass

# mixin_a.py
class MixinA:
    """責務Aを担当するミックスイン"""
    def method_a(self):
        pass

# mixin_b.py
class MixinB:
    """責務Bを担当するミックスイン"""
    def method_b(self):
        pass
```

#### 分割の目安

| 行数 | 推奨アクション |
|------|----------------|
| ~300行 | そのまま維持 |
| 300-500行 | 分割を検討 |
| 500行超 | **分割必須** |

#### TYPE_CHECKINGで循環インポート回避

Mixinでは `TYPE_CHECKING` を使って型ヒントを提供しつつ循環インポートを回避する：

```python
# mixin_module.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main_module import MainClass  # 実行時にはインポートされない

class SomeMixin:
    def method(self: "MainClass", arg: str) -> str:
        # selfの型をMainClassとして明示
        return self.main_attribute + arg
```

#### 後方互換性のためのRe-export

分割後も既存のimport文が動作するよう、メインモジュールでre-exportする：

```python
# main_module.py
from .helper import HelperClass, helper_function

__all__ = ["MainClass", "HelperClass", "helper_function"]
```

#### 詳細スキル

詳細な手順と実例は `mao/skills/learned/large_file_refactoring.md` を参照。

---

### 2. **コミット前のセルフレビュー**

```bash
# 変更内容を確認
git diff

# 変更されたファイル一覧
git status

# 意図しない変更がないか確認
git diff --stat
```

### 3. **変更サマリーを作成**

大規模な変更には、サマリードキュメントを作成：
- 変更の動機
- 変更内容
- 影響範囲
- テスト結果
- 既知の問題

---

## 📋 チェックリストテンプレート

### コード変更時

```markdown
## 変更チェックリスト

### 実装
- [ ] コード変更完了
- [ ] 構文エラーなし
- [ ] インポートエラーなし

### テスト
- [ ] 静的解析チェック合格
- [ ] インポートテスト合格
- [ ] 実行テスト合格
- [ ] 既存機能の動作確認

### 互換性
- [ ] 後方互換性確保
- [ ] 既存データの移行方法確認
- [ ] 既存設定との整合性確認

### ドキュメント
- [ ] コメント更新
- [ ] README更新（必要に応じて）
- [ ] 変更ドキュメント作成

### 最終確認
- [ ] git diff確認
- [ ] 意図しない変更なし
- [ ] ログにエラーなし
```

---

## 🚨 違反時の対応

ルール違反が発見された場合：

1. **即座に修正**
   - 実行時エラーが発生した場合は最優先で修正

2. **ロールバック検討**
   - 影響が大きい場合は、一旦ロールバックして再検討

3. **再発防止**
   - チェックリストを見直し
   - 自動化スクリプトを作成

---

## 🔧 自動化ツール

### 動作確認スクリプト

```bash
#!/bin/bash
# scripts/verify_changes.sh

echo "=== MAO 変更確認スクリプト ==="

# 1. 構文チェック
echo "1. 構文チェック..."
find mao -name "*.py" -exec python3 -m py_compile {} \; || exit 1
echo "   ✅ 構文チェック合格"

# 2. インポートテスト
echo "2. インポートテスト..."
python3 << 'EOF'
from mao.ui.widgets import CTOChatWidget
from mao.orchestrator.tmux_manager import TmuxManager
print("   ✅ インポートテスト合格")
EOF

# 3. 静的解析
echo "3. 静的解析..."
python3 scripts/static_analysis.py || exit 1
echo "   ✅ 静的解析合格"

echo ""
echo "✅ 全てのチェックに合格しました"
```

---

## 📚 参考資料

- **変更例**: `MANAGER_CTO_UNIFICATION.md`
- **テスト例**: `TMUX_INTEGRATION_TEST_RESULTS.md`

---

## 🎯 まとめ

**改修時の鉄則**:

1. ✅ **必ず動作確認を実施**
2. ✅ **段階的に変更**
3. ✅ **影響範囲を明確化**
4. ✅ **後方互換性を考慮**
5. ✅ **ドキュメント更新**

**これらのルールを遵守することで、安定した開発を実現します。**
