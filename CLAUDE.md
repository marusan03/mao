# CLAUDE.md - MAO開発ガイド for Claude Code

このドキュメントは、Claude Code（AI開発アシスタント）がMAOコードベースで作業する際の必読ガイドです。

## 🚨 最初に読むべきこと

MAOコードベースで作業を始める前に、以下を必ず読んでください：

1. **[DEVELOPMENT_RULES.md](./DEVELOPMENT_RULES.md)** - 🔴 必須
   - 改修時の必須ルール（動作確認、段階的変更、クリーンブレイク原則）
   - 後方互換性NG原則
   - チェックリストテンプレート

2. **このドキュメント（CLAUDE.md）** - ドキュメント構造とナビゲーション

3. **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - システムアーキテクチャ理解

---

## 🔧 改修の基本フロー

### ステップ1: ドキュメント読解

タスクに応じて、以下のドキュメントを読む：

| タスク | 読むべきドキュメント |
|--------|---------------------|
| アーキテクチャ変更 | `docs/ARCHITECTURE.md` |
| UI/UX変更 | `docs/ARCHITECTURE.md` (UIコンポーネント構造) |
| Claude Code統合 | `docs/CLAUDE_CODE_INTEGRATION.md` |
| エージェント動作 | `mao/agents/*.md` (プロンプトファイル) |
| tmux統合 | `TMUX_INTEGRATION_IMPLEMENTATION.md` |
| 過去の大規模変更 | `MANAGER_CTO_UNIFICATION.md` など |

### ステップ2: 影響範囲の調査

```bash
# 変更対象の文字列を検索
grep -r "変更する文字列" mao/ --include="*.py" -n

# クラス/関数の参照箇所を特定
grep -r "ClassName\|function_name" mao/ --include="*.py" -n
```

### ステップ3: コード変更

DEVELOPMENT_RULES.mdの原則に従う：
- ✅ 段階的に変更（Phase 1, 2, 3...）
- ✅ 各フェーズ後に動作確認
- ✅ 後方互換性は基本NG（クリーンブレイク）

### ステップ4: 動作確認（🔴 必須）

```bash
# 1. 構文チェック
python3 -m py_compile <変更したファイル>

# 2. インポートテスト
python3 -c "from mao.ui.widgets import CTOChatWidget; print('✅ Import OK')"

# 3. 実行テスト
mao start "簡単なテストタスク"

# 4. ログ確認
tail -f .mao/logs/*.log
```

詳細は **[DEVELOPMENT_RULES.md](./DEVELOPMENT_RULES.md)** 参照。

### ステップ5: ドキュメント更新

変更に応じて以下を更新：
- `CHANGELOG.md`: 変更履歴を追記
- 関連する技術ドキュメント（必要に応じて）
- コード内のdocstring/コメント

---

## 🔴 絶対に守るべきルール

### 1. 改修時は必ず動作確認を実施

**構文チェックだけではNG** - 実際に `mao start` で動作確認すること。

