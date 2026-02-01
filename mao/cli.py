#!/usr/bin/env python3
"""
Multi-Agent Orchestrator CLI
"""
import sys
from pathlib import Path
from typing import Optional
import shutil

import click
from rich.console import Console

from mao.version import __version__, get_git_commit
from mao import cli_completion

console = Console()


def show_version_info():
    """Display detailed version information"""
    from rich.table import Table
    import platform

    console.print(f"\n[bold cyan]MAO Version Information[/bold cyan]\n")

    table = Table(show_header=False, box=None)
    table.add_column("Key", style="dim")
    table.add_column("Value", style="green")

    # バージョン
    table.add_row("Version", __version__)

    # 開発モードの検出
    current_file = Path(__file__).resolve()
    dev_mode = False
    dev_repo_path = None

    if (current_file.parent.parent / "pyproject.toml").exists():
        dev_repo_path = current_file.parent.parent
        if (dev_repo_path / ".git").exists():
            dev_mode = True

    # モード表示
    if dev_mode:
        table.add_row("Mode", "[yellow]Development[/yellow]")
    else:
        table.add_row("Mode", "[green]Installed[/green]")

        # インストール日時
        mao_home = Path.home() / ".mao"
        install_dir = mao_home / "install"
        if install_dir.exists():
            import datetime
            mtime = install_dir.stat().st_mtime
            install_time = datetime.datetime.fromtimestamp(mtime)
            table.add_row("Installed", install_time.strftime("%Y-%m-%d %H:%M:%S"))

    # Python バージョン
    python_version = platform.python_version()
    table.add_row("Python", python_version)

    console.print(table)
    console.print()


def version_callback(ctx, param, value):
    """Callback for --version option"""
    if not value or ctx.resilient_parsing:
        return
    show_version_info()
    ctx.exit()


@click.group(name='mao')
@click.option(
    '--version', '-v',
    is_flag=True,
    callback=version_callback,
    expose_value=False,
    is_eager=True,
    help='Show detailed version information'
)
def main():
    """Multi-Agent Orchestrator - Hierarchical AI development system"""
    pass


def _select_session(project_path: Path) -> Optional[str]:
    """セッション選択UI

    Args:
        project_path: プロジェクトパス

    Returns:
        選択されたセッションID（新規の場合はNone）
    """
    from rich.table import Table
    from mao.orchestrator.session_manager import SessionManager
    from datetime import datetime

    # ダミーセッションマネージャーで全セッションを取得
    temp_manager = SessionManager(project_path=project_path)
    sessions = temp_manager.get_all_sessions()

    if not sessions:
        console.print("[yellow]📝 セッションが見つかりません。新規セッションを作成します。[/yellow]")
        return None

    console.print("\n[bold cyan]📚 利用可能なセッション:[/bold cyan]")

    # セッションテーブルを作成
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("タイトル", width=30)
    table.add_column("セッションID", width=15)
    table.add_column("メッセージ", justify="right", width=10)
    table.add_column("最終更新", width=16)

    for idx, session_meta in enumerate(sessions[:10], 1):  # 最新10件のみ表示
        session_id = session_meta.get("session_id", "N/A")
        title = session_meta.get("title", "")
        message_count = session_meta.get("message_count", 0)
        updated_at = session_meta.get("updated_at", "N/A")

        # タイトルがない場合はセッションIDから生成
        if not title:
            title = f"[dim]Session {session_id[-8:]}[/dim]"

        # 日時をフォーマット
        try:
            updated_dt = datetime.fromisoformat(updated_at)
            updated_str = updated_dt.strftime("%m/%d %H:%M")
        except:
            updated_str = updated_at[:16] if len(updated_at) > 16 else updated_at

        # セッションIDを短縮表示
        short_id = session_id[-8:] if len(session_id) > 8 else session_id

        table.add_row(
            str(idx),
            title,
            short_id,
            str(message_count),
            updated_str,
        )

    console.print(table)

    # ユーザーに選択を促す
    console.print("\n[yellow]オプション:[/yellow]")
    console.print("  [cyan]1-10[/cyan]: 既存のセッションを継続")
    console.print("  [cyan]n[/cyan]:   新規セッションを作成")
    console.print("  [cyan]Enter[/cyan]: 最新セッションを継続")

    choice = console.input("\n[bold]選択してください:[/bold] ").strip().lower()

    if choice == "" or choice == "1":
        # デフォルト: 最新セッション
        selected = sessions[0]
        title_display = selected.get("title", selected["session_id"][-8:])
        console.print(f"[green]✓ 最新セッションを継続: {title_display}[/green]")
        return (selected["session_id"], None)  # (session_id, title)
    elif choice == "n":
        # 新規セッション
        console.print("[green]✓ 新規セッションを作成します[/green]")
        # タイトルを入力
        title = console.input("[yellow]セッションタイトル（省略可）:[/yellow] ").strip()
        if title:
            console.print(f"[dim]タイトル: {title}[/dim]")
        return (None, title)  # (session_id, title)
    elif choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(sessions):
            selected = sessions[idx - 1]
            title_display = selected.get("title", selected["session_id"][-8:])
            console.print(f"[green]✓ セッションを継続: {title_display}[/green]")
            return (selected["session_id"], None)  # (session_id, title)
        else:
            console.print("[red]✗ 無効な選択です。新規セッションを作成します。[/red]")
            return (None, None)
    else:
        console.print("[red]✗ 無効な選択です。新規セッションを作成します。[/red]")
        return (None, None)


