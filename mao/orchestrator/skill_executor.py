"""
Skill execution system
"""
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess
import shlex
from dataclasses import dataclass

from mao.orchestrator.skill_manager import SkillDefinition


@dataclass
class SkillExecutionResult:
    """Skill実行結果"""

    success: bool
    output: str
    error: str
    exit_code: int
    duration: float  # seconds


class SkillExecutor:
    """Skill実行クラス"""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.skills_dir = project_path / ".mao" / "skills"

    def execute_skill(
        self, skill: SkillDefinition, parameters: Dict[str, Any]
    ) -> SkillExecutionResult:
        """Skillを実行"""
        import time

        start_time = time.time()

        try:
            # パラメータ検証
            self._validate_parameters(skill, parameters)

            # スクリプトがある場合はスクリプトを実行
            if skill.script:
                result = self._execute_script(skill, parameters)
            else:
                # コマンドリストを実行
                result = self._execute_commands(skill, parameters)

            duration = time.time() - start_time
            result.duration = duration

            return result

        except Exception as e:
            duration = time.time() - start_time
            return SkillExecutionResult(
                success=False,
                output="",
                error=str(e),
                exit_code=1,
                duration=duration,
            )

    def _validate_parameters(
        self, skill: SkillDefinition, parameters: Dict[str, Any]
    ) -> None:
        """パラメータを検証"""
        # 必須パラメータチェック
        for param_def in skill.parameters:
            param_name = param_def["name"]
            is_required = param_def.get("required", False)

            if is_required and param_name not in parameters:
                raise ValueError(f"Required parameter missing: {param_name}")

        # デフォルト値を適用
        for param_def in skill.parameters:
            param_name = param_def["name"]
            if param_name not in parameters and "default" in param_def:
                parameters[param_name] = param_def["default"]

    def _execute_script(
        self, skill: SkillDefinition, parameters: Dict[str, Any]
    ) -> SkillExecutionResult:
        """スクリプトファイルを実行"""
        script_file = self.skills_dir / f"{skill.name}.sh"

        if not script_file.exists():
            raise FileNotFoundError(f"Script file not found: {script_file}")

        # パラメータをコマンドライン引数として渡す
        args = []
        for param_def in skill.parameters:
            param_name = param_def["name"]
            if param_name in parameters:
                args.append(str(parameters[param_name]))

        # スクリプト実行
        try:
            result = subprocess.run(
                [str(script_file)] + args,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=300,  # 5分タイムアウト
            )

            return SkillExecutionResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
                exit_code=result.returncode,
                duration=0,  # 後で設定される
            )

        except subprocess.TimeoutExpired:
            return SkillExecutionResult(
                success=False,
                output="",
                error="Execution timeout (5 minutes)",
                exit_code=124,
                duration=300,
            )

    def _execute_commands(
        self, skill: SkillDefinition, parameters: Dict[str, Any]
    ) -> SkillExecutionResult:
        """コマンドリストを実行"""
        all_output = []
        all_errors = []

        for cmd_entry in skill.commands:
            # コマンドエントリーは文字列またはdict
            if isinstance(cmd_entry, str):
                command = cmd_entry
            elif isinstance(cmd_entry, dict):
                command = cmd_entry.get("command")
                description = cmd_entry.get("description", "")
                if description:
                    all_output.append(f"# {description}")
            else:
                continue

            # パラメータを置換
            command = self._substitute_parameters(command, parameters)

            # コマンド実行
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=self.project_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                all_output.append(f"$ {command}")
                all_output.append(result.stdout)

                if result.returncode != 0:
                    all_errors.append(f"Command failed: {command}")
                    all_errors.append(result.stderr)

                    return SkillExecutionResult(
                        success=False,
                        output="\n".join(all_output),
                        error="\n".join(all_errors),
                        exit_code=result.returncode,
                        duration=0,
                    )

            except subprocess.TimeoutExpired:
                return SkillExecutionResult(
                    success=False,
                    output="\n".join(all_output),
                    error=f"Command timeout: {command}",
                    exit_code=124,
                    duration=60,
                )

        return SkillExecutionResult(
            success=True,
            output="\n".join(all_output),
            error="\n".join(all_errors),
            exit_code=0,
            duration=0,
        )

    def _substitute_parameters(self, command: str, parameters: Dict[str, Any]) -> str:
        """コマンド内のパラメータを置換"""
        # ${param_name} 形式のプレースホルダーを置換
        result = command
        for key, value in parameters.items():
            result = result.replace(f"${{{key}}}", str(value))
            result = result.replace(f"${key}", str(value))

        return result

    def dry_run(
        self, skill: SkillDefinition, parameters: Dict[str, Any]
    ) -> List[str]:
        """ドライラン（実際には実行せず、実行予定のコマンドを返す）"""
        commands = []

        if skill.script:
            script_file = self.skills_dir / f"{skill.name}.sh"
            args = []
            for param_def in skill.parameters:
                param_name = param_def["name"]
                if param_name in parameters:
                    args.append(str(parameters[param_name]))

            commands.append(f"{script_file} {' '.join(args)}")

        else:
            for cmd_entry in skill.commands:
                if isinstance(cmd_entry, str):
                    command = cmd_entry
                elif isinstance(cmd_entry, dict):
                    command = cmd_entry.get("command", "")
                else:
                    continue

                command = self._substitute_parameters(command, parameters)
                commands.append(command)

        return commands
