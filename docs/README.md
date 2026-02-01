# MAO Documentation

## ドキュメント一覧

### ユーザー向け
- [QUICKSTART.md](../QUICKSTART.md) - 1分で始めるガイド
- [USAGE.md](../USAGE.md) - 詳細な使い方
- [FAQ.md](FAQ.md) - よくある質問（作成予定）

### 開発者向け
- [DASHBOARD_SPECIFICATION.md](DASHBOARD_SPECIFICATION.md) - **ダッシュボード設計書**
- [DASHBOARD_DESIGN.md](../DASHBOARD_DESIGN.md) - デザイン案
- [ARCHITECTURE.md](ARCHITECTURE.md) - システム設計（作成予定）
- [API.md](API.md) - API仕様（作成予定）

### テスト
- [TESTING.md](TESTING.md) - テストガイド（作成予定）
- [TEST_RESULTS.md](../TEST_RESULTS.md) - テスト結果

## ドキュメント更新ガイド

### ダッシュボード設計書の更新

設計変更時は必ず `DASHBOARD_SPECIFICATION.md` を更新：

```bash
# 設計書を編集
vim docs/DASHBOARD_SPECIFICATION.md

# 変更履歴セクションに記録
# バージョン番号を更新
```

### 変更履歴フォーマット

```markdown
### vX.Y - YYYY-MM-DD
- [x] 完了した変更
- [ ] 予定の変更
```

## ドキュメント原則

1. **常に最新を保つ** - コード変更時にドキュメントも更新
2. **明確に書く** - 誰が読んでもわかるように
3. **例を示す** - コードサンプルやスクリーンショット
4. **履歴を残す** - 変更理由も記録

## 貢献

ドキュメントの改善提案は Issue または PR で歓迎します！
