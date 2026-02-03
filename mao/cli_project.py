"""
CLI project commands - init, config, roles, uninstall, version, update, languages
"""
import sys
import shutil
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from mao.version import __version__

console = Console()


def _is_dev_mode() -> bool:
    """Check if running in development mode"""
    current_file = Path(__file__).resolve()
    if (current_file.parent.parent / "pyproject.toml").exists():
        dev_repo_path = current_file.parent.parent
        if (dev_repo_path / ".git").exists():
            return True
    return False


def show_version_info():
    """Display detailed version information"""
    from rich.table import Table
    import platform

    console.print(f"\n[bold cyan]MAO Version Information[/bold cyan]\n")

    table = Table(show_header=False, box=None)
    table.add_column("Key", style="dim")
    table.add_column("Value", style="green")

    table.add_row("Version", __version__)

    dev_mode = _is_dev_mode()

    if dev_mode:
        table.add_row("Mode", "[yellow]Development[/yellow]")
    else:
        table.add_row("Mode", "[green]Installed[/green]")

        mao_home = Path.home() / ".mao"
        install_dir = mao_home / "install"
        if install_dir.exists():
            import datetime
            mtime = install_dir.stat().st_mtime
            install_time = datetime.datetime.fromtimestamp(mtime)
            table.add_row("Installed", install_time.strftime("%Y-%m-%d %H:%M:%S"))

    python_version = platform.python_version()
    table.add_row("Python", python_version)

    console.print(table)
    console.print()


