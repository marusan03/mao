"""
CLI feedback improve command - Work on feedback with MAO
"""
from pathlib import Path

import click
from rich.console import Console

from mao import cli_completion
from mao.cli_improvements import _is_mao_project

console = Console()


def register_improve_command(feedback_group: click.Group):
    """Register improve command to feedback group"""

    @feedback_group.command("improve")
    @click.argument("feedback_id", shell_complete=cli_completion.complete_feedback_ids)
    @click.option("--project-dir", default=".", help="Project directory")
    @click.option("--model", default="sonnet", type=click.Choice(["sonnet", "opus", "haiku"]), help="Model to use", shell_complete=cli_completion.complete_models)
    @click.option("--no-issue", is_flag=True, help="Skip creating GitHub issue")
    @click.option("--no-pr", is_flag=True, help="Skip creating GitHub PR")
    def improve_feedback(feedback_id: str, project_dir: str, model: str, no_issue: bool, no_pr: bool):
        """Work on feedback - run MAO to improve MAO with issue/PR creation (MAO project only)"""
        from mao.orchestrator.feedback_manager import FeedbackManager
        from mao.orchestrator.project_loader import ProjectLoader
        from mao.ui.dashboard_interactive import InteractiveDashboard
        import subprocess
        import json

        project_path = Path(project_dir).resolve()

        if not _is_mao_project(project_path):
            console.print("[bold red]✗ Feedback improve can only be run on MAO project[/bold red]")
            console.print("[dim]Feedback can be created from any project, but improved only on MAO[/dim]")
            console.print("[dim]For other projects, use 'mao project' commands instead[/dim]")
            return

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

        console.print(f"\n[bold cyan]📋 Feedback: {fb.title}[/bold cyan]")
        console.print(f"Category: {fb.category} | Priority: {fb.priority}")
        console.print(f"Description:\n{fb.description}\n")

        # Git リポジトリかチェック
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=project_path,
                capture_output=True,
                timeout=5,
            )
            is_git_repo = result.returncode == 0
        except Exception:
            is_git_repo = False

        if not is_git_repo:
            console.print("[bold red]✗ Not a git repository[/bold red]")
            return

        # GitHub リポジトリかチェック
        try:
            result = subprocess.run(
                ["gh", "repo", "view", "--json", "nameWithOwner"],
                cwd=project_path,
                capture_output=True,
                timeout=5,
            )
            is_github_repo = result.returncode == 0
            if is_github_repo:
                repo_info = json.loads(result.stdout.decode())
                repo_name = repo_info.get("nameWithOwner", "")
        except Exception:
            is_github_repo = False
            repo_name = ""

        # GitHub issue を作成
        issue_number = None
        if not no_issue and is_github_repo:
            console.print("\n[bold]Creating GitHub issue...[/bold]")

            labels = {
                "bug": "bug",
                "feature": "enhancement",
                "improvement": "enhancement",
                "documentation": "documentation",
            }
            label = labels.get(fb.category, "enhancement")

            priority_labels = {
                "low": "priority: low",
                "medium": "priority: medium",
                "high": "priority: high",
                "critical": "priority: critical",
            }
            priority_label = priority_labels.get(fb.priority, "priority: medium")

            issue_body = f"""## Feedback ID
{fb.id}

## Category
{fb.category}

## Priority
{fb.priority}

## Description
{fb.description}

## Session Info
- Agent: {fb.agent_id}
- Session: {fb.session_id}
- Created: {fb.created_at}

---
*This issue was automatically created from MAO feedback system.*
"""

            try:
                result = subprocess.run(
                    [
                        "gh", "issue", "create",
                        "--title", fb.title,
                        "--body", issue_body,
                        "--label", label,
                        "--label", priority_label,
                        "--label", "mao-feedback",
                    ],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    issue_url = result.stdout.strip()
                    issue_number = issue_url.split("/")[-1]
                    console.print(f"[bold green]✓ Issue created: #{issue_number}[/bold green]")
                    console.print(f"[dim]{issue_url}[/dim]")
                else:
                    console.print(f"[bold yellow]⚠ Failed to create issue: {result.stderr}[/bold yellow]")
            except Exception as e:
                console.print(f"[bold yellow]⚠ Failed to create issue: {e}[/bold yellow]")

        # WorktreeManager を初期化
        from mao.orchestrator.worktree_manager import WorktreeManager
        worktree_manager = WorktreeManager(project_path=project_path)

        manager.update_status(feedback_id, "in_progress")

        safe_title = ''.join(c if c.isalnum() or c in '-_' else '-' for c in fb.title[:30])
        if issue_number:
            branch_name = f"feedback/{issue_number}_{fb.id[-8:]}-{safe_title}"
        else:
            branch_name = f"feedback/{fb.id[-8:]}-{safe_title}"

        console.print(f"\n[bold]Creating feedback worktree: {branch_name}[/bold]")
        feedback_worktree = worktree_manager.create_feedback_worktree(
            feedback_id=fb.id[-8:],
            branch_name=branch_name
        )

        if not feedback_worktree:
            console.print("[bold red]✗ Failed to create feedback worktree[/bold red]")
            manager.update_status(feedback_id, "pending")
            return

        console.print(f"[bold green]✓ Worktree created: {feedback_worktree}[/bold green]")

        try:
            loader = ProjectLoader(feedback_worktree)
            config = loader.load()
        except Exception as e:
            console.print(f"[bold red]✗ Failed to load config: {e}[/bold red]")
            worktree_manager.remove_worktree(feedback_worktree)
            manager.update_status(feedback_id, "pending")
            return

        console.print("\n[bold green]🚀 Starting MAO to work on this feedback...[/bold green]")
        if issue_number:
            console.print(f"[dim]Working on issue #{issue_number}[/dim]\n")

        prompt = f"""MAO プロジェクトの改善フィードバック:

【タイトル】{fb.title}

【カテゴリ】{fb.category}

【優先度】{fb.priority}

【GitHub Issue】{"#" + issue_number if issue_number else "なし"}

【詳細】
{fb.description}

このフィードバックに基づいて、MAO プロジェクトを改善してください。
必要なファイルの変更、テストの追加、ドキュメントの更新などを行ってください。

⚠️ 重要: 各ワーカーは独自の git worktree で作業します。
ワーカー用 worktree は自動的に作成されます。

完了したら、変更内容を git commit してください。
コミットメッセージには issue 番号（#{issue_number if issue_number else "N/A"}）を含めてください。"""

        model_map = {
            "sonnet": "claude-sonnet-4-20250514",
            "opus": "claude-opus-4-20250514",
            "haiku": "claude-3-5-haiku-20241022",
        }
        model_id = model_map.get(model, "claude-sonnet-4-20250514")

        app = InteractiveDashboard(
            project_path=feedback_worktree,
            config=config,
            use_redis=False,
            initial_prompt=prompt,
            initial_model=model_id,
            feedback_branch=branch_name,
            worktree_manager=worktree_manager,
        )

        success = False
        try:
            app.run()
            success = True

            console.print("\n[bold]Work completed![/bold]")
            console.print("[dim]CTOが /commit と /pr スキルでPRを作成済みです[/dim]")

            manager.update_status(feedback_id, "completed")
            console.print("[bold green]✓ Feedback marked as completed[/bold green]")

        except KeyboardInterrupt:
            console.print("\n[bold yellow]⚠ Interrupted by user[/bold yellow]")
        except Exception as e:
            console.print(f"[bold red]✗ Error: {e}[/bold red]")
        finally:
            console.print("\n[bold]Cleaning up worktrees...[/bold]")
            cleanup_count = worktree_manager.cleanup_worktrees()
            console.print(f"[bold green]✓ Cleaned up {cleanup_count} worktrees[/bold green]")

            if not success:
                manager.update_status(feedback_id, "pending")

        # 連続改善: 次のfeedbackを提案
        if success:
            pending_feedbacks = [
                f for f in manager.list_feedbacks()
                if f.status == "pending"
            ]

            if pending_feedbacks:
                console.print(f"\n[bold cyan]📋 次のフィードバック ({len(pending_feedbacks)}件残り)[/bold cyan]\n")

                from rich.table import Table
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("#", style="dim", width=4)
                table.add_column("タイトル", width=40)
                table.add_column("カテゴリ", width=12)
                table.add_column("優先度", width=10)

                for idx, f in enumerate(pending_feedbacks[:3], 1):
                    table.add_row(
                        str(idx),
                        f.title,
                        f.category,
                        f.priority,
                    )

                console.print(table)

                console.print("\n[yellow]オプション:[/yellow]")
                console.print("  [cyan]1-3[/cyan]: 次のフィードバックを改善")
                console.print("  [cyan]n[/cyan]:   終了")

                choice = console.input("\n[bold]次のフィードバックに進みますか？[/bold] ").strip().lower()

                if choice.isdigit():
                    idx = int(choice)
                    if 1 <= idx <= min(3, len(pending_feedbacks)):
                        next_feedback = pending_feedbacks[idx - 1]
                        console.print(f"\n[green]✓ 次のフィードバックに進みます: {next_feedback.title}[/green]")

                        from click import Context
                        ctx = Context(improve_feedback)
                        ctx.invoke(
                            improve_feedback,
                            feedback_id=next_feedback.id,
                            project_dir=project_dir,
                            model=model,
                            no_issue=no_issue,
                            no_pr=no_pr,
                        )
                        return

            console.print("\n[green]✅ すべてのフィードバック改善が完了しました！[/green]")
