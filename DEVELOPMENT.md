# Development Guide

MAO の開発環境セットアップガイド

## 🚀 クイックスタート

### 前提条件

- [mise](https://mise.jdx.dev/) がインストール済み

```bash
# mise のインストール
curl https://mise.run | sh

# または Homebrew
brew install mise

# シェル設定に追加
echo 'eval "$(mise activate bash)"' >> ~/.bashrc  # or ~/.zshrc for zsh
source ~/.bashrc
```

### セットアップ

```bash
# 開発環境を一括セットアップ
./scripts/setup_dev.sh
```

これで以下が自動実行されます：
1. Python 3.11 のインストール
2. 仮想環境 (`.venv`) の作成
3. 依存パッケージのインストール
4. pre-commit フックのインストール
5. 初回コード品質チェック

## 📋 mise コマンド

### ツール管理

```bash
# ツールバージョン確認
mise list

# ツールインストール
mise install

# Python バージョン確認
mise current python
```

### タスク実行

```bash
# コード品質チェック
mise run quality

# 自動修正付きチェック
mise run quality-fix

# テスト実行
mise run test

# 個別実行
mise run lint        # Linter のみ
mise run format      # Formatter のみ
mise run typecheck   # Type checker のみ

# 利用可能なタスク一覧
mise tasks
```

## 🛠️ 開発ワークフロー

### 1. ブランチ作成

```bash
git checkout -b feature/your-feature
```

### 2. コード変更

```bash
# お好きなエディタで編集
vim mao/your_file.py
```

### 3. コード品質チェック

```bash
# 自動修正付きチェック（推奨）
mise run quality-fix

# または Makefile
make quality-fix
```

### 4. テスト実行

```bash
mise run test

# または
make test
```

### 5. コミット

```bash
git add .
git commit -m "Add your feature"
# → pre-commit フックが自動実行
```

### 6. プッシュ

```bash
git push origin feature/your-feature
```

## 🎯 mise の利点

### 従来の方法との比較

**従来:**
```bash
# バージョン管理が煩雑
pyenv install 3.11
pyenv local 3.11
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**mise:**
```bash
# すべて自動
cd mao/
# → mise が自動的に Python 3.11 をインストール＆仮想環境を作成
mise run install
```

### 主な利点

1. **バージョン統一** - チーム全員が同じツールバージョンを使用
2. **自動切り替え** - ディレクトリに入るだけで環境が切り替わる
3. **シンプル** - `.mise.toml` 1つで管理
4. **高速** - Rust 製で爆速
5. **タスクランナー** - よく使うコマンドを定義可能

## 📝 mise 設定ファイル

### .mise.toml

```toml
[tools]
python = "3.11"  # Python バージョン固定

[env]
_.python.venv = { path = ".venv", create = true }  # 自動仮想環境

[tasks.quality]
run = "make quality"  # タスク定義
```

### カスタマイズ

プロジェクト固有の設定を追加：

```bash
# ローカル設定追加（Git にコミットしない）
mise set KEY=VALUE

# タスク追加
mise task add my-task "echo 'Hello'"
```

## 🔧 トラブルシューティング

### mise が見つからない

```bash
# インストール確認
which mise

# シェル設定確認
cat ~/.bashrc | grep mise  # or ~/.zshrc

# 再読み込み
source ~/.bashrc
```

### Python が古いバージョン

```bash
# mise の Python を使用
mise which python

# システムの Python と混同しないよう確認
python --version  # mise 管理下なら 3.11.x
```

### 仮想環境が作られない

```bash
# 手動作成
mise run install

# または
cd mao/
mise install
pip install -e ".[dev]"
```

### pre-commit が動かない

```bash
# 再インストール
mise run pre-commit-install

# または
pre-commit uninstall
pre-commit install
```

## 🎨 エディタ統合

### VS Code

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "ruff.path": ["${workspaceFolder}/.venv/bin/ruff"],
  "python.analysis.typeCheckingMode": "basic"
}
```

### PyCharm

1. Settings → Project → Python Interpreter
2. Add Interpreter → Existing environment
3. Select `.venv/bin/python`

## 📚 参考リンク

- [mise Documentation](https://mise.jdx.dev/)
- [mise Tasks](https://mise.jdx.dev/tasks/)
- [Ruff](https://docs.astral.sh/ruff/)
- [Pyright](https://github.com/microsoft/pyright)
