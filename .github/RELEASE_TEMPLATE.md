# MAO v{VERSION}

Multi-Agent Orchestrator の新しいバージョンがリリースされました。

## 📝 変更内容

{CHANGELOG}

## 📦 インストール

### 新規インストール

```bash
curl -fsSL https://raw.githubusercontent.com/marusan03/mao/main/install.sh | sh
```

### アップデート

既存のインストールをアップデート:

```bash
mao update
```

または特定のバージョンを指定:

```bash
MAO_VERSION=v{VERSION} curl -fsSL https://raw.githubusercontent.com/marusan03/mao/main/install.sh | sh
```

## 📋 必要要件

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- tmux (optional, for agent monitoring)
- Redis (optional, for distributed state)

## 📚 ドキュメント

- [README](https://github.com/marusan03/mao#readme)
- [CHANGELOG](https://github.com/marusan03/mao/blob/main/CHANGELOG.md)
- [リリース手順](https://github.com/marusan03/mao/blob/main/RELEASING.md)

## 🔗 リンク

- [GitHub Repository](https://github.com/marusan03/mao)
- [Issues](https://github.com/marusan03/mao/issues)
- [Previous Releases](https://github.com/marusan03/mao/releases)

---

**Full Changelog**: https://github.com/marusan03/mao/compare/v{PREV_VERSION}...v{VERSION}
