"""
CLI skills commands - Manage learned skills
"""
import sys
from pathlib import Path

import click
from rich.console import Console

console = Console()


def register_skills_commands(main_group: click.Group):
    """Register skills group and commands to main CLI group"""

    @main_group.group()
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
