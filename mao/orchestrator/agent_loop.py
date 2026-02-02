#!/usr/bin/env python3
"""
Agent loop script that runs inside tmux panes

This script:
1. Polls for task YAML file in .mao/queue/tasks/<role>.yaml
2. When found, reads the task
3. Executes claude-code with the task prompt
4. Writes result to .mao/queue/results/<role>.yaml
5. Loops back to step 1

Usage:
    python agent_loop.py --role agent-1 --project-path /path/to/project --model sonnet
"""
import argparse
import sys
import time
from pathlib import Path
import subprocess
import tempfile

# Add mao to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mao.orchestrator.task_queue import TaskQueue, Task, TaskStatus


def execute_claude_code(
    prompt: str,
    model: str = "sonnet",
    work_dir: Optional[Path] = None,
    allow_unsafe: bool = False,
) -> tuple[bool, str, str]:
    """Execute claude-code and return result

    Args:
        prompt: Prompt to send to claude-code
        model: Model name
        work_dir: Working directory
        allow_unsafe: Allow unsafe operations

    Returns:
        (success, stdout, stderr)
    """
    try:
        # Create temporary prompt file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(prompt)
            prompt_file = Path(f.name)

        # Build command
        cmd = [
            "bash",
            "-c",
            f"cat {prompt_file} | claude-code --print --model {model}",
        ]

        if allow_unsafe:
            cmd[-1] += " --dangerously-skip-permissions"

        if work_dir:
            cmd[-1] += f" --add-dir {work_dir}"

        # Execute
        print(f"\n🚀 Executing claude-code with model: {model}")
        print(f"📝 Prompt: {prompt[:100]}...")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes timeout
            cwd=str(work_dir) if work_dir else None,
        )

        # Cleanup
        prompt_file.unlink(missing_ok=True)

        return (
            result.returncode == 0,
            result.stdout,
            result.stderr,
        )

    except subprocess.TimeoutExpired:
        return False, "", "Execution timeout (10 minutes)"
    except Exception as e:
        return False, "", str(e)


def agent_loop(
    role: str,
    project_path: Path,
    model: str = "sonnet",
    poll_interval: float = 2.0,
    allow_unsafe: bool = False,
) -> None:
    """Agent main loop

    Args:
        role: Agent role (agent-1, agent-2, etc.)
        project_path: Project root path
        model: Claude model to use
        poll_interval: Polling interval in seconds
        allow_unsafe: Allow unsafe operations
    """
    queue = TaskQueue(project_path)
    work_dir = project_path

    print(f"🤖 Agent {role} started")
    print(f"📁 Project: {project_path}")
    print(f"🔧 Model: {model}")
    print(f"⏱️  Poll interval: {poll_interval}s")
    print(f"\n{'='*60}")
    print("Waiting for tasks...")
    print(f"{'='*60}\n")

    task_count = 0

    while True:
        try:
            # Check for task
            if queue.has_task(role):
                task = queue.get_task(role)

                if task is None:
                    time.sleep(poll_interval)
                    continue

                task_count += 1
                print(f"\n{'='*60}")
                print(f"📥 Task #{task_count} received: {task.task_id}")
                print(f"{'='*60}")

                # Update status
                task.status = TaskStatus.IN_PROGRESS
                task.started_at = time.time()

                # Execute
                success, stdout, stderr = execute_claude_code(
                    prompt=task.prompt,
                    model=model,
                    work_dir=work_dir,
                    allow_unsafe=allow_unsafe,
                )

                # Update result
                task.completed_at = time.time()
                duration = task.completed_at - task.started_at

                if success:
                    task.status = TaskStatus.COMPLETED
                    task.result = stdout
                    print(f"\n✅ Task completed in {duration:.1f}s")
                    print(f"\n{'─'*60}")
                    print("Result:")
                    print(f"{'─'*60}")
                    print(stdout[:500])
                    if len(stdout) > 500:
                        print(f"... ({len(stdout) - 500} more characters)")
                    print(f"{'─'*60}\n")
                else:
                    task.status = TaskStatus.FAILED
                    task.error = stderr
                    print(f"\n❌ Task failed in {duration:.1f}s")
                    print(f"\nError: {stderr}")

                # Submit result
                queue.submit_result(task)
                print(f"📤 Result submitted\n")
                print(f"{'='*60}")
                print("Waiting for next task...")
                print(f"{'='*60}\n")

            else:
                # No task, wait
                time.sleep(poll_interval)

        except KeyboardInterrupt:
            print(f"\n\n👋 Agent {role} shutting down...")
            break
        except Exception as e:
            print(f"\n⚠️  Error in agent loop: {e}")
            print("Continuing...")
            time.sleep(poll_interval)


def main() -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="MAO Agent Loop - Runs inside tmux pane"
    )
    parser.add_argument(
        "--role",
        required=True,
        help="Agent role (e.g., agent-1, agent-2)",
    )
    parser.add_argument(
        "--project-path",
        type=Path,
        required=True,
        help="Project root path",
    )
    parser.add_argument(
        "--model",
        default="sonnet",
        help="Claude model (sonnet, opus, haiku)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Polling interval in seconds",
    )
    parser.add_argument(
        "--allow-unsafe",
        action="store_true",
        help="Allow unsafe operations (--dangerously-skip-permissions)",
    )

    args = parser.parse_args()

    # Run agent loop
    agent_loop(
        role=args.role,
        project_path=args.project_path,
        model=args.model,
        poll_interval=args.poll_interval,
        allow_unsafe=args.allow_unsafe,
    )


if __name__ == "__main__":
    from typing import Optional
    main()
