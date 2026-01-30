#!/usr/bin/env python3
"""
リリースノート生成スクリプト

Usage:
    python scripts/generate_release_notes.py v0.2.0

CHANGELOG.md から該当バージョンのエントリを抽出して、
GitHub Release 用のリリースノートを生成します。
"""
import sys
import re
from pathlib import Path


def extract_version_from_changelog(changelog_path: Path, version: str) -> str:
    """CHANGELOG.md から特定バージョンのエントリを抽出

    Args:
        changelog_path: CHANGELOG.md のパス
        version: バージョン (例: "0.2.0" or "v0.2.0")

    Returns:
        該当バージョンのCHANGELOGエントリ
    """
    version = version.lstrip("v")  # v0.2.0 -> 0.2.0

    with open(changelog_path) as f:
        content = f.read()

    # バージョンセクションを抽出
    pattern = rf"## \[{re.escape(version)}\].*?\n(.*?)(?=\n## \[|\Z)"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        raise ValueError(f"Version {version} not found in CHANGELOG.md")

    return match.group(1).strip()


def generate_release_notes(version: str, prev_version: str = None) -> str:
    """リリースノートを生成

    Args:
        version: 新バージョン (例: "v0.2.0")
        prev_version: 前バージョン (例: "v0.1.0")

    Returns:
        リリースノートのマークダウン
    """
    # vプレフィックスを正規化
    version_with_v = version if version.startswith("v") else f"v{version}"
    version_without_v = version.lstrip("v")

    project_root = Path(__file__).parent.parent
    changelog_path = project_root / "CHANGELOG.md"
    template_path = project_root / ".github" / "RELEASE_TEMPLATE.md"

    # CHANGELOGから変更内容を取得
    changelog_entry = extract_version_from_changelog(changelog_path, version)

    # テンプレートを読み込む
    if template_path.exists():
        with open(template_path) as f:
            template = f.read()
    else:
        # テンプレートがない場合はシンプルな形式
        template = """# MAO {VERSION}

{CHANGELOG}

## 📦 Installation

### New Install
```bash
curl -fsSL https://raw.githubusercontent.com/marusan03/mao/main/install.sh | sh
```

### Update
```bash
mao update
```

---

**Full Changelog**: https://github.com/marusan03/mao/compare/{PREV_VERSION}...{VERSION}
"""

    # プレースホルダーを置換
    # テンプレートに "v{VERSION}" が含まれているので、vなしのバージョンを使用
    notes = template.replace("{VERSION}", version_without_v)
    notes = notes.replace("{CHANGELOG}", changelog_entry)

    if prev_version:
        prev_version_without_v = prev_version.lstrip("v")
        notes = notes.replace("{PREV_VERSION}", version_with_v)  # Full Changelogリンクにはvありのバージョンを使用
        notes = notes.replace("v{PREV_VERSION}", f"v{prev_version_without_v}")
    else:
        # 前バージョンが指定されていない場合は行を削除
        notes = re.sub(r"\*\*Full Changelog\*\*:.*\n", "", notes)

    return notes


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_release_notes.py <version> [prev_version]")
        print("Example: python scripts/generate_release_notes.py v0.2.0 v0.1.0")
        sys.exit(1)

    version = sys.argv[1]
    prev_version = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        notes = generate_release_notes(version, prev_version)
        print(notes)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
