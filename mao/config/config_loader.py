"""
Configuration loader for languages and coding standards
"""
from pathlib import Path
from typing import Optional, Dict, Any
import yaml


class LanguageConfig:
    """言語設定"""

    def __init__(self, config_data: Dict[str, Any]):
        self.name = config_data.get("name", "")
        self.file_extensions = config_data.get("file_extensions", [])
        self.tools = config_data.get("tools", {})
        self.defaults = config_data.get("defaults", {})
        self.standards = config_data.get("standards", [])
        self.recommended_packages = config_data.get("recommended_packages", {})
        self.recommended_tools = config_data.get("recommended_tools", [])

    @property
    def formatter(self) -> Optional[str]:
        """フォーマッター"""
        return self.tools.get("formatter")

    @property
    def linter(self) -> Optional[str]:
        """リンター"""
        return self.tools.get("linter")

    @property
    def test_framework(self) -> Optional[str]:
        """テストフレームワーク"""
        return self.tools.get("test_framework")


class CodingStandards:
    """コーディング規約"""

    def __init__(self, content: str):
        self.content = content

    def __str__(self) -> str:
        return self.content


class ConfigLoader:
    """設定ローダー"""

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            # デフォルトはパッケージ内の config ディレクトリ
            config_dir = Path(__file__).parent
        self.config_dir = config_dir

        self.languages_dir = config_dir / "languages"
        self.standards_dir = config_dir / "coding_standards"

    def load_language_config(self, language: str) -> Optional[LanguageConfig]:
        """言語設定を読み込む

        Args:
            language: 言語名 (例: "python", "typescript")

        Returns:
            LanguageConfig または None
        """
        config_file = self.languages_dir / f"{language}.yaml"

        if not config_file.exists():
            return None

        with open(config_file) as f:
            config_data = yaml.safe_load(f)

        return LanguageConfig(config_data)

    def load_coding_standards(
        self, language: str, custom_dir: Optional[Path] = None
    ) -> Optional[CodingStandards]:
        """コーディング規約を読み込む

        Args:
            language: 言語名
            custom_dir: カスタム規約ディレクトリ（プロジェクト固有）

        Returns:
            CodingStandards または None
        """
        # まずデフォルトを読み込む
        default_file = self.standards_dir / f"{language}.md"
        content_parts = []

        if default_file.exists():
            with open(default_file) as f:
                content_parts.append(f"# {language.title()} コーディング規約（デフォルト）\n")
                content_parts.append(f.read())

        # カスタム規約があれば追加
        if custom_dir:
            custom_file = custom_dir / f"{language}_custom.md"
            if custom_file.exists():
                with open(custom_file) as f:
                    content_parts.append("\n\n# プロジェクト固有の規約\n")
                    content_parts.append(f.read())

        if not content_parts:
            return None

        return CodingStandards("".join(content_parts))

    def get_language_prompt_context(
        self, language: str, custom_standards_dir: Optional[Path] = None
    ) -> str:
        """エージェントプロンプトに含める言語コンテキストを生成

        Args:
            language: 言語名
            custom_standards_dir: カスタム規約ディレクトリ

        Returns:
            プロンプトに含めるコンテキスト文字列
        """
        parts = []

        # 言語設定
        lang_config = self.load_language_config(language)
        if lang_config:
            parts.append(f"## 言語: {lang_config.name}\n")

            if lang_config.tools:
                parts.append("### 推奨ツール")
                if lang_config.formatter:
                    parts.append(f"- フォーマッター: {lang_config.formatter}")
                if lang_config.linter:
                    parts.append(f"- リンター: {lang_config.linter}")
                if lang_config.test_framework:
                    parts.append(f"- テストフレームワーク: {lang_config.test_framework}")
                parts.append("")

            if lang_config.defaults:
                parts.append("### デフォルト設定")
                for key, value in lang_config.defaults.items():
                    parts.append(f"- {key}: {value}")
                parts.append("")

        # コーディング規約
        standards = self.load_coding_standards(language, custom_standards_dir)
        if standards:
            parts.append("## コーディング規約\n")
            parts.append(standards.content)

        return "\n".join(parts)

    def list_available_languages(self) -> list[str]:
        """利用可能な言語の一覧

        Returns:
            言語名のリスト
        """
        if not self.languages_dir.exists():
            return []

        languages = []
        for file in self.languages_dir.glob("*.yaml"):
            languages.append(file.stem)

        return sorted(languages)
