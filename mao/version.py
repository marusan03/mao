"""
Version information for MAO
"""
from pathlib import Path
from typing import Optional
import tomllib


def get_version() -> str:
    """pyproject.toml からバージョンを取得

    Returns:
        バージョン文字列
    """
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except Exception:
        return "unknown"


def get_git_commit(repo_path: Optional[Path] = None) -> Optional[str]:
    """Git コミットハッシュを取得

    Args:
        repo_path: リポジトリパス（Noneの場合はMAOのインストールディレクトリ）

    Returns:
        コミットハッシュ（短縮版）または None
    """
    import subprocess

    if repo_path is None:
        repo_path = Path.home() / ".mao" / "install"

    if not (repo_path / ".git").exists():
        return None

    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_path,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return commit
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


__version__ = get_version()
