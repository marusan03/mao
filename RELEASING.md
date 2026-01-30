# リリース手順

MAO の新しいバージョンをリリースする手順です。

## バージョン番号の決定

[Semantic Versioning](https://semver.org/) に従います：

- **MAJOR** (X.0.0): 互換性のない API 変更
- **MINOR** (0.X.0): 後方互換性のある機能追加
- **PATCH** (0.0.X): 後方互換性のあるバグ修正

## リリース手順

### 1. バージョン番号を更新

`pyproject.toml` のバージョンを更新：

```toml
[project]
version = "0.2.0"  # 新しいバージョン番号
```

### 2. CHANGELOG.md を更新

`CHANGELOG.md` の Unreleased セクションを新バージョンに変更：

```markdown
## [0.2.0] - 2025-02-01

### Added
- 新機能の説明

### Changed
- 変更の説明

### Fixed
- 修正の説明
```

### 3. コミットとタグ

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "Release v0.2.0"
git tag v0.2.0
git push origin main
git push origin v0.2.0
```

### 4. GitHub Release の作成（オプション）

GitHub の Releases ページで新しいリリースを作成：

1. https://github.com/marusan03/mao/releases/new にアクセス
2. タグを選択: `v0.2.0`
3. リリースタイトル: `MAO v0.2.0`
4. CHANGELOG.md の内容をコピーして説明に貼り付け
5. "Publish release" をクリック

## ユーザーへのアップデート提供

ユーザーは以下のコマンドでアップデートできます：

```bash
mao update
```

このコマンドは：
- GitHub から最新版を取得
- 依存関係を再インストール
- 新しいバージョンを表示

## 開発版とリリース版

- **main ブランチ**: 開発版（常に最新の変更を含む）
- **タグ付きリリース**: 安定版（テスト済み）

ユーザーは main ブランチを使用して最新の機能を試すことができます。
安定版が必要な場合は、特定のバージョンタグを指定してインストールします：

```bash
MAO_VERSION=v0.1.0 curl -fsSL https://raw.githubusercontent.com/marusan03/mao/main/install.sh | sh
```
