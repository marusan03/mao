"""
CLI start command - tmux中心のマルチエージェント起動

新アーキテクチャ:
- tmux必須（全エージェントはtmuxペイン内で動作）
- CTOはペイン0でインタラクティブClaude Code
- エージェントは必要に応じてCTOが動的に起動
- ダッシュボードはオプション（進捗確認用）
"""
import sys
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

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
        except Exception:
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


def _check_tmux_available() -> bool:
    """tmuxが利用可能かチェック"""
    return shutil.which("tmux") is not None


def _check_claude_available() -> bool:
    """claude CLIが利用可能かチェック"""
    return shutil.which("claude") is not None or shutil.which("claude-code") is not None


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
        "--task",
        "-t",
        help="Initial task prompt (alternative to positional argument)",
    )
    @click.option(
        "--model",
        default="sonnet",
        type=click.Choice(["sonnet", "opus", "haiku"]),
        help="Model to use for CTO (default: sonnet)",
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
    @click.option(
        "--dashboard",
        is_flag=True,
        help="Also launch the dashboard for progress monitoring (optional)",
    )
    @click.option(
        "--num-agents",
        "-n",
        default=4,
        type=int,
        help="Number of agent panes to create (default: 4)",
    )
    def start(
        prompt: Optional[str],
        project_dir: str,
        task: Optional[str],
        model: str,
        session: Optional[str],
        new_session: bool,
        dashboard: bool,
        num_agents: int,
    ):
        """Start MAO with tmux-based multi-agent orchestration.

        All agents run as interactive Claude Code instances in tmux panes.
        CTO runs in pane 0 and orchestrates other agents as needed.
        """
        project_path = Path(project_dir).resolve()

        console.print(f"\n[bold green]🚀 Multi-Agent Orchestrator (MAO)[/bold green]")
        console.print(f"[dim]Project: {project_path}[/dim]")

        # 1. tmux必須チェック
        if not _check_tmux_available():
            console.print("\n[red bold]❌ Error: tmux is required but not found[/red bold]")
            console.print("[yellow]Please install tmux:[/yellow]")
            console.print("  macOS: [cyan]brew install tmux[/cyan]")
            console.print("  Ubuntu: [cyan]sudo apt install tmux[/cyan]")
            sys.exit(1)

        # 2. claude CLI必須チェック
        if not _check_claude_available():
            console.print("\n[red bold]❌ Error: Claude Code CLI is required but not found[/red bold]")
            console.print("[yellow]Please install Claude Code:[/yellow]")
            console.print("  Visit: [cyan]https://claude.ai/download[/cyan]")
            sys.exit(1)

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

        # セッション選択
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

        initial_prompt = prompt or task

        # モデル設定
        model_map = {
            "sonnet": "sonnet",
            "opus": "opus",
            "haiku": "haiku",
        }
        model_name = model_map.get(model, "sonnet")

        # tmuxセッション作成
        from mao.orchestrator.tmux_manager import TmuxManager

        if config.defaults and config.defaults.tmux:
            grid_config = config.defaults.tmux.grid
            tmux_manager = TmuxManager(
                use_grid_layout=True,
                grid_width=grid_config.width,
                grid_height=grid_config.height,
                num_agents=num_agents,
            )
        else:
            tmux_manager = TmuxManager(
                use_grid_layout=True,
                num_agents=num_agents,
            )

        if not tmux_manager.create_session():
            console.print("[red]❌ Failed to create tmux session[/red]")
            sys.exit(1)

        console.print(f"\n[green]✓ tmux session 'mao' created[/green]")
        console.print(f"  [cyan]CTO[/cyan] + [cyan]{num_agents} Agent panes[/cyan]")

        # CTOプロンプト準備
        cto_system_prompt = _build_cto_prompt(project_path, config, num_agents)

        # CTOペイン（pane 0）でclaudeをインタラクティブ起動
        cto_pane_id = tmux_manager.grid_panes.get("cto")
        if cto_pane_id:
            # CTOログファイル
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_dir = project_path / ".mao" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            cto_log_file = log_dir / f"cto_{timestamp}.log"

            # CTOを起動
            success = tmux_manager.start_cto_with_output_capture(
                pane_id=cto_pane_id,
                log_file=cto_log_file,
                model=model_name,
                work_dir=project_path,
            )

            if success:
                console.print(f"[green]✓ CTO started in pane 0[/green]")

                # 初期プロンプトがあれば送信
                if initial_prompt:
                    import time
                    time.sleep(2)  # claude起動待ち

                    full_prompt = f"""{cto_system_prompt}

---

# ユーザータスク

{initial_prompt}

上記タスクを分析し、必要に応じてエージェントを起動してください。
"""
                    tmux_manager.send_prompt_to_claude_pane(cto_pane_id, full_prompt)
                    console.print(f"[green]✓ Initial task sent to CTO[/green]")
            else:
                console.print("[yellow]⚠ Failed to start CTO[/yellow]")

        console.print(f"\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
        console.print(f"[bold green]🎯 MAO is running![/bold green]")
        console.print(f"\n[cyan]To interact with agents:[/cyan]")
        console.print(f"  [bold]tmux attach -t mao[/bold]")
        console.print(f"\n[cyan]Tmux controls:[/cyan]")
        console.print(f"  [dim]Ctrl+B then arrow keys[/dim] - Navigate between panes")
        console.print(f"  [dim]Ctrl+B then z[/dim]          - Zoom into a pane")
        console.print(f"  [dim]Ctrl+B then d[/dim]          - Detach from session")
        console.print(f"[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")

        # ダッシュボードオプション
        if dashboard:
            console.print("\n[bold]Launching dashboard...[/bold]")
            from mao.ui.dashboard_interactive import InteractiveDashboard

            model_id_map = {
                "sonnet": "claude-sonnet-4-20250514",
                "opus": "claude-opus-4-20250514",
                "haiku": "claude-3-5-haiku-20241022",
            }

            app = InteractiveDashboard(
                project_path=project_path,
                config=config,
                use_redis=False,
                redis_url=None,
                tmux_manager=tmux_manager,
                initial_prompt=initial_prompt,
                initial_role="general",
                initial_model=model_id_map.get(model, "claude-sonnet-4-20250514"),
                session_id=selected_session_id,
                session_title=session_title,
            )

            console.print("[dim]Dashboard: Ctrl+Q=Exit | Tab=Navigate[/dim]\n")

            try:
                app.run()
            except KeyboardInterrupt:
                console.print("\n[yellow]Dashboard closed[/yellow]")
            finally:
                cleanup = console.input("\n[yellow]Destroy tmux session?[/yellow] (y/N): ")
                if cleanup.lower() == "y":
                    tmux_manager.destroy_session()
                    console.print("[green]✓ tmux session destroyed[/green]")
        else:
            # ダッシュボードなしの場合はヒントを表示
            console.print(f"\n[dim]Tip: Run 'mao dashboard' in another terminal to monitor progress[/dim]")

            # tmuxにアタッチするか確認
            attach = console.input("\n[yellow]Attach to tmux session now?[/yellow] (Y/n): ")
            if attach.lower() != "n":
                import subprocess
                try:
                    subprocess.run(["tmux", "attach", "-t", "mao"])
                except KeyboardInterrupt:
                    pass

                # 終了後のクリーンアップ
                cleanup = console.input("\n[yellow]Destroy tmux session?[/yellow] (y/N): ")
                if cleanup.lower() == "y":
                    tmux_manager.destroy_session()
                    console.print("[green]✓ tmux session destroyed[/green]")


    @main_group.command()
    @click.option(
        "--project-dir",
        "-p",
        type=click.Path(exists=True, file_okay=False, dir_okay=True),
        default=".",
        help="Project directory (default: current directory)",
    )
    def dashboard(project_dir: str):
        """Launch the MAO dashboard for monitoring agent progress.

        Use this to monitor an existing MAO session.
        The dashboard connects to the running tmux session and displays:
        - Agent status and progress
        - Task queue contents
        - Logs and metrics
        """
        project_path = Path(project_dir).resolve()

        console.print(f"\n[bold green]📊 MAO Dashboard[/bold green]")
        console.print(f"[dim]Project: {project_path}[/dim]")

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

        # 既存のtmuxセッションに接続
        from mao.orchestrator.tmux_manager import TmuxManager

        tmux_manager = TmuxManager(use_grid_layout=True)

        if not tmux_manager.session_exists():
            console.print("[yellow]⚠ No MAO tmux session found.[/yellow]")
            console.print("[dim]Start MAO first with: mao start \"your task\"[/dim]")
            sys.exit(1)

        console.print("[green]✓ Connected to existing MAO session[/green]")

        # ダッシュボード起動
        from mao.ui.dashboard_interactive import InteractiveDashboard

        app = InteractiveDashboard(
            project_path=project_path,
            config=config,
            use_redis=False,
            redis_url=None,
            tmux_manager=tmux_manager,
            initial_prompt=None,
            initial_role="general",
            initial_model="claude-sonnet-4-20250514",
            session_id=None,
            session_title=None,
        )

        console.print("[dim]Dashboard: Ctrl+Q=Exit | Tab=Navigate | Ctrl+R=Refresh[/dim]\n")

        try:
            app.run()
        except KeyboardInterrupt:
            console.print("\n[yellow]Dashboard closed[/yellow]")


def _build_cto_prompt(project_path: Path, config, num_agents: int) -> str:
    """CTOシステムプロンプトを構築"""

    # CTOロール定義を読み込み
    cto_role_file = Path(__file__).parent / "roles" / "cto.yaml"
    cto_instructions = ""

    if cto_role_file.exists():
        import yaml
        with open(cto_role_file) as f:
            cto_role = yaml.safe_load(f)
            cto_instructions = cto_role.get("system_prompt", "")

    return f"""# MAO CTO (Chief Technology Officer)

{cto_instructions}

## 環境情報

- プロジェクトパス: {project_path}
- 利用可能なエージェントペイン数: {num_agents}
- エージェント通信: YAMLキュー経由 (.mao/queue/)

## エージェント起動方法

エージェントを起動するには、以下のようなタスクYAMLを作成してください:

```yaml
# .mao/queue/tasks/agent-1.yaml
task_id: task-001
role: agent-1
prompt: |
  タスクの詳細な説明...
model: sonnet
status: ASSIGNED
```

エージェントはこのファイルを検知して処理を開始します。
完了後、結果は `.mao/queue/results/agent-1.yaml` に出力されます。

## 重要事項

1. ユーザー承認が必要な操作（破壊的変更、外部API呼び出しなど）は必ず確認してください
2. 各エージェントは独立したtmuxペインでインタラクティブに動作しています
3. タスク完了時は結果をサマリーしてユーザーに報告してください
"""