@main.command()
@click.argument("prompt", required=False)
@click.option(
    "--project-dir",
    "-p",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=".",
    help="Project directory (default: current directory)",
)
@click.option(
    "--redis-url",
    "-r",
    default="redis://localhost:6379",
    help="Redis URL for state management",
)
@click.option(
    "--no-redis",
    is_flag=True,
    help="Use SQLite instead of Redis (local mode)",
)
@click.option(
    "--tmux/--no-tmux",
    default=True,
    help="Enable tmux agent monitor (default: enabled)",
)
@click.option(
    "--task",
    "-t",
    help="Initial task prompt (alternative to positional argument)",
)
@click.option(
    "--role",
    default="general",
    help="Agent role for the initial task (default: general)",
    shell_complete=cli_completion.complete_roles,
)
@click.option(
    "--model",
    default="sonnet",
    type=click.Choice(["sonnet", "opus", "haiku"]),
    help="Model to use for the initial task (default: sonnet)",
    shell_complete=cli_completion.complete_models,
)
@click.option(
    "--session",
    "-s",
    help="Session ID to continue from (default: interactive selection)",
)
@click.option(
    "--new-session",
    is_flag=True,
    help="Always create a new session (skip selection)",
)
def start(
    prompt: Optional[str],
    project_dir: str,
    redis_url: str,
    no_redis: bool,
    tmux: bool,
    task: Optional[str],
    role: str,
    model: str,
    session: Optional[str],
    new_session: bool,
):
    """Start the Multi-Agent Orchestrator in interactive mode"""
    project_path = Path(project_dir).resolve()

    console.print(f"\n[bold green]🚀 Multi-Agent Orchestrator[/bold green]")
    console.print(f"[dim]Project: {project_path}[/dim]")

    # セッション選択
    from mao.orchestrator.session_manager import SessionManager
    selected_session_id = None
    session_title = None

    if new_session:
        # 新規セッション強制
        console.print("[green]✓ 新規セッションを作成します[/green]")
        # タイトルを入力
        session_title = console.input("[yellow]セッションタイトル（省略可）:[/yellow] ").strip()
        if session_title:
            console.print(f"[dim]タイトル: {session_title}[/dim]")
    elif session:
        # セッションIDが指定されている
        selected_session_id = session
        console.print(f"[green]✓ セッションを継続: {selected_session_id}[/green]")
    else:
        # インタラクティブにセッション選択
        selected_session_id, session_title = _select_session(project_path)

    # セッションIDとタイトルをダッシュボードに渡す
    session_id_to_use = selected_session_id
    session_title_to_use = session_title

    # 初期プロンプトの処理
    initial_prompt = prompt or task

    if not initial_prompt:
        console.print("\n[yellow]💡 使い方:[/yellow]")
        console.print("  タスクを指定してエージェントを起動:")
        console.print("    [cyan]mao start \"ログイン機能のテストを書いて\"[/cyan]")
        console.print("\n  インタラクティブモードで複数エージェント起動:")
        console.print("    [cyan]mao start \"認証システムを実装\"[/cyan]")
        console.print("\n  詳細: [dim]cat USAGE.md[/dim]\n")
    else:
        console.print(f"\n[cyan]📋 タスク:[/cyan] {initial_prompt}")
        console.print(f"[dim]Role: {role} | Model: {model}[/dim]")

    # プロジェクト設定読み込み
    from mao.orchestrator.project_loader import ProjectLoader

    loader = ProjectLoader(project_path)
    try:
        config = loader.load()
    except FileNotFoundError:
        console.print(
            "[yellow]No MAO configuration found. Run 'mao init' first.[/yellow]"
        )
        sys.exit(1)

    console.print(f"[dim]Config: {config.config_file}[/dim]")

    # tmux設定（常にグリッドレイアウト）
    tmux_manager = None

    if tmux:
        from mao.orchestrator.tmux_manager import TmuxManager

        # グリッド設定を取得（config.defaultsがあればそれを使用）
        if config.defaults and config.defaults.tmux:
            grid_config = config.defaults.tmux.grid
            tmux_manager = TmuxManager(
                use_grid_layout=True,
                grid_width=grid_config.width,
                grid_height=grid_config.height,
                num_workers=grid_config.num_workers,
            )
        else:
            # デフォルト値を使用（常にグリッドレイアウト）
            tmux_manager = TmuxManager(use_grid_layout=True)

        if not tmux_manager.is_tmux_available():
            console.print("[yellow]⚠ tmux not found, running without tmux monitor[/yellow]")
            tmux_manager = None
        else:
            if tmux_manager.create_session():
                console.print(f"\n[green]✓ Grid Layout[/green]")
                console.print(f"  📋 Manager + 🔧 {tmux_manager.num_workers} Workers")
                console.print(f"  [cyan]tmux attach -t mao[/cyan] でエージェントを確認")
            else:
                tmux_manager = None

    # ダッシュボード起動（常にインタラクティブモード）
    from mao.ui.dashboard_interactive import InteractiveDashboard as Dashboard
    console.print("\n[bold green]🤝 インタラクティブモード[/bold green]")
    console.print("[dim]マネージャーと対話しながらタスクを進めます[/dim]")

    # モデル名をAPIモデルIDに変換
    model_map = {
        "sonnet": "claude-sonnet-4-20250514",
        "opus": "claude-opus-4-20250514",
        "haiku": "claude-3-5-haiku-20241022",
    }
    model_id = model_map.get(model, "claude-sonnet-4-20250514")

    app = Dashboard(
        project_path=project_path,
        config=config,
        use_redis=not no_redis,
        redis_url=redis_url if not no_redis else None,
        tmux_manager=tmux_manager,
        initial_prompt=initial_prompt,
        initial_role=role,
        initial_model=model_id,
        session_id=session_id_to_use,
        session_title=session_title_to_use,
    )

    console.print("\n[bold]ダッシュボード起動中...[/bold]")
    console.print("[dim]キーボード操作: Ctrl+Q=終了 | Ctrl+R=更新 | Ctrl+M=チャット | Tab=移動[/dim]\n")

    try:
        app.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
    finally:
        # クリーンアップ
        if tmux_manager:
            cleanup = console.input("\n[yellow]Destroy tmux session?[/yellow] (y/N): ")
            if cleanup.lower() == "y":
                tmux_manager.destroy_session()
        sys.exit(0)


@main.command()
@click.option(
    "--project-dir",
    "-p",
    type=click.Path(file_okay=False, dir_okay=True),
    default=".",
    help="Project directory to initialize",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing configuration",
)
def init(project_dir: str, force: bool):
    """Initialize Multi-Agent Orchestrator in current project"""
    project_path = Path(project_dir).resolve()
    mao_dir = project_path / ".mao"

    if mao_dir.exists() and not force:
        console.print(
            f"[yellow]Project already initialized at {mao_dir}[/yellow]\n"
            "Use --force to overwrite"
        )
        sys.exit(1)

    # .mao ディレクトリ作成
    mao_dir.mkdir(exist_ok=True)
    (mao_dir / "coding_standards").mkdir(exist_ok=True)
    (mao_dir / "roles").mkdir(exist_ok=True)
    (mao_dir / "context").mkdir(exist_ok=True)
    (mao_dir / "logs").mkdir(exist_ok=True)

    # デフォルト設定ファイル作成
    config_file = mao_dir / "config.yaml"
    if not config_file.exists() or force:
        default_config = """# Multi-Agent Orchestrator Configuration

project_name: my-project
default_language: python

# Agent settings
agents:
  default_model: sonnet  # sonnet, opus, haiku
  enable_parallel: true
  max_workers: 5

# State management
state:
  backend: sqlite  # sqlite or redis

# Logging
logging:
  level: INFO
  file: .mao/orchestrator.log

# Security settings
security:
  # WARNING: Setting allow_unsafe_operations to true gives agents unrestricted file system access
  allow_unsafe_operations: false  # Use --dangerously-skip-permissions flag
  allow_file_write: true
  allow_command_execution: true
"""
        config_file.write_text(default_config)

    # サンプルコンテキストファイル
    arch_file = mao_dir / "context" / "architecture.md"
    if not arch_file.exists() or force:
        arch_file.write_text("""# System Architecture

## Overview
Describe your system architecture here.

## Components
- Component 1: Description
- Component 2: Description

## Design Decisions
Document key architectural decisions here.
""")

    # サンプルカスタムコーディング規約
    custom_standards_file = mao_dir / "coding_standards" / "python_custom.md"
    if not custom_standards_file.exists() or force:
        custom_standards_file.write_text("""# プロジェクト固有のPythonコーディング規約

## API エンドポイント

- すべてのAPIエンドポイントは `/api/v1/` プレフィックスを使用
- RESTful な命名規則に従う

## エラーハンドリング

- カスタム例外クラスを使用
- すべてのエラーを structlog でログ記録

## その他

プロジェクト固有のルールをここに追加してください。
""")

    # .gitignore 追加
    gitignore = project_path / ".gitignore"
    gitignore_content = "\n# Multi-Agent Orchestrator\n.mao/state.db\n.mao/*.log\n.mao/logs/\n"
    if gitignore.exists():
        existing = gitignore.read_text()
        if ".mao" not in existing:
            gitignore.write_text(existing + gitignore_content)
    else:
        gitignore.write_text(gitignore_content)

    console.print(f"[bold green]✓[/bold green] Initialized at {mao_dir}")
    console.print(f"\nNext steps:")
    console.print(f"  1. Edit [cyan]{config_file}[/cyan] to customize settings")
    console.print(f"  2. Add coding standards to [cyan]{mao_dir / 'coding_standards'}[/cyan]")
    console.print(f"  3. Run [bold]mao start[/bold] to begin")