詳細: [DEVELOPMENT_RULES.md#1-改修時は必ず動作確認を実施する](./DEVELOPMENT_RULES.md#1-改修時は必ず動作確認を実施する)

### 2. 後方互換性は基本的にNG（クリーンブレイク原則）

```python
# ✅ 良い例: クリーンブレイク
elif msg.role == "cto":
    self.cto_chat_panel.chat_widget.add_cto_message(msg.content)

# ❌ 悪い例: 後方互換性サポート（禁止）
elif msg.role == "cto" or msg.role == "manager":  # ← NG
    self.cto_chat_panel.chat_widget.add_cto_message(msg.content)
```

**理由**:
- 古い形式のサポートコードが残るとコードが複雑化
- バグの温床になる
- 技術的負債が蓄積

詳細: [DEVELOPMENT_RULES.md#4-後方互換性は基本的にngクリーンブレイク原則](./DEVELOPMENT_RULES.md#4-後方互換性は基本的にngクリーンブレイク原則)

### 3. 段階的な変更を心がける

大規模変更は以下のように段階的に：
1. Phase 1: ファイル名変更
2. Phase 2: クラス名・変数名変更
3. Phase 3: 各ファイル統合
4. Phase 4: 動作確認
5. Phase 5: ドキュメント更新

**各フェーズ後に必ず動作確認**すること。

---

## 📚 ドキュメント構造

MAOのドキュメントは以下のように整理されています：

### ルートレベル（プロジェクトルート）

**開発ルール・ガイド**:
- `CLAUDE.md` - このファイル（Claude Code向け開発ガイド）
- `DEVELOPMENT_RULES.md` - 開発時の必須ルール
- `README.md` - プロジェクト概要

**変更記録**:
- `CHANGELOG.md` - バージョン履歴
- `MANAGER_CTO_UNIFICATION.md` - Manager→CTO統一の記録
- `TMUX_INTEGRATION_IMPLEMENTATION.md` - tmux統合実装記録
- `IMPLEMENTATION_AUDIT.md` - 実装監査記録

### /docs/ サブディレクトリ

**アーキテクチャ・設計**:
- `docs/ARCHITECTURE.md` - システム全体のアーキテクチャ
- `docs/WORKFLOW.md` - エージェントワークフロー
- `docs/CLAUDE_CODE_INTEGRATION.md` - Claude Code統合の詳細

**品質・テスト**:
- `docs/QUALITY.md` - 品質基準（存在する場合）
- `docs/TESTING.md` - テスト戦略（存在する場合）

**その他**:
- `docs/README.md` - ドキュメントインデックス

### /mao/agents/ ディレクトリ

**エージェントプロンプト** (各ロールの指示書):
- `mao/agents/cto_prompt.md` - CTO（Chief Technology Officer）
- `mao/agents/developer_prompt.md` - 開発者エージェント
- `mao/agents/tester_prompt.md` - テストエージェント
- ... など

---

## 🔍 ドキュメントの読み方

### タスク別: どのドキュメントを読むべきか

#### 1. 新しいセッションを開始する時
```
1. CLAUDE.md（このファイル） - 全体像を把握
2. DEVELOPMENT_RULES.md - ルール確認
3. docs/ARCHITECTURE.md - アーキテクチャ理解
```

#### 2. UI関連の変更
```
1. docs/ARCHITECTURE.md - UIコンポーネント構造
2. mao/ui/ ディレクトリ内のコードを読む
3. Textual公式ドキュメント（外部）
```

#### 3. エージェント動作の変更
```
1. docs/WORKFLOW.md - エージェントワークフロー
2. mao/agents/<role>_prompt.md - 該当ロールのプロンプト
3. mao/orchestrator/ ディレクトリのコード
```

#### 4. tmux統合の変更
```
1. TMUX_INTEGRATION_IMPLEMENTATION.md - 実装詳細
2. mao/orchestrator/tmux_manager.py - コード本体
3. docs/ARCHITECTURE.md - 全体での位置づけ
```

#### 5. 大規模なリファクタリング
```
1. DEVELOPMENT_RULES.md - クリーンブレイク原則
2. 過去の変更記録（MANAGER_CTO_UNIFICATION.md など）- パターン参考
3. 影響範囲の調査（grep検索）
```

---

## 💡 便利なコマンド

### ドキュメント検索

```bash
# ドキュメント内のキーワード検索
grep -r "キーワード" . --include="*.md" -n

# 特定トピックのドキュメント一覧
ls -lh docs/*.md
ls -lh *.md
```

### コード検索

```bash
# クラス定義を検索
grep -r "class ClassName" mao/ --include="*.py" -n

# 関数定義を検索
grep -r "def function_name" mao/ --include="*.py" -n

# 文字列の使用箇所を検索
grep -r "\"string\"" mao/ --include="*.py" -n
```

### 構造確認

```bash
# ディレクトリ構造を表示
tree mao/ -L 2

# Pythonファイル一覧
find mao -name "*.py" -type f

# ドキュメント一覧
find . -name "*.md" -type f
```

---

## 🚀 クイックスタート

新しいMAOタスクを開始する際の最速手順：

1. **このファイル（CLAUDE.md）を読む** ← 今ここ
2. **DEVELOPMENT_RULES.mdを読む** - 必須ルール確認
3. **タスク関連のドキュメントを読む** - 上記「タスク別」参照
4. **影響範囲を調査** - grep検索
5. **段階的に実装** - Phase 1, 2, 3...
6. **各フェーズ後に動作確認** - 🔴 必須
7. **ドキュメント更新** - CHANGELOG.md等
8. **コミット**

---

## 📖 さらに詳しく知りたい場合

- **システム全体**: [docs/README.md](./docs/README.md)
- **アーキテクチャ**: [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- **Claude Code統合**: [docs/CLAUDE_CODE_INTEGRATION.md](./docs/CLAUDE_CODE_INTEGRATION.md)
- **開発ルール詳細**: [DEVELOPMENT_RULES.md](./DEVELOPMENT_RULES.md)

---

## ✅ チェックリスト（改修前）

改修を開始する前に、以下を確認：

- [ ] DEVELOPMENT_RULES.mdを読んだ
- [ ] タスク関連のドキュメントを読んだ
- [ ] 影響範囲を調査した（grep検索）
- [ ] 段階的な変更計画を立てた
- [ ] 動作確認の方法を理解した

---

**Happy coding! 🚀**
