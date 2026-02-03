"""
CLI sandbox commands - Docker Sandbox isolation for MAO

Provides commands to run MAO in isolated Docker AI Sandboxes (MicroVMs).
This protects the host system while allowing full agent functionality.
"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


def register_sandbox_commands(main_group: click.Group):
    """Register sandbox commands to main CLI group"""

    @main_group.group()
    def sandbox():
        """Run MAO in Docker Sandbox for isolation.

        Docker AI Sandboxes run MAO inside a secure MicroVM,
        protecting your host system from potentially harmful operations.

        Requirements:
        - Docker Desktop (macOS/Windows) or Docker Desktop 4.57+ (Linux)
        - AI Sandboxes feature enabled in Docker Desktop settings
        """
        pass

    @sandbox.command("start")
    @click.argument("prompt", required=False)
    @click.option(
        "-p",
        "--project-dir",
        type=click.Path(exists=True, file_okay=False, dir_okay=True),
        default=".",
        help="Project directory to mount in sandbox (default: current directory)",
    )
    @click.option(
        "--model",
        default="sonnet",
        type=click.Choice(["sonnet", "opus", "haiku"]),
        help="Model to use for CTO (default: sonnet)",
    )
    @click.option(
        "--no-template",
        is_flag=True,
        help="Don't use custom MAO template (will need to install MAO manually)",
    )
    @click.pass_context
    def sandbox_start(ctx, prompt, project_dir, model, no_template):
        """Start MAO inside a Docker Sandbox.

        The sandbox provides full isolation while allowing MAO to operate
        normally. File changes are synced back to the host.

        Examples:
            mao sandbox start "Implement authentication"
            mao sandbox start -p ~/projects/myapp "Add tests"
        """
        from mao.orchestrator.sandbox_manager import SandboxManager

        project_path = Path(project_dir).resolve()
        manager = SandboxManager(project_path)

        # Check Docker Sandbox availability
        if not manager.is_available():
            console.print("[red bold]Error: Docker Sandbox is not available[/red bold]")
            console.print()
            console.print("[yellow]To use Docker Sandboxes:[/yellow]")
            console.print("  1. Install Docker Desktop")
            console.print("  2. Enable AI Sandboxes in Docker Desktop settings")
            console.print()
            console.print("[dim]For more info: https://docs.docker.com/ai/sandboxes/[/dim]")
            ctx.exit(1)

        # Check if sandbox already running
        if manager.is_running():
            console.print(
                f"[yellow]Sandbox '{manager.sandbox_name}' is already running[/yellow]"
            )
            console.print()
            console.print("Options:")
            console.print(f"  • Attach to it: [cyan]mao sandbox attach -p {project_dir}[/cyan]")
            console.print(f"  • Remove it:    [cyan]mao sandbox rm -p {project_dir}[/cyan]")
            ctx.exit(1)

        # Check for custom template
        use_template = not no_template
        if use_template and not manager.template_exists():
            console.print("[yellow]MAO sandbox template not found[/yellow]")
            console.print()
            build_it = console.input(
                "Build template now? (recommended for faster startups) [Y/n]: "
            )
            if build_it.lower() != "n":
                console.print("\n[bold]Building MAO sandbox template...[/bold]")
                if manager.build_template():
                    console.print("[green]Template built successfully[/green]\n")
                else:
                    console.print("[red]Failed to build template[/red]")
                    console.print("[dim]Continuing without custom template...[/dim]\n")
                    use_template = False
            else:
                use_template = False

        console.print(f"\n[bold green]Starting MAO in Docker Sandbox[/bold green]")
        console.print(f"[dim]Project: {project_path}[/dim]")
        console.print(f"[dim]Sandbox: {manager.sandbox_name}[/dim]")

        if prompt:
            console.print(f"[dim]Task: {prompt}[/dim]")

        console.print()

        success = manager.start(
            prompt=prompt,
            use_custom_template=use_template,
            model=model,
        )

        if not success:
            console.print("[red]Failed to start sandbox[/red]")
            ctx.exit(1)

    @sandbox.command("attach")
    @click.option(
        "-p",
        "--project-dir",
        type=click.Path(exists=True, file_okay=False, dir_okay=True),
        default=".",
        help="Project directory (to identify sandbox)",
    )
    @click.pass_context
    def sandbox_attach(ctx, project_dir):
        """Attach to an existing MAO sandbox.

        Reconnects to a previously started sandbox session.
        """
        from mao.orchestrator.sandbox_manager import SandboxManager

        project_path = Path(project_dir).resolve()
        manager = SandboxManager(project_path)

        if not manager.is_available():
            console.print("[red]Docker Sandbox is not available[/red]")
            ctx.exit(1)

        if not manager.is_running():
            console.print(
                f"[yellow]Sandbox '{manager.sandbox_name}' is not running[/yellow]"
            )
            console.print()
            console.print(f"Start it with: [cyan]mao sandbox start -p {project_dir}[/cyan]")
            ctx.exit(1)

        console.print(f"[bold]Attaching to sandbox: {manager.sandbox_name}[/bold]")
        manager.attach()

    @sandbox.command("rm")
    @click.option(
        "-p",
        "--project-dir",
        type=click.Path(exists=True, file_okay=False, dir_okay=True),
        default=".",
        help="Project directory (to identify sandbox)",
    )
    @click.option(
        "-f",
        "--force",
        is_flag=True,
        help="Force removal even if running",
    )
    @click.pass_context
    def sandbox_rm(ctx, project_dir, force):
        """Remove a MAO sandbox.

        Stops and removes the sandbox container.
        Project files are preserved on the host.
        """
        from mao.orchestrator.sandbox_manager import SandboxManager

        project_path = Path(project_dir).resolve()
        manager = SandboxManager(project_path)

        if not manager.is_available():
            console.print("[red]Docker Sandbox is not available[/red]")
            ctx.exit(1)

        status = manager.get_status()
        if status is None:
            console.print(
                f"[yellow]Sandbox '{manager.sandbox_name}' not found[/yellow]"
            )
            ctx.exit(1)

        console.print(f"Removing sandbox: {manager.sandbox_name}")

        if manager.remove(force=force):
            console.print("[green]Sandbox removed[/green]")
        else:
            console.print("[red]Failed to remove sandbox[/red]")
            if not force:
                console.print("[dim]Try with --force to force removal[/dim]")
            ctx.exit(1)

    @sandbox.command("ls")
    def sandbox_ls():
        """List all MAO sandboxes.

        Shows all Docker sandboxes created by MAO.
        """
        from mao.orchestrator.sandbox_manager import SandboxManager

        # Use dummy path just to access class methods
        manager = SandboxManager(Path.cwd())

        if not manager.is_available():
            console.print("[red]Docker Sandbox is not available[/red]")
            sys.exit(1)

        sandboxes = manager.list_sandboxes()

        if not sandboxes:
            console.print("[dim]No MAO sandboxes found[/dim]")
            return

        table = Table(title="MAO Sandboxes")
        table.add_column("Name", style="cyan")
        table.add_column("Status", style="green")

        for sb in sandboxes:
            status_style = "green" if sb["status"] == "running" else "yellow"
            table.add_row(sb["name"], f"[{status_style}]{sb['status']}[/{status_style}]")

        console.print(table)

    @sandbox.command("build")
    @click.option(
        "--force",
        "-f",
        is_flag=True,
        help="Force rebuild even if template exists",
    )
    @click.pass_context
    def sandbox_build(ctx, force):
        """Build the MAO sandbox template.

        Creates a Docker image with MAO preinstalled for faster sandbox startups.
        This only needs to be done once (or after MAO updates).
        """
        from mao.orchestrator.sandbox_manager import SandboxManager

        manager = SandboxManager(Path.cwd())

        if not force and manager.template_exists():
            console.print(
                f"[yellow]Template '{manager.TEMPLATE_NAME}' already exists[/yellow]"
            )
            rebuild = console.input("Rebuild? [y/N]: ")
            if rebuild.lower() != "y":
                console.print("Cancelled")
                return

        console.print("[bold]Building MAO sandbox template...[/bold]")
        console.print("[dim]This may take a few minutes on first build[/dim]\n")

        if manager.build_template():
            console.print(f"\n[green]Template built: {manager.TEMPLATE_NAME}[/green]")
            console.print()
            console.print("You can now start sandboxes with:")
            console.print("  [cyan]mao sandbox start \"your task\"[/cyan]")
        else:
            console.print("[red]Failed to build template[/red]")
            console.print()
            console.print("Check that Docker is running and try again.")
            ctx.exit(1)

    @sandbox.command("status")
    @click.option(
        "-p",
        "--project-dir",
        type=click.Path(exists=True, file_okay=False, dir_okay=True),
        default=".",
        help="Project directory (to identify sandbox)",
    )
    def sandbox_status(project_dir):
        """Show status of MAO sandbox for current project."""
        from mao.orchestrator.sandbox_manager import SandboxManager

        project_path = Path(project_dir).resolve()
        manager = SandboxManager(project_path)

        console.print(f"\n[bold]Sandbox Status[/bold]")
        console.print(f"[dim]Project: {project_path}[/dim]")
        console.print(f"[dim]Sandbox name: {manager.sandbox_name}[/dim]")
        console.print()

        # Check Docker Sandbox availability
        if not manager.is_available():
            console.print("[red]Docker Sandbox: Not available[/red]")
            console.print("[dim]Install Docker Desktop and enable AI Sandboxes[/dim]")
            return

        console.print("[green]Docker Sandbox: Available[/green]")

        # Check template
        if manager.template_exists():
            console.print(f"[green]MAO Template: Built ({manager.TEMPLATE_NAME})[/green]")
        else:
            console.print("[yellow]MAO Template: Not built[/yellow]")
            console.print("[dim]Run 'mao sandbox build' to create it[/dim]")

        # Check sandbox status
        status = manager.get_status()
        if status:
            status_color = "green" if status == "running" else "yellow"
            console.print(f"[{status_color}]Sandbox: {status}[/{status_color}]")
        else:
            console.print("[dim]Sandbox: Not created[/dim]")

        console.print()
