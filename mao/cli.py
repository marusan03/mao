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


@click.group()
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
    "--tmux-layout",
    type=click.Choice(["tiled", "horizontal", "vertical", "main-horizontal", "main-vertical", "grid"]),
    default="grid",
    help="tmux layout style (default: grid for 3x3 multi-agent layout)",
)
@click.option(
    "--grid",
    is_flag=True,
    help="Use 3x3 grid layout for multi-agent execution (same as --tmux-layout=grid)",
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
)
@click.option(
    "--model",
    default="sonnet",
    type=click.Choice(["sonnet", "opus", "haiku"]),
    help="Model to use for the initial task (default: sonnet)",
)
def start(
    prompt: Optional[str],
    project_dir: str,
    redis_url: str,
    no_redis: bool,
    tmux: bool,
    tmux_layout: str,
    grid: bool,
    task: Optional[str],
    role: str,
    model: str,
):
    """Start the Multi-Agent Orchestrator in interactive mode"""
    project_path = Path(project_dir).resolve()

    console.print(f"\n[bold green]🚀 Multi-Agent Orchestrator[/bold green]")
    console.print(f"[dim]Project: {project_path}[/dim]")

    # 初期プロンプトの処理
    initial_prompt = prompt or task

    if not initial_prompt:
        console.print("\n[yellow]💡 使い方:[/yellow]")
        console.print("  タスクを指定してエージェントを起動:")
        console.print("    [cyan]mao start \"ログイン機能のテストを書いて\"[/cyan]")
        console.print("\n  グリッドレイアウトで複数エージェント起動:")
        console.print("    [cyan]mao start --grid \"認証システムを実装\"[/cyan]")
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

    # tmux設定
    tmux_manager = None
    use_grid = grid or tmux_layout == "grid"

    if tmux:
        from mao.orchestrator.tmux_manager import TmuxManager

        # グリッド設定を取得（config.defaultsがあればそれを使用）
        if config.defaults and config.defaults.tmux:
            grid_config = config.defaults.tmux.grid
            tmux_manager = TmuxManager(
                use_grid_layout=use_grid,
                grid_width=grid_config.width,
                grid_height=grid_config.height,
                num_workers=grid_config.num_workers,
            )
        else:
            # デフォルト値を使用
            tmux_manager = TmuxManager(use_grid_layout=use_grid)

        if not tmux_manager.is_tmux_available():
            console.print("[yellow]⚠ tmux not found, running without tmux monitor[/yellow]")
            tmux_manager = None
        else:
            if tmux_manager.create_session():
                if use_grid:
                    console.print(f"\n[green]✓ Grid Layout[/green]")
                    console.print(f"  📋 Manager + 🔧 {tmux_manager.num_workers} Workers")
                else:
                    tmux_manager.set_layout(tmux_layout)
                    console.print(f"\n[green]✓ tmux session ready[/green]")
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


@skills.command("run")
@click.argument("skill_name")
@click.argument("args", nargs=-1)
@click.option("--dry-run", is_flag=True, help="Show commands without executing")
def skills_run(skill_name: str, args: tuple, dry_run: bool):
    """Run a skill"""
    from mao.orchestrator.skill_manager import SkillManager
    from mao.orchestrator.skill_executor import SkillExecutor

    project_path = Path.cwd()
    manager = SkillManager(project_path)
    executor = SkillExecutor(project_path)

    skill = manager.get_skill(skill_name)

    if not skill:
        console.print(f"[red]Skill not found: {skill_name}[/red]")
        sys.exit(1)

    # パラメータ解析 (--key=value 形式)
    parameters = {}
    for arg in args:
        if "=" in arg:
            key, value = arg.split("=", 1)
            key = key.lstrip("-")
            # boolean変換
            if value.lower() in ("true", "yes", "1"):
                value = True
            elif value.lower() in ("false", "no", "0"):
                value = False
            parameters[key] = value

    console.print(f"[bold]Running skill:[/bold] {skill.display_name}")

    if dry_run:
        console.print("\n[yellow]Dry run mode - commands that would be executed:[/yellow]\n")
        commands = executor.dry_run(skill, parameters)
        for cmd in commands:
            console.print(f"  $ {cmd}")
        return

    # 実行
    console.print()
    result = executor.execute_skill(skill, parameters)

    if result.success:
        console.print(f"\n[green]✓ Skill executed successfully[/green]")
        console.print(f"Duration: {result.duration:.2f}s")
        if result.output:
            console.print("\n[bold]Output:[/bold]")
            console.print(result.output)
    else:
        console.print(f"\n[red]✗ Skill execution failed[/red]")
        console.print(f"Exit code: {result.exit_code}")
        if result.error:
            console.print("\n[bold]Error:[/bold]")
            console.print(result.error)
        sys.exit(1)


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


