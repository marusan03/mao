"""
Skill definition formatter for agent prompts
"""
from typing import List, Dict, Any

from mao.orchestrator.skill_manager import SkillDefinition


class SkillFormatter:
    """スキル定義をプロンプト用にフォーマット"""

    def format_skill_for_prompt(self, skill: SkillDefinition) -> str:
        """単一スキルをプロンプト用にフォーマット"""
        lines = []

        # ヘッダー
        lines.append(f"### /{skill.name}")

        # 説明（複数行の場合は最初の段落のみ）
        if skill.description:
            desc = skill.description.strip()
            # 最初の空行までを取得
            first_para = desc.split("\n\n")[0].replace("\n", " ").strip()
            lines.append(f"**Description**: {first_para}")

        # パラメータテーブル
        if skill.parameters:
            lines.append("\n**Parameters**:")
            lines.append("| Parameter | Type | Required | Default | Description |")
            lines.append("|-----------|------|----------|---------|-------------|")

            for param in skill.parameters:
                name = param.get("name", "")
                param_type = param.get("type", "string")
                required = "Yes" if param.get("required", False) else "No"
                default = param.get("default")
                if default is None:
                    default = "-"
                elif default == "":
                    default = '""'
                desc = param.get("description", "").replace("\n", " ")

                lines.append(f"| {name} | {param_type} | {required} | {default} | {desc} |")

                # choices がある場合は追加行
                if "choices" in param:
                    choices = ", ".join(str(c) for c in param["choices"])
                    lines.append(f"\n  **Valid values for `{name}`**: {choices}")

        # スクリプト処理の要約
        if skill.script:
            summary = self._summarize_script(skill.script)
            if summary:
                lines.append(f"\n**Operations**: {summary}")

        # 使用例（metadata.examples または examples）
        examples = skill.data.get("metadata", {}).get("examples", []) or skill.examples
        if examples:
            lines.append("\n**Examples**:")
            for ex in examples[:3]:  # 最大3つ
                if isinstance(ex, dict):
                    if "command" in ex:
                        lines.append(f"- `{ex['command']}`")
                    elif "description" in ex:
                        lines.append(f"- {ex['description']}")
                elif isinstance(ex, str):
                    lines.append(f"- `{ex}`")

        return "\n".join(lines)

    def format_all_skills(self, skills: List[SkillDefinition]) -> str:
        """全スキルをプロンプト用セクションにフォーマット"""
        if not skills:
            return ""

        sections = [
            "## Available Skills",
            "",
            "The following skills are available. Use them as slash commands.",
            "",
        ]

        for skill in skills:
            sections.append(self.format_skill_for_prompt(skill))
            sections.append("")  # スキル間の空行

        return "\n".join(sections)

    def _summarize_script(self, script: str) -> str:
        """スクリプトの処理内容を要約"""
        operations = []

        script_lower = script.lower()

        # SQLite操作
        if "sqlite3" in script_lower:
            if "insert" in script_lower:
                operations.append("SQLite INSERT")
            elif "update" in script_lower:
                operations.append("SQLite UPDATE")
            elif "select" in script_lower:
                operations.append("SQLite SELECT")
            else:
                operations.append("SQLite operations")

        # ファイル書き込み
        if "json.dump" in script_lower or ("open(" in script_lower and "'w'" in script_lower):
            operations.append("File write")

        # ファイル読み込み
        if "json.load" in script_lower or ("open(" in script_lower and "'r'" in script_lower):
            operations.append("File read")

        # シェル実行
        if "subprocess" in script_lower or "os.system" in script_lower:
            operations.append("Shell execution")

        # HTTP リクエスト
        if "http" in script_lower or "requests." in script_lower:
            operations.append("HTTP request")

        # Git 操作
        if "git " in script_lower:
            operations.append("Git operations")

        return ", ".join(operations) if operations else ""