def register_project_commands(main_group: click.Group):
    """Register project-related commands to main CLI group"""

    @main_group.command()
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

        mao_dir.mkdir(exist_ok=True)
        (mao_dir / "coding_standards").mkdir(exist_ok=True)
        (mao_dir / "roles").mkdir(exist_ok=True)
        (mao_dir / "context").mkdir(exist_ok=True)
        (mao_dir / "logs").mkdir(exist_ok=True)

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

    @main_group.command()
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

    @main_group.command()
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

    @main_group.command()
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

        if MAO_HOME.exists():
            console.print(f"Removing {MAO_HOME}...")
            shutil.rmtree(MAO_HOME)
            console.print("[green]✓[/green] Removed installation directory")

        if MAO_BIN.exists():
            console.print(f"Removing {MAO_BIN}...")
            MAO_BIN.unlink()
            console.print("[green]✓[/green] Removed executable")

        console.print("\n[green]MAO has been uninstalled[/green]\n")
        console.print("[dim]Note: You may want to remove the PATH entry from your shell configuration[/dim]")
        console.print("[dim]Project .mao directories can be manually deleted if needed[/dim]\n")

    @main_group.command()
    def version():
        """Show detailed version information"""
        show_version_info()

    @main_group.command()
    def update():
        """Update MAO to the latest version"""
        import subprocess

        MAO_HOME = Path.home() / ".mao"
        MAO_INSTALL_DIR = MAO_HOME / "install"
        MAO_VENV = MAO_HOME / "venv"

        console.print("\n[bold cyan]MAO Updater[/bold cyan]\n")

        current_file = Path(__file__).resolve()
        dev_mode = False
        dev_repo_path = None

        if (current_file.parent.parent / "pyproject.toml").exists():
            dev_repo_path = current_file.parent.parent
            if (dev_repo_path / ".git").exists():
                dev_mode = True

        if not MAO_INSTALL_DIR.exists():
            if dev_mode:
                console.print("[yellow]Development mode[/yellow]\n")
                MAO_INSTALL_DIR = dev_repo_path
            else:
                console.print("[red]MAO installation directory not found[/red]")
                console.print("Please reinstall MAO using the installer")
                sys.exit(1)

        if (MAO_INSTALL_DIR / ".git").exists():
            console.print("Checking for updates...\n")

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

            try:
                import tomllib

                current_pyproject = subprocess.check_output(
                    ["git", "show", "HEAD:pyproject.toml"],
                    cwd=MAO_INSTALL_DIR,
                    text=True
                )
                current_data = tomllib.loads(current_pyproject)
                current_version = current_data["project"]["version"]

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

            if current_version == latest_version:
                console.print(f"[green]✓ Already up to date[/green]")
                console.print(f"Current version: [cyan]{current_version}[/cyan]\n")
                return

            console.print(f"[bold]Update available:[/bold] [yellow]{current_version}[/yellow] → [green]{latest_version}[/green]\n")

            confirm = console.input(f"[yellow]Update from {current_version} to {latest_version}?[/yellow] (y/N): ")
            if confirm.lower() != "y":
                console.print("Update cancelled")
                return

            console.print("\nDownloading updates...")
            try:
                subprocess.run(
                    ["git", "pull", "origin", "main"],
                    cwd=MAO_INSTALL_DIR,
                    check=True,
                    capture_output=True
                )
                console.print("[green]✓ Downloaded[/green]")
            except subprocess.CalledProcessError:
                console.print(f"[red]Failed to download updates[/red]")
                sys.exit(1)

        else:
            console.print("[yellow]Installation was not from git repository[/yellow]")
            console.print("Re-downloading from GitHub...")

            backup_dir = MAO_HOME / "install.backup"
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.move(str(MAO_INSTALL_DIR), str(backup_dir))

            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", "https://github.com/marusan03/mao", str(MAO_INSTALL_DIR)],
                    check=True,
                    capture_output=True
                )
                console.print("[green]✓ Downloaded latest version[/green]")
            except subprocess.CalledProcessError:
                shutil.move(str(backup_dir), str(MAO_INSTALL_DIR))
                console.print("[red]Failed to download updates[/red]")
                sys.exit(1)

            shutil.rmtree(backup_dir)

        console.print("\nReinstalling dependencies...")

        if dev_mode:
            dev_venv = MAO_INSTALL_DIR / "venv"
            if dev_venv.exists():
                target_venv = dev_venv
                console.print(f"[dim]Using development venv: {dev_venv}[/dim]")
            else:
                console.print("[yellow]Development venv not found[/yellow]")
                console.print("Please create a virtual environment:")
                console.print("  python -m venv venv")
                console.print("  source venv/bin/activate")
                console.print("  pip install -e .")
                return
        else:
            target_venv = MAO_VENV

        if not shutil.which("uv"):
            console.print("[yellow]uv not found, using pip instead[/yellow]")
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

        console.print("\n[green]✓ Update complete![/green]\n")
        console.print(f"Version updated: [dim]{current_version}[/dim] → [bold green]{latest_version}[/bold green]")
        console.print("\n[cyan]Restart your terminal to use the new version.[/cyan]")
        console.print()

    @main_group.command()
    @click.argument("language", required=False)
    def languages(language: Optional[str]):
        """List supported languages or show language details"""
        from mao.config import ConfigLoader
        from rich.table import Table

        config_loader = ConfigLoader()

        if language:
            lang_config = config_loader.load_language_config(language)
            if not lang_config:
                console.print(f"[red]Language '{language}' not found[/red]")
                console.print("\nRun 'mao languages' to see available languages")
                sys.exit(1)

            console.print(f"\n[bold cyan]{lang_config.name}[/bold cyan]\n")

            if lang_config.tools:
                console.print("[bold]推奨ツール:[/bold]")
                if lang_config.formatter:
                    console.print(f"  • フォーマッター: [green]{lang_config.formatter}[/green]")
                if lang_config.linter:
                    console.print(f"  • リンター: [green]{lang_config.linter}[/green]")
                if lang_config.test_framework:
                    console.print(f"  • テストフレームワーク: [green]{lang_config.test_framework}[/green]")
                console.print()

            if lang_config.defaults:
                console.print("[bold]デフォルト設定:[/bold]")
                for key, value in lang_config.defaults.items():
                    console.print(f"  • {key}: [cyan]{value}[/cyan]")
                console.print()

            if lang_config.file_extensions:
                exts = ", ".join(lang_config.file_extensions)
                console.print(f"[bold]ファイル拡張子:[/bold] {exts}\n")

        else:
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
