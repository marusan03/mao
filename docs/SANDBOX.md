# Docker Sandbox Mode

MAOをDocker Sandbox内で実行し、ホストシステムを保護します。

## 概要

Docker AI Sandboxesは、軽量なMicroVM内でMAOを実行します。これにより：

- ホストシステムのファイルやプロセスが保護される
- エージェントの操作がサンドボックス内に隔離される
- プロジェクトファイルは自動的にホストと同期される

## 要件

- **Docker Desktop** (macOS/Windows) または **Docker Desktop 4.57+** (Linux)
- Docker DesktopでAI Sandboxes機能の有効化
- インターネット接続（初回のイメージダウンロード用）

### Docker Desktopのセットアップ

1. Docker Desktopをインストール
2. Settings → Features in development → AI Sandboxes を有効化
3. Docker Desktopを再起動

## 使用方法

### テンプレートのビルド（初回のみ）

MAOがプリインストールされたカスタムテンプレートをビルドします：

```bash
mao sandbox build
```

これにより、サンドボックスの起動が高速化されます。

### サンドボックス内でMAOを起動

```bash
# 現在のディレクトリで起動
mao sandbox start "認証システムを実装"

# 特定のプロジェクトで起動
mao sandbox start -p ~/projects/myapp "テストを追加"

# モデルを指定
mao sandbox start --model opus "アーキテクチャをレビュー"
```

### 既存サンドボックスに再接続

```bash
mao sandbox attach

# 別のプロジェクトのサンドボックス
mao sandbox attach -p ~/projects/myapp
```

### サンドボックスの状態確認

```bash
# 現在のプロジェクトのステータス
mao sandbox status

# すべてのMAOサンドボックス一覧
mao sandbox ls
```

### サンドボックスを削除

```bash
mao sandbox rm

# 強制削除
mao sandbox rm --force
```

## 動作の仕組み

```
ホスト
  └─ Docker Sandbox (MicroVM)
       └─ MAO tmuxセッション
            ├─ CTO (pane 0)
            ├─ Agent-1 (pane 1) → worktree-1/
            ├─ Agent-2 (pane 2) → worktree-2/
            └─ ...
```

1. `docker sandbox run` でMicroVMを起動
2. プロジェクトディレクトリがサンドボックス内に同期
3. サンドボックス内でMAO（tmux + Claude Code）が動作
4. ファイル変更はホストに自動同期

## アーキテクチャ上の選択

MAOでは**プロジェクト単位サンドボックス**を採用しています：

- git worktreeで各エージェントは既にファイルレベルで隔離済み
- サンドボックスの目的はホストシステムの保護
- リソース効率が良い（1つのMicroVMで全エージェント実行）

個別エージェントごとのサンドボックスは不要です。

## カスタムテンプレート

MAOはカスタムDockerテンプレートを使用します：

```dockerfile
FROM docker/sandbox-templates:claude-code

# MAOをインストール
RUN pip install git+https://github.com/marusan03/mao.git

# 必要なツールを確認
RUN which tmux && which claude && which mao
```

テンプレートは `mao/docker/Dockerfile.mao-sandbox` にあります。

## コマンドリファレンス

| コマンド | 説明 |
|---------|------|
| `mao sandbox start [PROMPT]` | サンドボックス内でMAOを起動 |
| `mao sandbox attach` | 既存サンドボックスに再接続 |
| `mao sandbox rm` | サンドボックスを削除 |
| `mao sandbox ls` | すべてのMAOサンドボックスを表示 |
| `mao sandbox build` | MAOテンプレートをビルド |
| `mao sandbox status` | サンドボックスの状態を表示 |

## 制限事項

- **macOS/Windows推奨**: Linux版Docker DesktopはAI Sandboxes対応が限定的
- **初回起動時間**: 初回はイメージダウンロードに時間がかかる
- **ネットワーク制限**: サンドボックス内からホストのlocalhostサービスにはアクセス不可
- **リソース使用**: MicroVMが追加のメモリとCPUを使用

## トラブルシューティング

### "Docker Sandbox is not available"

Docker Desktopがインストールされ、AI Sandboxes機能が有効になっているか確認：

```bash
docker sandbox --help
```

### テンプレートのビルドに失敗

Docker Desktopが起動しているか確認し、ネットワーク接続を確認：

```bash
docker images
mao sandbox build
```

### サンドボックスが起動しない

既存のサンドボックスが残っている可能性があります：

```bash
mao sandbox ls
mao sandbox rm --force
mao sandbox start "タスク"
```

## 参考リンク

- [Docker AI Sandboxes](https://docs.docker.com/ai/sandboxes/)
- [docker sandbox run](https://docs.docker.com/reference/cli/docker/sandbox/run/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