@main.command()
def config():
    """Show current configuration"""
    from mao.orchestrator.project_loader import ProjectLoader

    project_path = Path.cwd()
    loader = ProjectLoader(project_path)

    try:
        cfg = loader.load()
        console.print("[bold]Current Configuration:[/bold]")
        console.print_json(cfg.model_dump_json(indent=2))
    except FileNotFoundError:
        console.print("[yellow]No configuration found. Run 'mao init' first.[/yellow]")
        sys.exit(1)


@main.command()
def roles():
    """List available agent roles"""
    from mao.orchestrator.task_dispatcher import TaskDispatcher

    try:
        dispatcher = TaskDispatcher()

        console.print("[bold]Available Agent Roles:[/bold]\n")

        for role_name, role_config in dispatcher.roles.items():
            console.print(f"[cyan]{role_config['display_name']}[/cyan]")
            console.print(f"  Name: {role_name}")
            console.print(f"  Model: {role_config.get('model', 'sonnet')}")
            console.print(f"  Responsibilities:")
            for resp in role_config.get("responsibilities", []):
                console.print(f"    • {resp}")
            console.print()
    except Exception as e:
        console.print(f"[yellow]Note: Some roles may not be fully configured yet[/yellow]")
        console.print(f"[dim]Error: {e}[/dim]")


@main.command()
@click.option(
    "--yes", "-y",
    is_flag=True,
    help="Skip confirmation prompt"
)
def uninstall(yes: bool):
    """Uninstall Multi-Agent Orchestrator"""
    MAO_HOME = Path.home() / ".mao"
    MAO_BIN = Path.home() / ".local" / "bin" / "mao"

    console.print("\n[yellow]Multi-Agent Orchestrator Uninstaller[/yellow]\n")

    if not yes:
        console.print("This will remove:")
        console.print(f"  • {MAO_HOME}")
        console.print(f"  • {MAO_BIN}")
        console.print("\n[dim]Project-specific .mao directories will NOT be removed[/dim]\n")

        confirm = console.input("[yellow]Are you sure?[/yellow] (y/N): ")
        if confirm.lower() != "y":
            console.print("Cancelled.")
            return

    # Remove installation directory
    if MAO_HOME.exists():
        console.print(f"Removing {MAO_HOME}...")
        shutil.rmtree(MAO_HOME)
        console.print("[green]✓[/green] Removed installation directory")

    # Remove executable
    if MAO_BIN.exists():
        console.print(f"Removing {MAO_BIN}...")
        MAO_BIN.unlink()
        console.print("[green]✓[/green] Removed executable")

    console.print("\n[green]MAO has been uninstalled[/green]\n")
    console.print("[dim]Note: You may want to remove the PATH entry from your shell configuration[/dim]")
    console.print("[dim]Project .mao directories can be manually deleted if needed[/dim]\n")


@main.command()
def version():
    """Show detailed version information"""
    show_version_info()


