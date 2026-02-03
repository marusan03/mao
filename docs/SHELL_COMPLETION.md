# シェル補完 - Shell Completion

MAO CLIは、bash、zsh、fishでのコマンド補完（オートコンプリート）をサポートしています。

## 🚀 クイックスタート

### 自動インストール

```bash
# 現在のシェルを自動検出してインストール
mao completion --install
```

### 手動インストール

#### Bash

```bash
# ~/.bashrc に追加
echo 'eval "$(_MAO_COMPLETE=bash_source mao)"' >> ~/.bashrc

# リロード
source ~/.bashrc
```

または、補完ファイルを生成：

```bash
# 補完ファイルを生成
_MAO_COMPLETE=bash_source mao > ~/.local/share/bash-completion/completions/mao

# リロード
source ~/.local/share/bash-completion/completions/mao
```

#### Zsh

```bash
# ~/.zshrc に追加
echo 'eval "$(_MAO_COMPLETE=zsh_source mao)"' >> ~/.zshrc

# リロード
source ~/.zshrc
```

#### Fish

```bash
# 補完ファイルを生成
_MAO_COMPLETE=fish_source mao > ~/.config/fish/completions/mao.fish

# 新しいシェルで自動的に有効化
```

## 📋 補完される項目

### 1. コマンド補完

```bash
mao <TAB>
# → init, start, stop, status, feedback, completion, version など
```

### 2. サブコマンド補完

```bash
mao feedback <TAB>
# → list, show, improve, send
```

### 3. フィードバックID補完

```bash
mao feedback improve <TAB>
# → 736_8938017d  [AgentLoggerのバッファリング問題... [open]]
# → 025_cb28a15a  [エージェント間通信の最適化検討 [open]]
```

タイトルとステータスも表示されるので、どのフィードバックか一目瞭然！

### 4. ロール補完

```bash
mao start --role <TAB>
# → general  [Role: general]
# → planner  [Role: planner]
# → coder    [Role: coder]
# → cto      [Role: cto]
```

### 5. モデル補完

```bash
mao start --model <TAB>
# → opus    [Claude Opus 4.5 - Most powerful]
# → sonnet  [Claude Sonnet 4.5 - Balanced (default)]
# → haiku   [Claude Haiku 3.5 - Fast and efficient]
```

### 6. オプション補完

```bash
mao start --<TAB>
# → --role        (初期タスクのロール)
# → --model       (使用するモデル)
# → --tmux        (tmux有効化)
# → --no-tmux     (tmux無効化)
# → --redis-url   (Redis URL)
# → --no-redis    (SQLite使用)
# → --session     (セッション継続)
# → --new-session (新規セッション作成)
```

## 🔧 高度な使用法

### 補完スクリプトの確認

```bash
# 補完スクリプトを表示（インストールせずに）
mao completion bash
mao completion zsh
mao completion fish
```

### 特定のシェル用にインストール

```bash
# 現在bashを使っているが、zsh用にもインストールしたい場合
mao completion zsh --install
```

### トラブルシューティング

#### 補完が動作しない場合

1. **シェルをリロード**
   ```bash
   # bash/zsh
   source ~/.bashrc  # または ~/.zshrc

   # fish
   # 新しいシェルを開く
   ```

2. **補完スクリプトが読み込まれているか確認**
   ```bash
   # bash
   type _mao_completion

   # zsh
   which _mao

   # fish
   complete -c mao
   ```

3. **手動で再インストール**
   ```bash
   mao completion --install
   ```

## 📝 補完の仕組み

### 動的補完

MAOの補完は**動的**です。つまり：

- **フィードバックID**: `.mao/feedback/index.json` から実際のフィードバックを読み込み
- **ロール**: `mao/roles/` ディレクトリから利用可能なロールを検出
- **モデル**: 最新のモデルリストを提供

キャッシュではなくリアルタイムで補完候補を生成します。

### 補完関数

`mao/cli_completion.py` に補完ロジックが実装されています：

- `complete_feedback_ids()`: フィードバックID補完
- `complete_roles()`: ロール補完
- `complete_models()`: モデル補完
- `complete_session_ids()`: セッションID補完
- `complete_agent_ids()`: エージェントID補完

### カスタム補完の実装

カスタム補完が必要なパラメータには `shell_complete` を指定:

```python
@click.option(
    "--role",
    shell_complete=complete_roles,  # カスタム補完関数
    help="Agent role"
)
```

補完関数は `(value, help_text)` のタプルを返します:

```python
def complete_roles(ctx, param, incomplete):
    """ロール名を補完"""
    roles = list_available_roles()
    return [
        (role.name, role.description)
        for role in roles
        if role.name.startswith(incomplete)
    ]
```

## 🎯 ベストプラクティス

### 効率的な使い方

1. **コマンドの発見**
   ```bash
   mao <TAB><TAB>
   # 利用可能な全コマンドを表示
   ```

2. **オプションの確認**
   ```bash
   mao start --<TAB><TAB>
   # 利用可能な全オプションを表示
   ```

3. **フィードバックの選択**
   ```bash
   mao feedback improve <TAB>
   # タイトルを見ながら選択
   ```

### エイリアスとの組み合わせ

```bash
# ~/.bashrc または ~/.zshrc
alias mf='mao feedback'
alias mfi='mao feedback improve'
alias mfl='mao feedback list'

# 補完も動作
mfi <TAB>  # フィードバックID補完
```

## 🐛 既知の問題

### Python仮想環境

Python仮想環境（venv）を使用している場合、補完が動作しないことがあります。

**解決策:**

仮想環境をアクティブにした状態で補完をインストール：

```bash
source .venv/bin/activate
mao completion --install
```

### Clickバージョン

Click 8.0以降が必要です。古いバージョンでは補完が動作しません。

```bash
# Clickバージョン確認
python -c "import click; print(click.__version__)"

# アップグレード
pip install --upgrade click
```

## 📚 参考

- [Click Shell Completion](https://click.palletsprojects.com/en/8.1.x/shell-completion/)
- [Bash Completion](https://github.com/scop/bash-completion)
- [Zsh Completion System](https://zsh.sourceforge.io/Doc/Release/Completion-System.html)
- [Fish Completion](https://fishshell.com/docs/current/completions.html)
