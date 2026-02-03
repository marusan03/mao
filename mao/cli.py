#!/usr/bin/env python3
"""
Multi-Agent Orchestrator CLI

This is the main entry point for the MAO CLI.
Commands are organized into separate modules for maintainability.
"""
import os
import subprocess
import click
from rich.console import Console

from mao.version import __version__
from mao.cli_project import show_version_info

console = Console()


def _tmux_session_exists(session_name: str) -> bool:
    """Check if tmux session exists"""
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


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


# Register commands from separate modules
from mao.cli_start import register_start_command
from mao.cli_project import register_project_commands
from mao.cli_skills import register_skills_commands
from mao.cli_improvements import register_improvement_commands
from mao.cli_feedback import register_feedback_commands
from mao.cli_sessions import register_session_commands
from mao.cli_shell_completion import register_completion_command
from mao.cli_sandbox import register_sandbox_commands

register_start_command(main)
register_project_commands(main)
register_skills_commands(main)
register_improvement_commands(main)
register_feedback_commands(main)
register_session_commands(main)
register_completion_command(main)
register_sandbox_commands(main)


@main.command()
@click.option(
    "--session", "-s",
    default="mao",
    help="tmux session name (default: mao)"
)
def attach(session: str):
    """Attach to MAO tmux session"""
    if not _tmux_session_exists(session):
        console.print(f"[red]✗ tmux session '{session}' not found[/red]")
        console.print("[dim]Start a task first with: mao start[/dim]")
        raise SystemExit(1)

    # Replace current process with tmux attach
    os.execvp("tmux", ["tmux", "attach-session", "-t", session])


if __name__ == "__main__":
    main()
