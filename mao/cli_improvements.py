"""
CLI project improvement commands - Manage project improvements
"""
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from mao import cli_completion

console = Console()


def _is_mao_project(project_path: Path) -> bool:
    """MAOプロジェクトかどうかを判定"""
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib

            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
                project_name = data.get("project", {}).get("name", "")
                return project_name == "mao"
        except Exception:
            pass

    setup_py = project_path / "setup.py"
    if setup_py.exists():
        try:
            content = setup_py.read_text()
            return 'name="mao"' in content or "name='mao'" in content
        except Exception:
            pass

    return False


def register_improvement_commands(main_group: click.Group):
    """Register project improvement commands to main CLI group"""

    @main_group.group()
    def project():
        """Manage project improvements (for any project)"""
        pass

    @project.command("create")
    @click.option("--project-dir", default=".", help="Project directory")
    @click.option("--title", "-t", required=True, help="Improvement title")
    @click.option("--description", "-d", required=True, help="Improvement description")
    @click.option(
        "--category",
        "-c",
        type=click.Choice(["feature", "bug", "refactor", "performance", "documentation"]),
        default="feature",
        help="Improvement category",
    )
    @click.option(
        "--priority",
        "-p",
        type=click.Choice(["low", "medium", "high", "critical"]),
        default="medium",
        help="Improvement priority",
    )
    def create_improvement(
        project_dir: str, title: str, description: str, category: str, priority: str
    ):
        """Create a new project improvement task"""
        from mao.orchestrator.improvement_manager import ImprovementManager

        project_path = Path(project_dir).resolve()
        manager = ImprovementManager(project_path=project_path)

        improvement = manager.create_improvement(
            title=title,
            description=description,
            category=category,
            priority=priority,
        )

        console.print(f"\n[bold green]✓ Improvement created![/bold green]")
        console.print(f"[cyan]ID:[/cyan] {improvement.id[:12]}")
        console.print(f"[cyan]Title:[/cyan] {improvement.title}")
        console.print(f"[cyan]Category:[/cyan] {improvement.category}")
        console.print(f"[cyan]Priority:[/cyan] {improvement.priority}")
        console.print(f"\n[dim]Use 'mao project improve {improvement.id[:8]}' to work on it[/dim]")

    @project.command("list")
    @click.option("--project-dir", default=".", help="Project directory")
    @click.option("--status", type=click.Choice(["pending", "in_progress", "completed", "cancelled"]), help="Filter by status")
    @click.option("--category", type=click.Choice(["feature", "bug", "refactor", "performance", "documentation"]), help="Filter by category")
    def list_improvements(project_dir: str, status: Optional[str], category: Optional[str]):
        """List all project improvements"""
        from rich.table import Table
        from mao.orchestrator.improvement_manager import ImprovementManager

        project_path = Path(project_dir).resolve()
        manager = ImprovementManager(project_path=project_path)

        improvements = manager.list_improvements(status=status, category=category)

        if not improvements:
            console.print("[yellow]No improvements found[/yellow]")
            return

        stats = manager.get_stats()
        console.print(f"\n[bold cyan]📋 Project Improvements ({stats['total']} total)[/bold cyan]")
        console.print(
            f"[dim]Pending: {stats['pending']} | In Progress: {stats['in_progress']} | "
            f"Completed: {stats['completed']} | Cancelled: {stats['cancelled']}[/dim]\n"
        )

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", width=12)
        table.add_column("Title", width=40)
        table.add_column("Category", width=12)
        table.add_column("Priority", width=10)
        table.add_column("Status", width=12)

        status_colors = {
            "pending": "yellow",
            "in_progress": "cyan",
            "completed": "green",
            "cancelled": "red",
        }

        for imp in improvements:
            status_color = status_colors.get(imp.status, "white")
            table.add_row(
                imp.id[:12],
                imp.title,
                imp.category,
                imp.priority,
                f"[{status_color}]{imp.status}[/{status_color}]",
            )

        console.print(table)

    @project.command("show")
    @click.argument("improvement_id", shell_complete=cli_completion.complete_improvement_ids)
    @click.option("--project-dir", default=".", help="Project directory")
    def show_improvement(improvement_id: str, project_dir: str):
        """Show detailed improvement information"""
        from rich.panel import Panel
        from rich.markdown import Markdown
        from mao.orchestrator.improvement_manager import ImprovementManager

        project_path = Path(project_dir).resolve()
        manager = ImprovementManager(project_path=project_path)

        improvement = manager.get_improvement(improvement_id)

        if not improvement:
            console.print(f"[bold red]✗ Improvement not found: {improvement_id}[/bold red]")
            console.print("[dim]Use [cyan]mao project list[/cyan] to see available improvements[/dim]")
            return

        console.print(f"\n[bold cyan]📋 Improvement: {improvement.title}[/bold cyan]\n")
        console.print(f"[bold]ID:[/bold] {improvement.id}")
        console.print(f"[bold]Category:[/bold] {improvement.category}")
        console.print(f"[bold]Priority:[/bold] {improvement.priority}")
        console.print(f"[bold]Status:[/bold] {improvement.status}")
        console.print(f"[bold]Created:[/bold] {improvement.created_at}")
        console.print(f"[bold]Updated:[/bold] {improvement.updated_at}")

        if improvement.completed_at:
            console.print(f"[bold]Completed:[/bold] {improvement.completed_at}")

        if improvement.pr_url:
            console.print(f"[bold]PR:[/bold] {improvement.pr_url}")

        if improvement.branch_name:
            console.print(f"[bold]Branch:[/bold] {improvement.branch_name}")

        console.print(f"\n[bold]Description:[/bold]")
        console.print(Panel(Markdown(improvement.description), border_style="cyan"))

    @project.command("delete")
    @click.argument("improvement_id", shell_complete=cli_completion.complete_improvement_ids)
    @click.option("--project-dir", default=".", help="Project directory")
    @click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
    def delete_improvement(improvement_id: str, project_dir: str, yes: bool):
        """Delete a project improvement"""
        from mao.orchestrator.improvement_manager import ImprovementManager

        project_path = Path(project_dir).resolve()
        manager = ImprovementManager(project_path=project_path)

        improvement = manager.get_improvement(improvement_id)

        if not improvement:
            console.print(f"[bold red]✗ Improvement not found: {improvement_id}[/bold red]")
            return

        if not yes:
            console.print(f"\n[yellow]Delete improvement?[/yellow]")
            console.print(f"  ID: {improvement.id[:12]}")
            console.print(f"  Title: {improvement.title}")
            console.print(f"  Status: {improvement.status}")

            if not click.confirm("Are you sure?"):
                console.print("[dim]Cancelled[/dim]")
                return

        if manager.delete_improvement(improvement.id):
            console.print(f"[bold green]✓ Improvement deleted: {improvement.id[:12]}[/bold green]")
        else:
            console.print(f"[bold red]✗ Failed to delete improvement[/bold red]")

    @project.command("improve")
    @click.argument("improvement_id", shell_complete=cli_completion.complete_improvement_ids)
    @click.option("--project-dir", default=".", help="Project directory")
    @click.option("--model", default="sonnet", type=click.Choice(["sonnet", "opus", "haiku"]), help="Model to use", shell_complete=cli_completion.complete_models)
    @click.option("--no-issue", is_flag=True, help="Don't create GitHub issue")
    def improve_project(
        improvement_id: str,
        project_dir: str,
        model: str,
        no_issue: bool,
    ):
        """Work on a project improvement with CTO and workers (any project)"""
        console.print("[yellow]project improve コマンドは実装中です[/yellow]")
        console.print("[dim]詳細は次のコミットで追加されます[/dim]")
