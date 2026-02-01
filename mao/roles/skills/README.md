# MAO Skills

汎用的なスキル定義ディレクトリ。エージェントが再利用できる共通タスクを定義します。

## 利用可能なスキル

### code_quality_check

コード品質チェックを実行するスキル。

**機能:**
- Ruff による lint チェック（コードスタイル、潜在的バグ検出）
- Ruff によるフォーマットチェック
- Pyright による型チェック

**使い方:**

```bash
# 手動実行（読み取り専用）
./mao/roles/skills/code_quality_check.sh

# 自動修正付き
./mao/roles/skills/code_quality_check.sh --fix

# または Makefile を使用
make quality          # チェックのみ
make quality-fix      # 自動修正付き
```

**エージェント向け:**

エージェントはこのスキルを以下の場面で使用すべき：
1. コードを書いた後
2. コミット前
3. プルリクエスト作成前
4. コードレビュー前

## スキルの追加方法

新しいスキルを追加する場合：

1. **YAML定義を作成** (`skill_name.yaml`)
   ```yaml
   name: skill_name
   description: "スキルの説明"
   execution:
     type: script
     command: ./path/to/script.sh
   ```

2. **実行スクリプトを作成** (`skill_name.sh`)
   ```bash
   #!/usr/bin/env bash
   # スキルの実装
   ```

3. **実行権限を付与**
   ```bash
   chmod +x mao/roles/skills/skill_name.sh
   ```

4. **ドキュメントに追加**
   - このREADMEに使用例を記載
   - 必要に応じてテストを作成

## ベストプラクティス

- スキルは **単一責任** とする（1つのスキル = 1つの明確なタスク）
- エラーハンドリングを適切に行う
- 実行結果を明確に表示（成功/失敗がわかりやすく）
- 前提条件（必要なツール等）を明記
- 使用例を複数用意
