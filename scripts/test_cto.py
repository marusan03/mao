#!/usr/bin/env python3
"""
CTO Direct Test - TUIをバイパスしてCTOプロンプトをテスト

Usage:
    python3 scripts/test_cto.py
    python3 scripts/test_cto.py --task "Your custom task"
"""
import subprocess
import sys
import argparse
from pathlib import Path


def load_cto_prompt() -> str:
    """CTOプロンプトを読み込み"""
    script_dir = Path(__file__).parent
    cto_prompt_file = script_dir.parent / "mao/agents/cto_prompt.md"

    if not cto_prompt_file.exists():
        print(f"❌ CTO prompt not found: {cto_prompt_file}")
        sys.exit(1)

    with open(cto_prompt_file) as f:
        return f.read()


def build_test_prompt(cto_prompt: str, task: str, num_agents: int = 3) -> str:
    """テストプロンプトを構築（task_dispatcher.pyと同じロジック）"""
    return f"""{cto_prompt}

---

# User Task

{task}

**Available Agents**: {num_agents}

Please analyze this task and provide the decomposition in YAML format.
"""


def test_cto(task: str, timeout: int = 60) -> bool:
    """
    CTOをテストする

    Args:
        task: テストタスク
        timeout: タイムアウト秒数

    Returns:
        成功したかどうか
    """
    print("=== CTO Direct Test ===")
    print(f"Task: {task}")
    print("")

    # CTOプロンプトを読み込み
    print("[1/4] Loading CTO prompt...")
    cto_prompt = load_cto_prompt()
    print(f"      ✅ Loaded {len(cto_prompt)} characters")

    # フルプロンプトを構築
    print("[2/4] Building full prompt...")
    full_prompt = build_test_prompt(cto_prompt, task)
    print(f"      ✅ Full prompt: {len(full_prompt)} characters")

    # プロンプト検証
    print("[3/4] Validating prompt contains CRITICAL instructions...")
    critical_checks = [
        ("CRITICAL REQUIREMENT", "Critical section"),
        ("YOU MUST ACTUALLY EXECUTE TASKS", "Execution mandate"),
        ("Step 2: Execute", "Two-step process"),
    ]

    all_present = True
    for keyword, description in critical_checks:
        if keyword in full_prompt:
            print(f"      ✅ {description}")
        else:
            print(f"      ❌ Missing: {description}")
            all_present = False

    if not all_present:
        print("\n❌ FAIL: Prompt missing critical instructions")
        return False

    # Claude CLIで実行
    print("[4/4] Calling Claude CLI (--print mode)...")
    print("      This may take 30-60 seconds...")
    print("")

    try:
        # 標準入力からプロンプトを渡す
        result = subprocess.run(
            [
                "claude",
                "--print",
                "--model", "sonnet",
                "--dangerously-skip-permissions"
            ],
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        output = result.stdout
        stderr = result.stderr

        if stderr and "error" in stderr.lower():
            print(f"⚠️  Stderr: {stderr[:200]}")

        print("="*60)
        print("CTO Response:")
        print("="*60)
        print(output[:1500])  # 最初の1500文字
        if len(output) > 1500:
            print(f"\n... (truncated, total {len(output)} chars)")
        print("="*60)
        print("")

        # 分析
        print("=== Analysis ===")

        has_yaml = "```yaml" in output or "subtasks:" in output or "tasks:" in output
        has_step_mention = "step" in output.lower()
        mentions_tool = "task tool" in output.lower() or "task(" in output.lower()
        has_invoke = "<invoke" in output or "function_calls" in output

        print(f"{'✅' if has_yaml else '❌'} YAML plan output")
        print(f"{'✅' if has_step_mention else '❌'} Step-based process mentioned")
        print(f"{'✅' if mentions_tool else '❌'} Task tool mentioned")
        print(f"{'✅' if has_invoke else '⚠️ '} Actual tool invocation detected")

        print("")

        # 判定
        if has_yaml and (mentions_tool or has_invoke):
            print("✅ SUCCESS: CTO follows the updated prompt!")
            print("   - Outputs YAML plan")
            print("   - Mentions/calls Task tool")
            return True
        elif has_yaml:
            print("⚠️  PARTIAL SUCCESS: CTO outputs plan")
            print("   - However, Task tool execution unclear")
            print("   - Prompt may need further strengthening")
            return True  # 部分的成功として扱う
        else:
            print("❌ FAIL: CTO does not follow expected format")
            return False

    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT: Claude CLI took longer than {timeout}s")
        print("   Try increasing timeout or using shorter task")
        return False
    except FileNotFoundError:
        print("❌ ERROR: 'claude' command not found")
        print("   Make sure Claude Code CLI is installed")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test CTO prompt without TUI")
    parser.add_argument(
        "--task",
        default="Create a simple contact form with frontend and backend",
        help="Task to give to CTO"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds (default: 60)"
    )

    args = parser.parse_args()

    success = test_cto(args.task, args.timeout)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
