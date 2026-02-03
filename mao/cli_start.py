"""
CLI start command - Session selection and dashboard startup
"""
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from mao import cli_completion

console = Console()


def _select_session(project_path: Path) -> tuple[Optional[str], Optional[str]]:
    """セッション選択UI

    Args:
        project_path: プロジェクトパス

    Returns:
        (session_id, title)のタプル（新規の場合はsession_idがNone）
    """
    from rich.table import Table
    from mao.orchestrator.session_manager import SessionManager
    from datetime import datetime

    # ダミーセッションマネージャーで全セッションを取得
    temp_manager = SessionManager(project_path=project_path)
    sessions = temp_manager.get_all_sessions()

    if not sessions:
        console.print("[yellow]📝 セッションが見つかりません。新規セッションを作成します。[/yellow]")
        return (None, None)

    console.print("\n[bold cyan]📚 利用可能なセッション:[/bold cyan]")

    # セッションテーブルを作成
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("タイトル", width=30)
    table.add_column("セッションID", width=15)
    table.add_column("メッセージ", justify="right", width=10)
    table.add_column("最終更新", width=16)

    for idx, session_meta in enumerate(sessions[:10], 1):
        session_id = session_meta.get("session_id", "N/A")
        title = session_meta.get("title", "")
        message_count = session_meta.get("message_count", 0)
        updated_at = session_meta.get("updated_at", "N/A")

        if not title:
            title = f"[dim]Session {session_id[-8:]}[/dim]"

        try:
            updated_dt = datetime.fromisoformat(updated_at)
            updated_str = updated_dt.strftime("%m/%d %H:%M")
        except:
            updated_str = updated_at[:16] if len(updated_at) > 16 else updated_at

        short_id = session_id[-8:] if len(session_id) > 8 else session_id

        table.add_row(
            str(idx),
            title,
            short_id,
            str(message_count),
            updated_str,
        )

    console.print(table)

    console.print("\n[yellow]オプション:[/yellow]")
    console.print("  [cyan]1-10[/cyan]: 既存のセッションを継続")
    console.print("  [cyan]Enter[/cyan]: 新規セッションを作成（デフォルト）")

    choice = console.input("\n[bold]選択してください:[/bold] ").strip().lower()

    if choice == "":
        console.print("[green]✓ 新規セッションを作成します[/green]")
        title = console.input("[yellow]セッションタイトル（省略可）:[/yellow] ").strip()
        if title:
            console.print(f"[dim]タイトル: {title}[/dim]")
        return (None, title)
    elif choice == "1":
        selected = sessions[0]
        title_display = selected.get("title", selected["session_id"][-8:])
        console.print(f"[green]✓ 最新セッションを継続: {title_display}[/green]")
        return (selected["session_id"], None)
    elif choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(sessions):
            selected = sessions[idx - 1]
            title_display = selected.get("title", selected["session_id"][-8:])
            console.print(f"[green]✓ セッションを継続: {title_display}[/green]")
            return (selected["session_id"], None)
        else:
            console.print("[red]✗ 無効な選択です。新規セッションを作成します。[/red]")
            return (None, None)
    else:
        console.print("[red]✗ 無効な選択です。新規セッションを作成します。[/red]")
        return (None, None)


def register_start_command(main_group: click.Group):
    """Register start command to main CLI group"""

    @main_group.command()
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
        help="Enable tmux grid visualization (default: enabled).",
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
        shell_complete=cli_completion.complete_roles,
    )
    @click.option(
        "--model",
        default="sonnet",
        type=click.Choice(["sonnet", "opus", "haiku"]),
        help="Model to use for the initial task (default: sonnet)",
        shell_complete=cli_completion.complete_models,
    )
    @click.option(
        "--session",
        "-s",
        help="Session ID to continue from (default: interactive selection)",
    )
    @click.option(
        "--new-session",
        is_flag=True,
        help="Always create a new session (skip selection)",
    )
    def start(
        prompt: Optional[str],
        project_dir: str,
        redis_url: str,
        no_redis: bool,
        tmux: bool,
        task: Optional[str],
        role: str,
        model: str,
        session: Optional[str],
        new_session: bool,
    ):
        """Start the Multi-Agent Orchestrator in interactive mode"""
        project_path = Path(project_dir).resolve()

        console.print(f"\n[bold green]🚀 Multi-Agent Orchestrator[/bold green]")
        console.print(f"[dim]Project: {project_path}[/dim]")

        # セッション選択
        from mao.orchestrator.session_manager import SessionManager
        selected_session_id = None
        session_title = None

        if new_session:
            console.print("[green]✓ 新規セッションを作成します[/green]")
            session_title = console.input("[yellow]セッションタイトル（省略可）:[/yellow] ").strip()
            if session_title:
                console.print(f"[dim]タイトル: {session_title}[/dim]")
        elif session:
            selected_session_id = session
            console.print(f"[green]✓ セッションを継続: {selected_session_id}[/green]")
        else:
            selected_session_id, session_title = _select_session(project_path)

        session_id_to_use = selected_session_id
        session_title_to_use = session_title

        initial_prompt = prompt or task

        if not initial_prompt:
            console.print("\n[yellow]💡 使い方:[/yellow]")
            console.print("  タスクを指定してエージェントを起動:")
            console.print("    [cyan]mao start \"ログイン機能のテストを書いて\"[/cyan]")
            console.print("\n  インタラクティブモードで複数エージェント起動:")
            console.print("    [cyan]mao start \"認証システムを実装\"[/cyan]")
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

        if tmux:
            from mao.orchestrator.tmux_manager import TmuxManager

            if config.defaults and config.defaults.tmux:
                grid_config = config.defaults.tmux.grid
                tmux_manager = TmuxManager(
                    use_grid_layout=True,
                    grid_width=grid_config.width,
                    grid_height=grid_config.height,
                    num_agents=grid_config.num_agents,
                )
            else:
                tmux_manager = TmuxManager(use_grid_layout=True)

            if not tmux_manager.is_tmux_available():
                console.print("[yellow]⚠ tmux not found, running without tmux monitor[/yellow]")
                tmux_manager = None
            else:
                if tmux_manager.create_session():
                    console.print(f"\n[green]✓ Tmux Grid Enabled[/green]")
                    console.print(f"  📋 Manager + 🔧 {tmux_manager.num_agents} Agents")
                    console.print(f"  [cyan bold]tmux attach -t mao[/cyan bold] で各エージェントをリアルタイム確認")
                    console.print(f"  [dim]各ペインにエージェント出力が表示されます[/dim]")
                else:
                    tmux_manager = None

        # ダッシュボード起動
        from mao.ui.dashboard_interactive import InteractiveDashboard as Dashboard
        console.print("\n[bold green]🤝 インタラクティブモード[/bold green]")
        console.print("[dim]マネージャーと対話しながらタスクを進めます[/dim]")

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
            session_id=session_id_to_use,
            session_title=session_title_to_use,
        )

        console.print("\n[bold]ダッシュボード起動中...[/bold]")
        console.print("[dim]キーボード操作: Ctrl+Q=終了 | Ctrl+R=更新 | Ctrl+M=チャット | Tab=移動[/dim]\n")

        try:
            app.run()
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down...[/yellow]")
        finally:
            if tmux_manager:
                cleanup = console.input("\n[yellow]Destroy tmux session?[/yellow] (y/N): ")
                if cleanup.lower() == "y":
                    tmux_manager.destroy_session()
            sys.exit(0)