@main.command()
def update():
    """Update MAO to the latest version"""
    import subprocess
    from pathlib import Path

    MAO_HOME = Path.home() / ".mao"
    MAO_INSTALL_DIR = MAO_HOME / "install"
    MAO_VENV = MAO_HOME / "venv"

    console.print("\n[bold cyan]MAO Updater[/bold cyan]\n")

    # 開発モードの検出
    current_file = Path(__file__).resolve()
    dev_mode = False
    dev_repo_path = None

    # 現在のファイルが開発ディレクトリにある場合
    if (current_file.parent.parent / "pyproject.toml").exists():
        dev_repo_path = current_file.parent.parent
        if (dev_repo_path / ".git").exists():
            dev_mode = True

    # インストールディレクトリの確認
    if not MAO_INSTALL_DIR.exists():
        if dev_mode:
            console.print("[yellow]Development mode[/yellow]\n")
            MAO_INSTALL_DIR = dev_repo_path
        else:
            console.print("[red]MAO installation directory not found[/red]")
            console.print("Please reinstall MAO using the installer")
            sys.exit(1)

    # Gitリポジトリかどうか確認
    if (MAO_INSTALL_DIR / ".git").exists():
        console.print("Checking for updates...\n")

        # リモートから最新情報を取得
        try:
            subprocess.run(
                ["git", "fetch", "origin", "main"],
                cwd=MAO_INSTALL_DIR,
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError:
            console.print("[red]Failed to check for updates[/red]")
            sys.exit(1)

        # 現在のバージョンと最新のバージョンを取得
        try:
            import tomllib

            # 現在のバージョン（HEAD）
            current_pyproject = subprocess.check_output(
                ["git", "show", "HEAD:pyproject.toml"],
                cwd=MAO_INSTALL_DIR,
                text=True
            )
            current_data = tomllib.loads(current_pyproject)
            current_version = current_data["project"]["version"]

            # 最新のバージョン（origin/main）
            remote_pyproject = subprocess.check_output(
                ["git", "show", "origin/main:pyproject.toml"],
                cwd=MAO_INSTALL_DIR,
                text=True
            )
            remote_data = tomllib.loads(remote_pyproject)
            latest_version = remote_data["project"]["version"]
        except Exception as e:
            console.print(f"[red]Failed to get version information: {e}[/red]")
            sys.exit(1)

        # バージョン比較
        if current_version == latest_version:
            console.print(f"[green]✓ Already up to date[/green]")
            console.print(f"Current version: [cyan]{current_version}[/cyan]\n")
            return

        # アップデート可能を表示
        console.print(f"[bold]Update available:[/bold] [yellow]{current_version}[/yellow] → [green]{latest_version}[/green]\n")

        # 確認
        confirm = console.input(f"[yellow]Update from {current_version} to {latest_version}?[/yellow] (y/N): ")
        if confirm.lower() != "y":
            console.print("Update cancelled")
            return

        # git pull
        console.print("\nDownloading updates...")
        try:
            subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=MAO_INSTALL_DIR,
                check=True,
                capture_output=True
            )
            console.print("[green]✓ Downloaded[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to download updates[/red]")
            sys.exit(1)

    else:
        console.print("[yellow]Installation was not from git repository[/yellow]")
        console.print("Re-downloading from GitHub...")

        # ディレクトリをバックアップして削除
        import shutil
        backup_dir = MAO_HOME / "install.backup"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.move(str(MAO_INSTALL_DIR), str(backup_dir))

        # 再ダウンロード
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "https://github.com/marusan03/mao", str(MAO_INSTALL_DIR)],
                check=True,
                capture_output=True
            )
            console.print("[green]✓ Downloaded latest version[/green]")
        except subprocess.CalledProcessError:
            # 失敗したらバックアップを戻す
            shutil.move(str(backup_dir), str(MAO_INSTALL_DIR))
            console.print("[red]Failed to download updates[/red]")
            sys.exit(1)

        # バックアップを削除
        shutil.rmtree(backup_dir)

    # 依存関係を再インストール
    console.print("\nReinstalling dependencies...")

    # 開発モードの場合は、プロジェクトディレクトリのvenvを使用
    if dev_mode:
        dev_venv = MAO_INSTALL_DIR / "venv"
        if dev_venv.exists():
            target_venv = dev_venv
            console.print(f"[dim]Using development venv: {dev_venv}[/dim]")
        else:
            console.print("[yellow]Development venv not found[/yellow]")
            console.print("Please create a virtual environment:")
            console.print("  python -m venv venv")
            console.print("  source venv/bin/activate  # or venv\\Scripts\\activate on Windows")
            console.print("  pip install -e .")
            return
    else:
        target_venv = MAO_VENV

    # uv が利用可能か確認
    if not shutil.which("uv"):
        console.print("[yellow]uv not found, using pip instead[/yellow]")
        # uv がない場合は pip を使用
        python_exe = target_venv / "bin" / "python"
        try:
            subprocess.run(
                [str(python_exe), "-m", "pip", "install", "-e", str(MAO_INSTALL_DIR)],
                check=True,
                capture_output=True
            )
            console.print("[green]✓ Dependencies updated[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to install dependencies: {e}[/red]")
            sys.exit(1)
    else:
        try:
            subprocess.run(
                ["uv", "pip", "install", "--python", str(target_venv / "bin" / "python"), "-e", str(MAO_INSTALL_DIR)],
                check=True,
                capture_output=True
            )
            console.print("[green]✓ Dependencies updated[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to install dependencies: {e}[/red]")
            sys.exit(1)

    # アップデート完了メッセージ
    console.print("\n[green]✓ Update complete![/green]\n")
    console.print(f"Version updated: [dim]{current_version}[/dim] → [bold green]{latest_version}[/bold green]")
    console.print("\n[cyan]Restart your terminal to use the new version.[/cyan]")
    console.print()


@main.command()
@click.argument("language", required=False)
def languages(language: Optional[str]):
    """List supported languages or show language details"""
    from mao.config import ConfigLoader
    from rich.table import Table

    config_loader = ConfigLoader()

    if language:
        # 特定言語の詳細表示
        lang_config = config_loader.load_language_config(language)
        if not lang_config:
            console.print(f"[red]Language '{language}' not found[/red]")
            console.print("\nRun 'mao languages' to see available languages")
            sys.exit(1)

        console.print(f"\n[bold cyan]{lang_config.name}[/bold cyan]\n")

        # ツール
        if lang_config.tools:
            console.print("[bold]推奨ツール:[/bold]")
            if lang_config.formatter:
                console.print(f"  • フォーマッター: [green]{lang_config.formatter}[/green]")
            if lang_config.linter:
                console.print(f"  • リンター: [green]{lang_config.linter}[/green]")
            if lang_config.test_framework:
                console.print(f"  • テストフレームワーク: [green]{lang_config.test_framework}[/green]")
            console.print()

        # デフォルト設定
        if lang_config.defaults:
            console.print("[bold]デフォルト設定:[/bold]")
            for key, value in lang_config.defaults.items():
                console.print(f"  • {key}: [cyan]{value}[/cyan]")
            console.print()

        # ファイル拡張子
        if lang_config.file_extensions:
            exts = ", ".join(lang_config.file_extensions)
            console.print(f"[bold]ファイル拡張子:[/bold] {exts}\n")

    else:
        # 言語一覧表示
        languages_list = config_loader.list_available_languages()

        if not languages_list:
            console.print("[yellow]No languages configured[/yellow]")
            return

        table = Table(title="サポートされている言語")
        table.add_column("言語", style="cyan")
        table.add_column("フォーマッター", style="green")
        table.add_column("リンター", style="yellow")
        table.add_column("テストフレームワーク", style="magenta")

        for lang_name in languages_list:
            lang_config = config_loader.load_language_config(lang_name)
            if lang_config:
                table.add_row(
                    lang_config.name,
                    lang_config.formatter or "-",
                    lang_config.linter or "-",
                    lang_config.test_framework or "-",
                )

        console.print()
        console.print(table)
        console.print(f"\n[dim]詳細を表示: mao languages <language>[/dim]")
        console.print(f"[dim]例: mao languages python[/dim]\n")


# Skills management commands
@main.group()
def skills():
    """Manage learned skills"""
    pass


@skills.command("list")
def skills_list():
    """List available skills"""
    from mao.orchestrator.skill_manager import SkillManager

    project_path = Path.cwd()
    manager = SkillManager(project_path)

    all_skills = manager.list_skills()

    if not all_skills:
        console.print("[yellow]No skills found.[/yellow]")
        console.print("\nSkills will be automatically created as agents learn patterns.")
        return

    console.print(f"[bold]Available Skills ({len(all_skills)}):[/bold]\n")

    for skill in all_skills:
        console.print(f"[cyan]• {skill.display_name}[/cyan] (v{skill.version})")
        console.print(f"  Name: {skill.name}")
        console.print(f"  {skill.description}")
        console.print()


