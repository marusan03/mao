# Code Quality Guide

MAO プロジェクトのコード品質管理ガイド

> **重要**: コーディング規約については [CODING_STANDARDS.md](./CODING_STANDARDS.md) を参照してください。
> - Pydantic と Enum の使用
> - dict の禁止
> - ミュータブルなデフォルト引数の完全禁止

## 🛠️ 使用ツール

### Ruff（Linter & Formatter）

高速な Python linter およびフォーマッター。以下をチェック：

- **コードスタイル** - PEP 8 準拠
- **潜在的バグ** - 未使用変数、未定義名など
- **コード簡素化** - より良い書き方の提案
- **Import の整理** - isort 互換
- **型チェックの改善** - type-checking 関連

### Pyright（Type Checker）

Microsoft 製の高速型チェッカー。以下をチェック：

- **型の整合性** - 型アノテーションの正しさ
- **未使用コード** - 使われていない import/変数/関数
- **Null 安全性** - Optional 型の適切な処理

## 🚀 使い方

### 推奨: mise（最も簡単）

```bash
# 初回セットアップ
./scripts/setup_dev.sh

# 以降は mise タスクで実行
mise run quality          # すべてのチェック
mise run quality-fix      # 自動修正付き
mise run lint            # lint のみ
mise run format          # フォーマットのみ
mise run typecheck       # 型チェックのみ
mise run test            # テスト実行

# 利用可能なタスク一覧
mise tasks
```

詳細: [DEVELOPMENT.md](../DEVELOPMENT.md)

### 方法1: Makefile

```bash
# すべてのチェックを実行
make quality

# 自動修正付きですべてのチェックを実行
make quality-fix

# 個別実行
make lint           # Ruff linter のみ
make format         # Ruff formatter チェックのみ
make format-fix     # Ruff formatter 修正適用
make typecheck      # Pyright のみ
```

### 方法2: スクリプト直接実行

```bash
# チェックのみ
./scripts/check_code_quality.sh

# 自動修正付き
./scripts/check_code_quality.sh --fix
```

### 方法3: スキルとして実行

```bash
# エージェントが使用
./mao/roles/skills/code_quality_check.sh
./mao/roles/skills/code_quality_check.sh --fix
```

### 方法4: 各ツール個別実行

```bash
# Ruff linter
ruff check mao/ tests/
ruff check --fix mao/ tests/  # 自動修正

# Ruff formatter
ruff format mao/ tests/

# Pyright
pyright mao/
```

## 🪝 Git フックで自動実行

### セットアップ

```bash
# pre-commit のインストールと設定
make pre-commit-install

# または手動で
pip install pre-commit
pre-commit install
```

### 動作

コミット時に自動的に以下が実行されます：

1. Ruff linter（自動修正可能なものは修正）
2. Ruff formatter
3. Pyright 型チェック
4. その他のチェック（trailing whitespace など）

エラーがある場合、コミットは中断されます。

### 手動実行

```bash
# すべてのファイルに対して実行
pre-commit run --all-files

# 特定のフックのみ実行
pre-commit run ruff --all-files
pre-commit run pyright --all-files
```

## ⚙️ 設定

### Ruff 設定（pyproject.toml）

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "N",      # pep8-naming
    "UP",     # pyupgrade
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "SIM",    # flake8-simplify
    "RUF",    # ruff-specific rules
]
```

### Pyright 設定（pyproject.toml）

```toml
[tool.pyright]
pythonVersion = "3.11"
typeCheckingMode = "basic"
reportMissingImports = true
reportUnusedImport = true
reportUnusedVariable = true
```

## 📝 開発ワークフロー

### 推奨フロー

1. **コードを書く**
   ```bash
   # 開発作業...
   ```

2. **品質チェック（自動修正）**
   ```bash
   make quality-fix
   ```

3. **テスト実行**
   ```bash
   make test
   ```

4. **コミット**
   ```bash
   git add .
   git commit -m "message"
   # → pre-commit フックが自動実行
   ```

5. **プッシュ/PR作成**

### エージェント向けワークフロー

エージェントがコードを生成した後：

```yaml
steps:
  1. コード生成
  2. make quality-fix を実行（自動修正）
  3. エラーが残っている場合は修正
  4. make test を実行
  5. すべて成功したらコミット
```

## 🔧 トラブルシューティング

### "command not found: ruff"

```bash
pip install ruff
```

### "command not found: pyright"

```bash
pip install pyright
```

### 多数のエラーが表示される

```bash
# 自動修正を試す
make quality-fix

# それでも残るエラーは手動で修正
```

### pre-commit が遅い

```bash
# 特定のファイルのみチェック
git commit -m "message" -- path/to/file.py

# または一時的にスキップ（非推奨）
git commit --no-verify -m "message"
```

## 📊 CI/CD 統合

GitHub Actions で自動実行する例：

```yaml
name: Code Quality
on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install ruff pyright
      - name: Run quality checks
        run: make quality
```

## 🎯 目標

- **一貫性**: すべてのコードが同じスタイル
- **品質**: バグの早期発見
- **保守性**: 型安全で読みやすいコード
- **効率**: 自動化でレビュー時間短縮

## 📚 参考資料

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pyright Documentation](https://github.com/microsoft/pyright)
- [Pre-commit Documentation](https://pre-commit.com/)
