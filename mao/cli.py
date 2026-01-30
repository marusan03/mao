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

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Multi-Agent Orchestrator - Hierarchical AI development system"""
    pass


@main.command()
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
    type=click.Choice(["tiled", "horizontal", "vertical", "main-horizontal", "main-vertical"]),
    default="tiled",
    help="tmux layout style",
)
def start(
    project_dir: str,
    redis_url: str,
    no_redis: bool,
    tmux: bool,
    tmux_layout: str,
):
    """Start the Multi-Agent Orchestrator dashboard"""
    project_path = Path(project_dir).resolve()

    console.print(f"[bold green]Starting Multi-Agent Orchestrator[/bold green]")
    console.print(f"Project: {project_path}")

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

    console.print(f"[dim]Configuration loaded from {config.config_file}[/dim]")

    # tmux設定
    tmux_manager = None
    if tmux:
        from mao.orchestrator.tmux_manager import TmuxManager

        tmux_manager = TmuxManager()

        if not tmux_manager.is_tmux_available():
            console.print("[yellow]⚠ tmux not found, running without tmux monitor[/yellow]")
            tmux_manager = None
        else:
            if tmux_manager.create_session():
                tmux_manager.set_layout(tmux_layout)
                console.print(f"[green]✓ tmux session created[/green]")
                console.print(f"  View agents: [cyan]tmux attach -t mao[/cyan]")
            else:
                tmux_manager = None

    # ダッシュボード起動
    from mao.ui.dashboard import Dashboard

    app = Dashboard(
        project_path=project_path,
        config=config,
        use_redis=not no_redis,
        redis_url=redis_url if not no_redis else None,
        tmux_manager=tmux_manager,
    )

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


if __name__ == "__main__":
    main()