@skills.command("show")
@click.argument("skill_name")
def skills_show(skill_name: str):
    """Show skill details"""
    from mao.orchestrator.skill_manager import SkillManager

    project_path = Path.cwd()
    manager = SkillManager(project_path)

    skill = manager.get_skill(skill_name)

    if not skill:
        console.print(f"[red]Skill not found: {skill_name}[/red]")
        sys.exit(1)

    console.print(f"[bold cyan]{skill.display_name}[/bold cyan] (v{skill.version})\n")
    console.print(f"[bold]Description:[/bold]")
    console.print(f"  {skill.description}\n")

    if skill.parameters:
        console.print(f"[bold]Parameters:[/bold]")
        for param in skill.parameters:
            required = "[red]*[/red]" if param.get("required") else ""
            default = f" (default: {param.get('default')})" if "default" in param else ""
            console.print(f"  {required} {param['name']}: {param.get('type', 'string')}{default}")
            console.print(f"    {param.get('description', '')}")
        console.print()

    if skill.examples:
        console.print(f"[bold]Examples:[/bold]")
        for example in skill.examples:
            console.print(f"  {example.get('description', '')}")
            console.print(f"  $ [green]{example.get('command', '')}[/green]")
        console.print()


@skills.command("delete")
@click.argument("skill_name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def skills_delete(skill_name: str, yes: bool):
    """Delete a skill"""
    from mao.orchestrator.skill_manager import SkillManager

    project_path = Path.cwd()
    manager = SkillManager(project_path)

    skill = manager.get_skill(skill_name)

    if not skill:
        console.print(f"[red]Skill not found: {skill_name}[/red]")
        sys.exit(1)

    if not yes:
        confirm = console.input(f"[yellow]Delete skill '{skill_name}'?[/yellow] (y/N): ")
        if confirm.lower() != "y":
            console.print("Cancelled.")
            return

    if manager.delete_skill(skill_name):
        console.print(f"[green]✓ Skill deleted: {skill_name}[/green]")
    else:
        console.print(f"[red]Failed to delete skill: {skill_name}[/red]")
        sys.exit(1)


@main.group()
def feedback():
    """Manage feedback for MAO improvements"""
    pass


@feedback.command("send")
@click.option("--title", "-t", required=True, help="Feedback title")
@click.option("--description", "-d", required=True, help="Detailed description")
@click.option(
    "--category",
    "-c",
    type=click.Choice(["bug", "feature", "improvement", "documentation"]),
    default="improvement",
    help="Feedback category",
)
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["low", "medium", "high", "critical"]),
    default="medium",
    help="Priority level",
)
@click.option("--project-dir", default=".", help="Project directory")
def send_feedback(title: str, description: str, category: str, priority: str, project_dir: str):
    """Send feedback about MAO"""
    from mao.orchestrator.feedback_manager import FeedbackManager

    project_path = Path(project_dir).resolve()
    manager = FeedbackManager(project_path=project_path)

    feedback = manager.add_feedback(
        title=title,
        description=description,
        category=category,
        priority=priority,
        agent_id="user",
        session_id="manual",
    )

    console.print(f"\n[bold green]✓ Feedback sent![/bold green]")
    console.print(f"ID: {feedback.id}")
    console.print(f"Title: {feedback.title}")
    console.print(f"Category: {feedback.category} | Priority: {feedback.priority}")
    console.print(f"\nUse [cyan]mao feedback list[/cyan] to view all feedback")


