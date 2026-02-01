"""
Project configuration loader
"""
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field

from mao.config import ConfigLoader


class AgentConfig(BaseModel):
    """Agent configuration"""
    default_model: str = "sonnet"
    enable_parallel: bool = True
    max_workers: int = 5


class StateConfig(BaseModel):
    """State management configuration"""
    backend: str = "sqlite"  # sqlite or redis


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = "INFO"
    file: str = ".mao/orchestrator.log"


class SecurityConfig(BaseModel):
    """Security configuration"""
    allow_unsafe_operations: bool = False  # --dangerously-skip-permissions
    allow_file_write: bool = True
    allow_command_execution: bool = True


class ModelPricing(BaseModel):
    """Model pricing information"""
    input: float
    output: float
    description: Optional[str] = None


class PricingConfig(BaseModel):
    """Pricing configuration"""
    models: Dict[str, ModelPricing] = Field(default_factory=dict)
    default: ModelPricing = Field(
        default_factory=lambda: ModelPricing(input=3.0, output=15.0)
    )


class TmuxGridConfig(BaseModel):
    """Tmux grid layout configuration"""
    width: int = 240
    height: int = 60
    num_workers: int = 8
    default_layout: str = "tiled"


class TmuxConfig(BaseModel):
    """Tmux configuration"""
    grid: TmuxGridConfig = Field(default_factory=TmuxGridConfig)


class ExecutionConfig(BaseModel):
    """Execution configuration"""
    max_tokens: int = 4096
    temperature: float = 1.0
    timeout: int = 300


class DefaultsConfig(BaseModel):
    """Default configuration values"""
    tmux: TmuxConfig = Field(default_factory=TmuxConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)


class ProjectConfig(BaseModel):
    """Project configuration"""
    project_name: str
    default_language: str = "python"
    agents: AgentConfig = Field(default_factory=AgentConfig)
    state: StateConfig = Field(default_factory=StateConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    # Pricing and defaults (loaded from global config files)
    pricing: Optional[PricingConfig] = None
    defaults: Optional[DefaultsConfig] = None

    # Internal fields
    config_file: Optional[Path] = None
    project_path: Optional[Path] = None


class ProjectLoader:
    """Load and manage project configuration"""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.mao_dir = project_path / ".mao"
        self.config_file = self.mao_dir / "config.yaml"
        self.config_loader = ConfigLoader()
        self.custom_standards_dir = self.mao_dir / "coding_standards"

        # Global config files
        self.global_config_dir = Path(__file__).parent.parent / "config"
        self.pricing_file = self.global_config_dir / "pricing.yaml"
        self.defaults_file = self.global_config_dir / "defaults.yaml"

    def load(self) -> ProjectConfig:
        """Load project configuration"""
        if not self.config_file.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_file}\n"
                "Run 'mao init' to initialize the project"
            )

        with open(self.config_file) as f:
            config_data = yaml.safe_load(f)

        config = ProjectConfig(**config_data)
        config.config_file = self.config_file
        config.project_path = self.project_path

        # Load global pricing configuration
        config.pricing = self._load_pricing()

        # Load global defaults configuration
        config.defaults = self._load_defaults()

        return config

    def _load_pricing(self) -> PricingConfig:
        """Load pricing configuration from global config file"""
        if not self.pricing_file.exists():
            # Return default pricing if file doesn't exist
            return PricingConfig()

        with open(self.pricing_file) as f:
            pricing_data = yaml.safe_load(f)

        return PricingConfig(**pricing_data)

    def _load_defaults(self) -> DefaultsConfig:
        """Load defaults configuration from global config file"""
        if not self.defaults_file.exists():
            # Return default values if file doesn't exist
            return DefaultsConfig()

        with open(self.defaults_file) as f:
            defaults_data = yaml.safe_load(f)

        return DefaultsConfig(**defaults_data)

    def save(self, config: ProjectConfig) -> None:
        """Save project configuration"""
        self.mao_dir.mkdir(exist_ok=True)

        config_data = config.model_dump(exclude={"config_file", "project_path"})

        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

    def get_coding_standards_context(self, language: Optional[str] = None) -> str:
        """コーディング規約のコンテキストを取得

        Args:
            language: 言語名（Noneの場合はデフォルト言語を使用）

        Returns:
            エージェントプロンプトに含めるコンテキスト
        """
        lang = language or self.load().default_language
        return self.config_loader.get_language_prompt_context(
            lang, self.custom_standards_dir
        )

    def list_available_languages(self) -> list[str]:
        """利用可能な言語の一覧"""
        return self.config_loader.list_available_languages()
