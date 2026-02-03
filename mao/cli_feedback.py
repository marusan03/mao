"""
CLI feedback commands - Manage feedback for MAO improvements
"""
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from mao import cli_completion
from mao.cli_improvements import _is_mao_project

console = Console()


def _is_dev_mode() -> bool:
    """Check if running in development mode"""
    current_file = Path(__file__).resolve()
    if (current_file.parent.parent / "pyproject.toml").exists():
        dev_repo_path = current_file.parent.parent
        if (dev_repo_path / ".git").exists():
            return True
    return False


def register_feedback_commands(main_group: click.Group):
    """Register feedback group and commands to main CLI group"""

    @main_group.group(invoke_without_command=True)
    @click.pass_context
    def feedback(ctx):
        """Manage feedback for MAO improvements (can create from any project, improve only on MAO)"""
        if not _is_dev_mode():
            console.print("[bold red]✗ The 'mao feedback' command is only available in development mode[/bold red]")
            console.print("[dim]This command is for MAO developers to collect and process feedback.[/dim]")
            console.print("[dim]If you want to report an issue, please visit: https://github.com/your-org/mao/issues[/dim]")
            sys.exit(1)

        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())
            ctx.exit()

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

        fb = manager.add_feedback(
            title=title,
            description=description,
            category=category,
            priority=priority,
            agent_id="user",
            session_id="manual",
        )

        console.print(f"\n[bold green]✓ Feedback sent![/bold green]")
        console.print(f"ID: {fb.id}")
        console.print(f"Title: {fb.title}")
        console.print(f"Category: {fb.category} | Priority: {fb.priority}")
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

        stats = manager.get_stats()
        console.print(f"\n[bold]Feedback Statistics[/bold]")
        console.print(f"Total: {stats['total']} | Open: {stats['open']} | In Progress: {stats['in_progress']} | Completed: {stats['completed']}")
        console.print()

        table = Table(show_header=True)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("Category", style="magenta")
        table.add_column("Priority", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Created", style="dim")

        for fb in feedbacks:
            priority_color = {
                "low": "dim",
                "medium": "yellow",
                "high": "bold yellow",
                "critical": "bold red",
            }.get(fb.priority, "white")

            status_color = {
                "open": "cyan",
                "in_progress": "yellow",
                "completed": "green",
                "rejected": "red",
            }.get(fb.status, "white")

            table.add_row(
                fb.id[-12:],
                fb.title[:40],
                fb.category,
                f"[{priority_color}]{fb.priority}[/{priority_color}]",
                f"[{status_color}]{fb.status}[/{status_color}]",
                fb.created_at[:10],
            )

        console.print(table)
        console.print(f"\n[dim]Use [cyan]mao feedback improve <ID>[/cyan] to work on a feedback[/dim]")

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

    @feedback.command("repair")
    @click.option("--project-dir", default=".", help="Project directory")
    def repair_feedback(project_dir: str):
        """Repair feedback index.json by scanning individual files"""
        from mao.orchestrator.feedback_manager import FeedbackManager

        project_path = Path(project_dir).resolve()
        manager = FeedbackManager(project_path=project_path)

        console.print("\n[bold cyan]🔧 Repairing feedback index...[/bold cyan]\n")

        result = manager.repair_index()

        if result["repaired"]:
            console.print(f"[bold green]✓ Repair completed![/bold green]")
            console.print(f"\nTotal feedback files: {result['total_files']}")
            console.print(f"In index before: {result['in_index_before']}")
            console.print(f"[yellow]Missing feedbacks (now added):[/yellow]")
            for fb_id in result["missing_in_index"]:
                console.print(f"  - {fb_id}")
            console.print(f"\n[bold green]✓ {len(result['missing_in_index'])} feedbacks added to index[/bold green]")
        else:
            console.print(f"[green]✓ No repair needed[/green]")
            console.print(f"Total feedbacks: {result['total_files']}")
            console.print(f"All files are in sync with index.json")

        console.print()

    # Import and register improve command from separate file
    from mao.cli_feedback_improve import register_improve_command
    register_improve_command(feedback)