@feedback.command("list")
@click.option(
    "--status",
    type=click.Choice(["open", "in_progress", "completed", "rejected"]),
    help="Filter by status",
)
@click.option(
    "--category",
    type=click.Choice(["bug", "feature", "improvement", "documentation"]),
    help="Filter by category",
)
@click.option(
    "--priority",
    type=click.Choice(["low", "medium", "high", "critical"]),
    help="Filter by priority",
)
@click.option("--project-dir", default=".", help="Project directory")
def list_feedbacks(status: Optional[str], category: Optional[str], priority: Optional[str], project_dir: str):
    """List all feedback"""
    from mao.orchestrator.feedback_manager import FeedbackManager
    from rich.table import Table

    project_path = Path(project_dir).resolve()
    manager = FeedbackManager(project_path=project_path)

    feedbacks = manager.list_feedbacks(status=status, category=category, priority=priority)

    if not feedbacks:
        console.print("\n[dim]No feedback found[/dim]")
        return

    # 統計を表示
    stats = manager.get_stats()
    console.print(f"\n[bold]Feedback Statistics[/bold]")
    console.print(f"Total: {stats['total']} | Open: {stats['open']} | In Progress: {stats['in_progress']} | Completed: {stats['completed']}")
    console.print()

    # テーブル表示
    table = Table(show_header=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Category", style="magenta")
    table.add_column("Priority", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Created", style="dim")

    for fb in feedbacks:
        # 優先度の色分け
        priority_color = {
            "low": "dim",
            "medium": "yellow",
            "high": "bold yellow",
            "critical": "bold red",
        }.get(fb.priority, "white")

        # ステータスの色分け
        status_color = {
            "open": "cyan",
            "in_progress": "yellow",
            "completed": "green",
            "rejected": "red",
        }.get(fb.status, "white")

        table.add_row(
            fb.id[-12:],  # 短縮ID
            fb.title[:40],  # タイトル（最大40文字）
            fb.category,
            f"[{priority_color}]{fb.priority}[/{priority_color}]",
            f"[{status_color}]{fb.status}[/{status_color}]",
            fb.created_at[:10],  # 日付のみ
        )

    console.print(table)
    console.print(f"\n[dim]Use [cyan]mao feedback improve <ID>[/cyan] to work on a feedback[/dim]")


@feedback.command("improve")
@click.argument("feedback_id", shell_complete=cli_completion.complete_feedback_ids)
@click.option("--project-dir", default=".", help="Project directory")
@click.option("--model", default="sonnet", type=click.Choice(["sonnet", "opus", "haiku"]), help="Model to use", shell_complete=cli_completion.complete_models)
@click.option("--no-issue", is_flag=True, help="Skip creating GitHub issue")
@click.option("--no-pr", is_flag=True, help="Skip creating GitHub PR")
def improve_feedback(feedback_id: str, project_dir: str, model: str, no_issue: bool, no_pr: bool):
    """Work on feedback - run MAO to improve MAO with issue/PR creation"""
    from mao.orchestrator.feedback_manager import FeedbackManager
    from mao.orchestrator.project_loader import ProjectLoader
    from mao.ui.dashboard_interactive import InteractiveDashboard
    import subprocess
    import json

    project_path = Path(project_dir).resolve()
    manager = FeedbackManager(project_path=project_path)

    # フィードバックを取得（短縮IDにも対応）
    fb = manager.get_feedback(feedback_id)

    # 短縮IDの場合、完全なIDを検索
    if not fb:
        # 全フィードバックから短縮IDで検索
        all_feedbacks = manager.list_feedbacks()
        for feedback in all_feedbacks:
            if feedback.id.endswith(feedback_id):
                fb = feedback
                break

    if not fb:
        console.print(f"[bold red]✗ Feedback not found: {feedback_id}[/bold red]")
        console.print("[dim]Use [cyan]mao feedback list[/cyan] to see available feedback IDs[/dim]")
        return

    console.print(f"\n[bold cyan]📋 Feedback: {fb.title}[/bold cyan]")
    console.print(f"Category: {fb.category} | Priority: {fb.priority}")
    console.print(f"Description:\n{fb.description}\n")

    # Git リポジトリかチェック
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=project_path,
            capture_output=True,
            timeout=5,
        )
        is_git_repo = result.returncode == 0
    except Exception:
        is_git_repo = False

    if not is_git_repo:
        console.print("[bold red]✗ Not a git repository[/bold red]")
        return

    # GitHub リポジトリかチェック
    try:
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner"],
            cwd=project_path,
            capture_output=True,
            timeout=5,
        )
        is_github_repo = result.returncode == 0
        if is_github_repo:
            repo_info = json.loads(result.stdout.decode())
            repo_name = repo_info.get("nameWithOwner", "")
    except Exception:
        is_github_repo = False
        repo_name = ""

    # GitHub issue を作成
    issue_number = None
    if not no_issue and is_github_repo:
        console.print("\n[bold]Creating GitHub issue...[/bold]")

        # カテゴリに応じたラベル
        labels = {
            "bug": "bug",
            "feature": "enhancement",
            "improvement": "enhancement",
            "documentation": "documentation",
        }
        label = labels.get(fb.category, "enhancement")

        # 優先度ラベル
        priority_labels = {
            "low": "priority: low",
            "medium": "priority: medium",
            "high": "priority: high",
            "critical": "priority: critical",
        }
        priority_label = priority_labels.get(fb.priority, "priority: medium")

        issue_body = f"""## Feedback ID
{fb.id}

## Category
{fb.category}

## Priority
{fb.priority}

## Description
{fb.description}

## Session Info
- Agent: {fb.agent_id}
- Session: {fb.session_id}
- Created: {fb.created_at}

---
*This issue was automatically created from MAO feedback system.*
"""

        try:
            result = subprocess.run(
                [
                    "gh", "issue", "create",
                    "--title", fb.title,
                    "--body", issue_body,
                    "--label", label,
                    "--label", priority_label,
                    "--label", "mao-feedback",
                ],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # issue URL から番号を抽出
                issue_url = result.stdout.strip()
                issue_number = issue_url.split("/")[-1]
                console.print(f"[bold green]✓ Issue created: #{issue_number}[/bold green]")
                console.print(f"[dim]{issue_url}[/dim]")
            else:
                console.print(f"[bold yellow]⚠ Failed to create issue: {result.stderr}[/bold yellow]")
        except Exception as e:
            console.print(f"[bold yellow]⚠ Failed to create issue: {e}[/bold yellow]")

    # WorktreeManager を初期化
    from mao.orchestrator.worktree_manager import WorktreeManager
    worktree_manager = WorktreeManager(project_path=project_path)

    # ステータスを in_progress に更新
    manager.update_status(feedback_id, "in_progress")

    # ブランチ名を生成
    safe_title = ''.join(c if c.isalnum() or c in '-_' else '-' for c in fb.title[:30])
    if issue_number:
        branch_name = f"feedback/{issue_number}_{fb.id[-8:]}-{safe_title}"
    else:
        branch_name = f"feedback/{fb.id[-8:]}-{safe_title}"

    # Feedback 用の worktree を作成
    console.print(f"\n[bold]Creating feedback worktree: {branch_name}[/bold]")
    feedback_worktree = worktree_manager.create_feedback_worktree(
        feedback_id=fb.id[-8:],
        branch_name=branch_name
    )

    if not feedback_worktree:
        console.print("[bold red]✗ Failed to create feedback worktree[/bold red]")
        manager.update_status(feedback_id, "pending")
        return

    console.print(f"[bold green]✓ Worktree created: {feedback_worktree}[/bold green]")

    # プロジェクト設定を読み込み
    try:
        loader = ProjectLoader(feedback_worktree)  # worktree パスで読み込み
        config = loader.load()
    except Exception as e:
        console.print(f"[bold red]✗ Failed to load config: {e}[/bold red]")
        worktree_manager.remove_worktree(feedback_worktree)
        manager.update_status(feedback_id, "pending")
        return

    # MAO を起動してフィードバックに取り組む
    console.print("\n[bold green]🚀 Starting MAO to work on this feedback...[/bold green]")
    if issue_number:
        console.print(f"[dim]Working on issue #{issue_number}[/dim]\n")

    # フィードバックを含めたプロンプトを作成
    prompt = f"""MAO プロジェクトの改善フィードバック:

【タイトル】{fb.title}

【カテゴリ】{fb.category}

【優先度】{fb.priority}

【GitHub Issue】{"#" + issue_number if issue_number else "なし"}

【詳細】
{fb.description}

このフィードバックに基づいて、MAO プロジェクトを改善してください。
必要なファイルの変更、テストの追加、ドキュメントの更新などを行ってください。

⚠️ 重要: 各ワーカーは独自の git worktree で作業します。
ワーカー用 worktree は自動的に作成されます。

完了したら、変更内容を git commit してください。
コミットメッセージには issue 番号（#{issue_number if issue_number else "N/A"}）を含めてください。"""

    # モデル名変換
    model_map = {
        "sonnet": "claude-sonnet-4-20250514",
        "opus": "claude-opus-4-20250514",
        "haiku": "claude-3-5-haiku-20241022",
    }
    model_id = model_map.get(model, "claude-sonnet-4-20250514")

    # InteractiveDashboard を起動（feedback worktree で）
    app = InteractiveDashboard(
        project_path=feedback_worktree,  # worktree パスで起動
        config=config,
        use_redis=False,
        initial_prompt=prompt,
        initial_model=model_id,
        feedback_branch=branch_name,  # フィードバックブランチ名を渡す
        worktree_manager=worktree_manager,  # WorktreeManager を渡す
    )

    success = False
    try:
        app.run()
        success = True

        # 完了後の処理
        console.print("\n[bold]Work completed![/bold]")

        # 変更をプッシュ
        console.print("\n[bold]Pushing changes...[/bold]")
        if worktree_manager.push_branch(feedback_worktree, branch_name):
            console.print("[bold green]✓ Changes pushed[/bold green]")

            # PR を自動作成（no_pr でない場合）
            if not no_pr and is_github_repo:
                console.print("\n[bold]Creating Pull Request...[/bold]")

                # PR の本文を作成
                pr_body = f"""## Summary
This PR addresses feedback: {fb.title}

## Feedback Details
- **Category**: {fb.category}
- **Priority**: {fb.priority}
- **Feedback ID**: {fb.id}
"""

                if issue_number:
                    pr_body += f"\nCloses #{issue_number}\n"

                pr_body += f"""
## Description
{fb.description}

## Changes
<!-- MAO による変更内容 -->

## Test Plan
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Changes reviewed

---
*This PR was created automatically by MAO feedback improvement workflow.*
"""

                pr_url = worktree_manager.create_pr(
                    worktree_path=feedback_worktree,
                    title=f"{fb.category}: {fb.title}",
                    body=pr_body,
                    base="main"
                )

                if pr_url:
                    console.print(f"[bold green]✓ PR created![/bold green]")
                    console.print(f"[cyan]{pr_url}[/cyan]")

                    # フィードバックを completed に
                    manager.update_status(feedback_id, "completed")
                    console.print("[bold green]✓ Feedback marked as completed[/bold green]")
                else:
                    console.print(f"[bold yellow]⚠ Failed to create PR[/bold yellow]")
        else:
            console.print(f"[bold yellow]⚠ Failed to push changes[/bold yellow]")

    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠ Interrupted by user[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]✗ Error: {e}[/bold red]")
    finally:
        # Worktree をクリーンアップ
        console.print("\n[bold]Cleaning up worktrees...[/bold]")
        cleanup_count = worktree_manager.cleanup_worktrees()
        console.print(f"[bold green]✓ Cleaned up {cleanup_count} worktrees[/bold green]")

        if not success:
            manager.update_status(feedback_id, "pending")


@main.group()
def session():
    """Manage chat sessions"""
    pass


@session.command("list")
@click.option("--project-dir", default=".", help="Project directory")
@click.option("--limit", "-n", default=20, help="Number of sessions to show")
def list_sessions(project_dir: str, limit: int):
    """List all sessions"""
    from rich.table import Table
    from mao.orchestrator.session_manager import SessionManager
    from datetime import datetime

    project_path = Path(project_dir).resolve()
    temp_manager = SessionManager(project_path=project_path)
    sessions = temp_manager.get_all_sessions()

    if not sessions:
        console.print("[yellow]📝 セッションが見つかりません[/yellow]")
        return

    console.print(f"\n[bold cyan]📚 セッション一覧 (最新{min(limit, len(sessions))}件)[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("セッションID", width=20)
    table.add_column("タイトル", width=40)
    table.add_column("メッセージ", justify="right", width=10)
    table.add_column("最終更新", width=16)
    table.add_column("作成日時", width=16)

    for session_meta in sessions[:limit]:
        session_id = session_meta.get("session_id", "N/A")
        title = session_meta.get("title", "")
        message_count = session_meta.get("message_count", 0)
        updated_at = session_meta.get("updated_at", "N/A")
        created_at = session_meta.get("created_at", "N/A")

        if not title:
            title = f"[dim](タイトルなし)[/dim]"

        # 日時をフォーマット
        try:
            updated_dt = datetime.fromisoformat(updated_at)
            updated_str = updated_dt.strftime("%m/%d %H:%M")
        except:
            updated_str = updated_at[:16] if len(updated_at) > 16 else updated_at

        try:
            created_dt = datetime.fromisoformat(created_at)
            created_str = created_dt.strftime("%m/%d %H:%M")
        except:
            created_str = created_at[:16] if len(created_at) > 16 else created_at

        short_id = session_id[-12:]

        table.add_row(
            short_id,
            title,
            str(message_count),
            updated_str,
            created_str,
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(sessions)} sessions[/dim]")


@session.command("rename")
@click.argument("session_id")
@click.argument("new_title")
@click.option("--project-dir", default=".", help="Project directory")
def rename_session(session_id: str, new_title: str, project_dir: str):
    """Rename a session"""
    from mao.orchestrator.session_manager import SessionManager

    project_path = Path(project_dir).resolve()
    temp_manager = SessionManager(project_path=project_path)
    sessions = temp_manager.get_all_sessions()

    # セッションIDを検索（部分一致）
    found = None
    for s in sessions:
        if s["session_id"].endswith(session_id):
            found = s
            break

    if not found:
        console.print(f"[red]✗ セッションが見つかりません: {session_id}[/red]")
        return

    # セッションマネージャーを作成してタイトルを更新
    session_mgr = SessionManager(
        project_path=project_path,
        session_id=found["session_id"]
    )
    session_mgr.set_title(new_title)

    console.print(f"[green]✓ セッションタイトルを更新しました[/green]")
    console.print(f"  セッション: {found['session_id'][-12:]}")
    console.print(f"  新しいタイトル: {new_title}")


@session.command("delete")
@click.argument("session_id")
@click.option("--project-dir", default=".", help="Project directory")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def delete_session(session_id: str, project_dir: str, yes: bool):
    """Delete a session"""
    from mao.orchestrator.session_manager import SessionManager

    project_path = Path(project_dir).resolve()
    temp_manager = SessionManager(project_path=project_path)
    sessions = temp_manager.get_all_sessions()

    # セッションIDを検索（部分一致）
    found = None
    for s in sessions:
        if s["session_id"].endswith(session_id):
            found = s
            break

    if not found:
        console.print(f"[red]✗ セッションが見つかりません: {session_id}[/red]")
        return

    # 確認
    if not yes:
        title = found.get("title", "(タイトルなし)")
        console.print(f"\n[yellow]セッションを削除しますか？[/yellow]")
        console.print(f"  ID: {found['session_id'][-12:]}")
        console.print(f"  タイトル: {title}")
        console.print(f"  メッセージ数: {found.get('message_count', 0)}")

        if not click.confirm("削除しますか？"):
            console.print("[dim]キャンセルしました[/dim]")
            return

    # セッションを削除
    session_mgr = SessionManager(
        project_path=project_path,
        session_id=found["session_id"]
    )
    if session_mgr.delete_session():
        console.print(f"[green]✓ セッションを削除しました: {found['session_id'][-12:]}[/green]")
    else:
        console.print(f"[red]✗ セッションの削除に失敗しました[/red]")


@session.command("show")
@click.argument("session_id")
@click.option("--project-dir", default=".", help="Project directory")
@click.option("--messages", "-m", is_flag=True, help="Show messages")
def show_session(session_id: str, project_dir: str, messages: bool):
    """Show session details"""
    from mao.orchestrator.session_manager import SessionManager
    from rich.panel import Panel
    from datetime import datetime

    project_path = Path(project_dir).resolve()
    temp_manager = SessionManager(project_path=project_path)
    sessions = temp_manager.get_all_sessions()

    # セッションIDを検索（部分一致）
    found = None
    for s in sessions:
        if s["session_id"].endswith(session_id):
            found = s
            break

    if not found:
        console.print(f"[red]✗ セッションが見つかりません: {session_id}[/red]")
        return

    # セッション詳細を表示
    session_mgr = SessionManager(
        project_path=project_path,
        session_id=found["session_id"]
    )

    stats = session_mgr.get_session_stats()
    title = stats.get("title", "(タイトルなし)")

    console.print(f"\n[bold cyan]📋 セッション詳細[/bold cyan]\n")
    console.print(f"[bold]ID:[/bold] {stats['session_id']}")
    console.print(f"[bold]タイトル:[/bold] {title}")
    console.print(f"[bold]メッセージ数:[/bold] {stats['total_messages']}")
    console.print(f"  - User: {stats['user_messages']}")
    console.print(f"  - Manager: {stats['manager_messages']}")
    console.print(f"  - System: {stats['system_messages']}")

    try:
        created_dt = datetime.fromisoformat(stats['created_at'])
        console.print(f"[bold]作成日時:[/bold] {created_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    except:
        console.print(f"[bold]作成日時:[/bold] {stats['created_at']}")

    try:
        updated_dt = datetime.fromisoformat(stats['updated_at'])
        console.print(f"[bold]最終更新:[/bold] {updated_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    except:
        console.print(f"[bold]最終更新:[/bold] {stats['updated_at']}")

    # メッセージを表示
    if messages:
        console.print(f"\n[bold cyan]💬 メッセージ履歴[/bold cyan]\n")
        session_messages = session_mgr.get_messages()

        for msg in session_messages:
            role_emoji = {
                "user": "👤",
                "manager": "👔",
                "system": "⚙️",
            }.get(msg.role, "❓")

            role_name = {
                "user": "User",
                "manager": "CTO",
                "system": "System",
            }.get(msg.role, msg.role)

            console.print(Panel(
                msg.content,
                title=f"{role_emoji} {role_name}",
                subtitle=msg.timestamp[:19] if len(msg.timestamp) >= 19 else msg.timestamp,
                border_style="cyan" if msg.role == "user" else "green" if msg.role == "manager" else "dim",
            ))


@feedback.command("show")
@click.argument("feedback_id", shell_complete=cli_completion.complete_feedback_ids)
@click.option("--project-dir", default=".", help="Project directory")
def show_feedback(feedback_id: str, project_dir: str):
    """Show detailed feedback information"""
    from mao.orchestrator.feedback_manager import FeedbackManager
    from rich.panel import Panel
    from rich.markdown import Markdown

    project_path = Path(project_dir).resolve()
    manager = FeedbackManager(project_path=project_path)

    fb = manager.get_feedback(feedback_id)

    # 短縮IDの場合、完全なIDを検索
    if not fb:
        all_feedbacks = manager.list_feedbacks()
        for feedback in all_feedbacks:
            if feedback.id.endswith(feedback_id):
                fb = feedback
                break

    if not fb:
        console.print(f"[bold red]✗ Feedback not found: {feedback_id}[/bold red]")
        console.print("[dim]Use [cyan]mao feedback list[/cyan] to see available feedback IDs[/dim]")
        return

    # 詳細情報を表示
    console.print()
    console.print(Panel(
        f"[bold]{fb.title}[/bold]\n\n"
        f"[cyan]ID:[/cyan] {fb.id}\n"
        f"[cyan]Category:[/cyan] {fb.category}\n"
        f"[cyan]Priority:[/cyan] {fb.priority}\n"
        f"[cyan]Status:[/cyan] {fb.status}\n"
        f"[cyan]Agent:[/cyan] {fb.agent_id}\n"
        f"[cyan]Session:[/cyan] {fb.session_id}\n"
        f"[cyan]Created:[/cyan] {fb.created_at}",
        title="Feedback Details",
        border_style="cyan",
    ))

    console.print("\n[bold]Description:[/bold]")
    console.print(Markdown(fb.description))
    console.print()


@main.command("completion")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]), required=False)
@click.option("--install", is_flag=True, help="Install completion for current shell")
def completion(shell: Optional[str], install: bool):
    """Generate shell completion script

    Examples:
        # Show completion script for bash
        mao completion bash

        # Install completion for current shell (auto-detect)
        mao completion --install

        # Install completion for specific shell
        mao completion zsh --install
    """
    import os
    import subprocess

    # シェルを自動検出
    if not shell:
        current_shell = os.environ.get("SHELL", "")
        if "bash" in current_shell:
            shell = "bash"
        elif "zsh" in current_shell:
            shell = "zsh"
        elif "fish" in current_shell:
            shell = "fish"
        else:
            console.print("[red]✗ Could not detect shell. Please specify: bash, zsh, or fish[/red]")
            return

    if install:
        # インストール手順を表示
        console.print(f"\n[bold cyan]Installing completion for {shell}[/bold cyan]\n")

        if shell == "bash":
            completion_dir = Path.home() / ".local" / "share" / "bash-completion" / "completions"
            completion_dir.mkdir(parents=True, exist_ok=True)
            completion_file = completion_dir / "mao"

            # 補完スクリプトを生成
            result = subprocess.run(
                ["_MAO_COMPLETE=bash_source mao"],
                shell=True,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                completion_file.write_text(result.stdout)
                console.print(f"[green]✓ Bash completion installed to: {completion_file}[/green]")
                console.print("\n[dim]Reload your shell or run:[/dim]")
                console.print(f"[cyan]  source {completion_file}[/cyan]\n")
            else:
                console.print(f"[red]✗ Failed to generate completion script[/red]")
                console.print(f"[dim]{result.stderr}[/dim]")

        elif shell == "zsh":
            # zsh用のインストール手順
            console.print("[yellow]Add the following to your ~/.zshrc:[/yellow]\n")
            console.print("[cyan]eval \"$(_MAO_COMPLETE=zsh_source mao)\"[/cyan]\n")
            console.print("[dim]Then reload your shell:[/dim]")
            console.print("[cyan]source ~/.zshrc[/cyan]\n")

        elif shell == "fish":
            completion_dir = Path.home() / ".config" / "fish" / "completions"
            completion_dir.mkdir(parents=True, exist_ok=True)
            completion_file = completion_dir / "mao.fish"

            # 補完スクリプトを生成
            result = subprocess.run(
                ["_MAO_COMPLETE=fish_source mao"],
                shell=True,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                completion_file.write_text(result.stdout)
                console.print(f"[green]✓ Fish completion installed to: {completion_file}[/green]")
                console.print("\n[dim]Completions will be available in new shells[/dim]\n")
            else:
                console.print(f"[red]✗ Failed to generate completion script[/red]")
                console.print(f"[dim]{result.stderr}[/dim]")

    else:
        # 補完スクリプトを表示
        console.print(f"\n[bold]Completion script for {shell}:[/bold]\n")

        if shell == "bash":
            console.print("[dim]# Add to ~/.bashrc:[/dim]")
            console.print("[cyan]eval \"$(_MAO_COMPLETE=bash_source mao)\"[/cyan]\n")

        elif shell == "zsh":
            console.print("[dim]# Add to ~/.zshrc:[/dim]")
            console.print("[cyan]eval \"$(_MAO_COMPLETE=zsh_source mao)\"[/cyan]\n")

        elif shell == "fish":
            console.print("[dim]# Fish completions are auto-loaded from:[/dim]")
            console.print(f"[cyan]{Path.home() / '.config/fish/completions/mao.fish'}[/cyan]\n")
            console.print("[dim]# Generate and save:[/dim]")
            console.print("[cyan]_MAO_COMPLETE=fish_source mao > ~/.config/fish/completions/mao.fish[/cyan]\n")


if __name__ == "__main__":
    main()
