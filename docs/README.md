# MAO Documentation

## ドキュメント一覧

### 概要・設計

| ファイル | 内容 |
|---------|------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | システムアーキテクチャ |
| [WORKFLOW.md](./WORKFLOW.md) | エージェントワークフロー |
| [CTO_ARCHITECTURE.md](./CTO_ARCHITECTURE.md) | CTO設計詳細 |
| [TMUX_ARCHITECTURE.md](./TMUX_ARCHITECTURE.md) | tmux統合設計 |

### 機能ガイド

| ファイル | 内容 |
|---------|------|
| [INTERACTIVE_MODE.md](./INTERACTIVE_MODE.md) | インタラクティブモード |
| [SANDBOX.md](./SANDBOX.md) | Docker Sandboxモード |
| [API.md](./API.md) | API仕様 |
| [SHELL_COMPLETION.md](./SHELL_COMPLETION.md) | シェル補完設定 |
| [REALTIME_LOGGING.md](./REALTIME_LOGGING.md) | リアルタイムログ |
| [WORKTREE_ISOLATION.md](./WORKTREE_ISOLATION.md) | Worktree分離 |

### 開発者向け

| ファイル | 内容 |
|---------|------|
| [CLAUDE_CODE_INTEGRATION.md](./CLAUDE_CODE_INTEGRATION.md) | Claude Code統合 |
| [DASHBOARD_SPECIFICATION.md](./DASHBOARD_SPECIFICATION.md) | ダッシュボード設計書 |
| [CODE_QUALITY.md](./CODE_QUALITY.md) | 品質基準 |
| [CODING_STANDARDS.md](./CODING_STANDARDS.md) | コーディング規約 |

### ルートレベル（プロジェクトルート）

| ファイル | 内容 |
|---------|------|
| [README.md](../README.md) | プロジェクト概要 |
| [CLAUDE.md](../CLAUDE.md) | Claude Code向け開発ガイド |
| [CHANGELOG.md](../CHANGELOG.md) | 変更履歴 |
| [DEVELOPMENT.md](../DEVELOPMENT.md) | 開発環境セットアップ |
| [DEVELOPMENT_RULES.md](../DEVELOPMENT_RULES.md) | 開発ルール |
| [RELEASING.md](../RELEASING.md) | リリース手順 |

## ドキュメント更新ガイド

### 変更時の原則

1. **常に最新を保つ** - コード変更時にドキュメントも更新
2. **明確に書く** - 誰が読んでもわかるように
3. **例を示す** - コードサンプルやスクリーンショット
4. **履歴を残す** - 変更理由も記録

### 変更履歴フォーマット

```markdown
### vX.Y - YYYY-MM-DD
- [x] 完了した変更
- [ ] 予定の変更
```

## 貢献

ドキュメントの改善提案は Issue または PR で歓迎します。