@skills.command("proposals")
def skills_proposals():
    """List pending skill proposals"""
    from mao.orchestrator.skill_manager import SkillManager

    project_path = Path.cwd()
    manager = SkillManager(project_path)

    proposals = manager.list_proposals()

    if not proposals:
        console.print("[yellow]No pending proposals.[/yellow]")
        return

    console.print(f"[bold]Pending Skill Proposals ({len(proposals)}):[/bold]\n")

    for proposal in proposals:
        risk_color = {
            "SAFE": "green",
            "WARNING": "yellow",
            "CRITICAL": "red",
        }.get(proposal.review.risk_level, "white")

        console.print(f"[cyan]• {proposal.skill.display_name}[/cyan]")
        console.print(f"  Status: {proposal.review.status}")
        console.print(f"  Quality: {proposal.review.quality_score}/10")
        console.print(f"  Security: [{risk_color}]{proposal.review.risk_level}[/{risk_color}]")
        console.print(f"  Proposed: {proposal.proposed_at}")
        console.print()


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
@click.argument("feedback_id")
@click.option("--project-dir", default=".", help="Project directory")
@click.option("--model", default="sonnet", type=click.Choice(["sonnet", "opus", "haiku"]), help="Model to use")
@click.option("--no-issue", is_flag=True, help="Skip creating GitHub issue")
@click.option("--no-pr", is_flag=True, help="Skip creating GitHub PR")
def improve_feedback(feedback_id: str, project_dir: str, model: str, no_issue: bool, no_pr: bool):
    """Work on feedback - run MAO to improve MAO with issue/PR creation"""
    from mao.orchestrator.feedback_manager import FeedbackManager
    from mao.orchestrator.project_loader import load_project_config
    from mao.ui.dashboard_interactive import InteractiveDashboard
    import subprocess
    import json

    project_path = Path(project_dir).resolve()
    manager = FeedbackManager(project_path=project_path)

    # フィードバックを取得
    fb = manager.get_feedback(feedback_id)
    if not fb:
        console.print(f"[bold red]✗ Feedback not found: {feedback_id}[/bold red]")
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

    # ステータスを in_progress に更新
    manager.update_status(feedback_id, "in_progress")

    # ブランチ名を生成
    branch_name = f"feedback/{fb.id[-12:]}-{fb.title[:30].replace(' ', '-').lower()}"

    # ブランチを作成
    console.print(f"\n[bold]Creating branch: {branch_name}[/bold]")
    try:
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=project_path,
            check=True,
            timeout=10,
        )
        console.print("[bold green]✓ Branch created[/bold green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold yellow]⚠ Branch may already exist, switching to it[/bold yellow]")
        try:
            subprocess.run(["git", "checkout", branch_name], cwd=project_path, check=True, timeout=10)
        except Exception:
            console.print(f"[bold red]✗ Failed to checkout branch[/bold red]")
            return

    # プロジェクト設定を読み込み
    try:
        config = load_project_config(project_path)
    except Exception as e:
        console.print(f"[bold red]✗ Failed to load config: {e}[/bold red]")
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

完了したら、変更内容を git commit してください。
コミットメッセージには issue 番号（#{issue_number if issue_number else "N/A"}）を含めてください。"""

    # モデル名変換
    model_map = {
        "sonnet": "claude-sonnet-4-20250514",
        "opus": "claude-opus-4-20250514",
        "haiku": "claude-3-5-haiku-20241022",
    }
    model_id = model_map.get(model, "claude-sonnet-4-20250514")

    # InteractiveDashboard を起動
    app = InteractiveDashboard(
        project_path=project_path,
        config=config,
        use_redis=False,
        initial_prompt=prompt,
        initial_model=model_id,
    )

    try:
        app.run()

        # 完了後の処理
        console.print("\n[bold]Work completed![/bold]")

        # PR を作成するか確認
        if not no_pr and is_github_repo and click.confirm("Create GitHub PR?"):
            console.print("\n[bold]Creating Pull Request...[/bold]")

            # 変更をプッシュ
            try:
                subprocess.run(
                    ["git", "push", "-u", "origin", branch_name],
                    cwd=project_path,
                    check=True,
                    timeout=60,
                )
                console.print("[bold green]✓ Changes pushed[/bold green]")
            except subprocess.CalledProcessError as e:
                console.print(f"[bold red]✗ Failed to push: {e}[/bold red]")
                return

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

            # PR を作成
            try:
                result = subprocess.run(
                    [
                        "gh", "pr", "create",
                        "--title", f"{fb.category}: {fb.title}",
                        "--body", pr_body,
                        "--label", "mao-feedback",
                    ],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    pr_url = result.stdout.strip()
                    console.print(f"[bold green]✓ PR created![/bold green]")
                    console.print(f"[cyan]{pr_url}[/cyan]")

                    # フィードバックを completed に
                    manager.update_status(feedback_id, "completed")
                    console.print("[bold green]✓ Feedback marked as completed[/bold green]")
                else:
                    console.print(f"[bold yellow]⚠ Failed to create PR: {result.stderr}[/bold yellow]")
            except Exception as e:
                console.print(f"[bold red]✗ Failed to create PR: {e}[/bold red]")

        elif click.confirm("Mark this feedback as completed?"):
            manager.update_status(feedback_id, "completed")
            console.print("[bold green]✓ Feedback marked as completed[/bold green]")

    except Exception as e:
        console.print(f"[bold red]✗ Error: {e}[/bold red]")


@feedback.command("show")
@click.argument("feedback_id")
@click.option("--project-dir", default=".", help="Project directory")
def show_feedback(feedback_id: str, project_dir: str):
    """Show detailed feedback information"""
    from mao.orchestrator.feedback_manager import FeedbackManager
    from rich.panel import Panel
    from rich.markdown import Markdown

    project_path = Path(project_dir).resolve()
    manager = FeedbackManager(project_path=project_path)

    fb = manager.get_feedback(feedback_id)
    if not fb:
        console.print(f"[bold red]✗ Feedback not found: {feedback_id}[/bold red]")
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


if __name__ == "__main__":
    main()
