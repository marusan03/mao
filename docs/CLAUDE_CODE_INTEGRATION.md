# Claude Code CLI Integration

MAOは複数のClaude Codeインスタンスを並列実行できます。

## セットアップ

### 1. Claude Code のインストール

https://claude.ai/download から Claude Code をインストールしてください。

### 2. コマンドの確認

以下のコマンドが利用可能か確認：

```bash
claude-code --version
# または
claude --version
```

## 動作方式

### エージェント起動時の処理

1. エージェントごとに専用の作業ディレクトリを作成
   - `.mao/agents/<agent-id>/`

2. プロンプトをファイルに保存
   - `prompt.txt`

3. Claude Code CLIを起動
   - 作業ディレクトリで実行
   - プロンプトを標準入力から渡す

4. 実行結果を取得
   - 標準出力から応答を読み取り

### 並列実行

複数のエージェントは独立したプロセスとして実行されます：

```
Dashboard
├── Agent 1 (claude-code) → .mao/agents/planner-xxx/
├── Agent 2 (claude-code) → .mao/agents/coder-yyy/
└── Agent 3 (claude-code) → .mao/agents/reviewer-zzz/
```

各エージェントは：
- 独自の作業ディレクトリを持つ
- 独立したClaude Codeプロセスで実行
- tmuxペインで個別に監視可能

## 制限事項

### 現在の制限

1. **対話的実行**
   - Claude Code CLIは対話的なツール
   - 完全な自動化は難しい場合がある

2. **トークン使用量**
   - CLIからは正確なトークン数を取得できない
   - 概算値を使用（文字数÷4）

3. **ストリーミング**
   - CLIはストリーミングをサポートしていない
   - 実行完了後に一括で結果を返す

### 将来の改善

- Claude Code APIが公開されたらより良い統合が可能
- 現在は実験的な実装

## トラブルシューティング

### コマンドが見つからない

```
ValueError: claude-code command not found
```

→ Claude Code をインストールして、PATHに追加してください

### 実行エラー

ダッシュボードのログを確認：
- `.mao/logs/<agent-id>.log`

作業ディレクトリを確認：
- `.mao/agents/<agent-id>/`

### デバッグモード

ログファイルで詳細を確認：

```bash
tail -f .mao/logs/planner-*.log
```

## フォールバック

Claude Code CLIが利用できない場合、MAOは自動的にAnthropic APIにフォールバックします。

優先順位：
1. Claude Code CLI（推奨）
2. Anthropic API（ANTHROPIC_API_KEY必要）
3. ダッシュボードのみ（エージェント実行無効）
