"""
CLI shell completion command - Generate shell completion scripts
"""
import os
import subprocess
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

console = Console()


def register_completion_command(main_group: click.Group):
    """Register completion command to main CLI group"""

    @main_group.command("completion")
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
            console.print(f"\n[bold cyan]Installing completion for {shell}[/bold cyan]\n")

            if shell == "bash":
                completion_dir = Path.home() / ".local" / "share" / "bash-completion" / "completions"
                completion_dir.mkdir(parents=True, exist_ok=True)
                completion_file = completion_dir / "mao"

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
                console.print("[yellow]Add the following to your ~/.zshrc:[/yellow]\n")
                console.print("[cyan]eval \"$(_MAO_COMPLETE=zsh_source mao)\"[/cyan]\n")
                console.print("[dim]Then reload your shell:[/dim]")
                console.print("[cyan]source ~/.zshrc[/cyan]\n")

            elif shell == "fish":
                completion_dir = Path.home() / ".config" / "fish" / "completions"
                completion_dir.mkdir(parents=True, exist_ok=True)
                completion_file = completion_dir / "mao.fish"

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
