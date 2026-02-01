# Tab Completion Setup Guide

MAOのCLIコマンドでタブ補完を有効にする方法です。

## Bash の場合

1. `~/.bashrc` に以下を追加:

```bash
eval "$(_MAO_COMPLETE=bash_source mao)"
```

2. 設定を再読み込み:

```bash
source ~/.bashrc
```

## Zsh の場合

1. `~/.zshrc` に以下を追加:

```bash
eval "$(_MAO_COMPLETE=zsh_source mao)"
```

2. 設定を再読み込み:

```bash
source ~/.zshrc
```

## Fish の場合

1. `~/.config/fish/completions/mao.fish` を作成:

```bash
_MAO_COMPLETE=fish_source mao | source
```

2. Fishを再起動:

```bash
exec fish
```

## 動作確認

設定後、以下のコマンドでタブ補完が動作することを確認:

```bash
mao <TAB>           # サブコマンド一覧
mao feedback <TAB>  # feedbackサブコマンド一覧
mao feedback improve <TAB>  # フィードバックIDとタイトルのプレビュー
mao start --role <TAB>      # 利用可能なロール一覧
mao start --model <TAB>     # モデル一覧と説明
```

## 補完の仕組み

MAOは[Click](https://click.palletsprojects.com/)フレームワークの補完機能を使用しています。

- **動的補完**: フィードバックID、ロール、モデルなどは実行時に動的に生成されます
- **ヘルプテキスト**: 補完候補には説明文が表示されます（シェルによる）
- **カスタム補完関数**: `mao/cli_completion.py` で各パラメータの補完ロジックを定義

## 補完の実装

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

## トラブルシューティング

### 補完が動作しない

1. 設定を再読み込みしたか確認:
   ```bash
   source ~/.bashrc  # または ~/.zshrc
   ```

2. MAOがインストールされているか確認:
   ```bash
   which mao
   ```

3. 環境変数が正しく設定されているか確認:
   ```bash
   echo $_MAO_COMPLETE
   ```

### 一部のコマンドで補完が効かない

- 動的補完の場合、プロジェクトディレクトリ内で実行する必要があります
- `.mao/` ディレクトリが存在することを確認してください

## 参考資料

- [Click Shell Completion](https://click.palletsprojects.com/en/8.1.x/shell-completion/)
- `mao/cli_completion.py` - 補完関数の実装
- `mao/cli.py` - コマンド定義と補完の統合
