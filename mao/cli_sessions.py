"""
CLI session commands - Manage chat sessions
"""
from pathlib import Path

import click
from rich.console import Console

from mao import cli_completion

console = Console()


def register_session_commands(main_group: click.Group):
    """Register session group and commands to main CLI group"""

    @main_group.group()
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
    @click.argument("session_id", shell_complete=cli_completion.complete_session_ids)
    @click.argument("new_title")
    @click.option("--project-dir", default=".", help="Project directory")
    def rename_session(session_id: str, new_title: str, project_dir: str):
        """Rename a session"""
        from mao.orchestrator.session_manager import SessionManager

        project_path = Path(project_dir).resolve()
        temp_manager = SessionManager(project_path=project_path)
        sessions = temp_manager.get_all_sessions()

        found = None
        for s in sessions:
            if s["session_id"].endswith(session_id):
                found = s
                break

        if not found:
            console.print(f"[red]✗ セッションが見つかりません: {session_id}[/red]")
            return

        session_mgr = SessionManager(
            project_path=project_path,
            session_id=found["session_id"]
        )
        session_mgr.set_title(new_title)

        console.print(f"[green]✓ セッションタイトルを更新しました[/green]")
        console.print(f"  セッション: {found['session_id'][-12:]}")
        console.print(f"  新しいタイトル: {new_title}")

    @session.command("delete")
    @click.argument("session_id", shell_complete=cli_completion.complete_session_ids)
    @click.option("--project-dir", default=".", help="Project directory")
    @click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
    def delete_session(session_id: str, project_dir: str, yes: bool):
        """Delete a session"""
        from mao.orchestrator.session_manager import SessionManager

        project_path = Path(project_dir).resolve()
        temp_manager = SessionManager(project_path=project_path)
        sessions = temp_manager.get_all_sessions()

        found = None
        for s in sessions:
            if s["session_id"].endswith(session_id):
                found = s
                break

        if not found:
            console.print(f"[red]✗ セッションが見つかりません: {session_id}[/red]")
            return

        if not yes:
            title = found.get("title", "(タイトルなし)")
            console.print(f"\n[yellow]セッションを削除しますか？[/yellow]")
            console.print(f"  ID: {found['session_id'][-12:]}")
            console.print(f"  タイトル: {title}")
            console.print(f"  メッセージ数: {found.get('message_count', 0)}")

            if not click.confirm("削除しますか？"):
                console.print("[dim]キャンセルしました[/dim]")
                return

        session_mgr = SessionManager(
            project_path=project_path,
            session_id=found["session_id"]
        )
        if session_mgr.delete_session():
            console.print(f"[green]✓ セッションを削除しました: {found['session_id'][-12:]}[/green]")
        else:
            console.print(f"[red]✗ セッションの削除に失敗しました[/red]")

    @session.command("show")
    @click.argument("session_id", shell_complete=cli_completion.complete_session_ids)
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

        found = None
        for s in sessions:
            if s["session_id"].endswith(session_id):
                found = s
                break

        if not found:
            console.print(f"[red]✗ セッションが見つかりません: {session_id}[/red]")
            return

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

        if messages:
            console.print(f"\n[bold cyan]💬 メッセージ履歴[/bold cyan]\n")
            session_messages = session_mgr.get_messages()

            for msg in session_messages:
                role_emoji = {
                    "user": "👤",
                    "cto": "🛡️",
                    "system": "⚙️",
                }.get(msg.role, "❓")

                role_name = {
                    "user": "User",
                    "cto": "CTO",
                    "system": "System",
                }.get(msg.role, msg.role)

                console.print(Panel(
                    msg.content,
                    title=f"{role_emoji} {role_name}",
                    subtitle=msg.timestamp[:19] if len(msg.timestamp) >= 19 else msg.timestamp,
                    border_style="cyan" if msg.role == "user" else "green" if msg.role == "cto" else "dim",
                ))
