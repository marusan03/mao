"""
Task dispatcher for launching agents
"""
import yaml
from pathlib import Path
from typing import Dict, Any


class TaskDispatcher:
    """Claude Code の Task tool を使ってエージェントを起動"""

    def __init__(self):
        self.roles = self._load_roles()

    def _load_roles(self) -> Dict[str, Any]:
        """全ロール定義を読み込み"""
        roles = {}

        # まず組み込みロールを探す
        # パッケージインストール後は mao/roles/ から読み込む
        # 開発中は相対パスから読み込む
        roles_dir = Path(__file__).parent.parent / "roles"

        if not roles_dir.exists():
            # パッケージとしてインストールされている場合
            import mao
            package_path = Path(mao.__file__).parent
            roles_dir = package_path / "roles"

        if roles_dir.exists():
            for yaml_file in roles_dir.rglob("*.yaml"):
                try:
                    with open(yaml_file) as f:
                        role_config = yaml.safe_load(f)
                        if role_config and "name" in role_config:
                            roles[role_config["name"]] = role_config
                except Exception as e:
                    print(f"Warning: Failed to load role from {yaml_file}: {e}")

        return roles

    def build_agent_prompt(self, role_name: str, task: Dict) -> str:
        """ロール設定からプロンプトを構築"""
        if role_name not in self.roles:
            raise ValueError(f"Unknown role: {role_name}")

        role = self.roles[role_name]

        # ベースプロンプト読み込み
        prompt_file = Path(role["prompt_file"])
        if not prompt_file.exists():
            # 相対パスの場合、ロールディレクトリからの相対パスとして解決
            roles_dir = Path(__file__).parent.parent / "roles"
            prompt_file = roles_dir / role["prompt_file"]

        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {role['prompt_file']}")

        with open(prompt_file) as f:
            base_prompt = f.read()

        # コーディング規約読み込み（該当する場合）
        coding_standards = ""
        if "coding_standards" in role:
            standards = []
            for std_file in role["coding_standards"]:
                std_path = Path(std_file)
                if std_path.exists():
                    with open(std_path) as f:
                        standards.append(f.read())
            if standards:
                coding_standards = (
                    "\n\n# Coding Standards\n\n" + "\n\n---\n\n".join(standards)
                )

        # 言語設定読み込み（該当する場合）
        lang_config = ""
        if "language_config" in role:
            lang_config_path = Path(role["language_config"])
            if lang_config_path.exists():
                with open(lang_config_path) as f:
                    lang_config = (
                        "\n\n# Language Configuration\n\n```yaml\n"
                        + f.read()
                        + "\n```"
                    )

        # 追加コンテキスト読み込み
        additional_context = ""
        if "additional_context" in role:
            contexts = []
            for ctx_file in role["additional_context"]:
                ctx_path = Path(ctx_file)
                if ctx_path.exists():
                    with open(ctx_path) as f:
                        contexts.append(f.read())
            if contexts:
                additional_context = (
                    "\n\n# Additional Context\n\n" + "\n\n---\n\n".join(contexts)
                )

        # 最終プロンプト構築
        full_prompt = f"""
{base_prompt}

{coding_standards}

{lang_config}

{additional_context}

---

# Your Current Task

{task['description']}

## Task Details
- Task ID: {task['id']}
- Priority: {task.get('priority', 'normal')}

## Expected Output
{task.get('expected_output', 'Complete the task and report results.')}
"""
        return full_prompt

    async def dispatch_task(self, role_name: str, task: Dict) -> Dict[str, Any]:
        """タスクを該当ロールのエージェントにディスパッチ"""
        role = self.roles[role_name]
        prompt = self.build_agent_prompt(role_name, task)

        # Claude Code の Task tool を呼び出す形をシミュレート
        # 実際にはClaude Code APIまたはCLIを通じて呼び出す
        agent_config = {
            "subagent_type": role["subagent_type"],
            "model": role.get("model", "sonnet"),
            "description": f"{role['display_name']} - {task['description'][:50]}",
            "prompt": prompt,
        }

        # TODO: ここで実際にTaskを起動
        # 例: claude_code.task(**agent_config)
        return agent_config
