"""
Project configuration loader
"""
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field


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


class ProjectConfig(BaseModel):
    """Project configuration"""
    project_name: str
    default_language: str = "python"
    agents: AgentConfig = Field(default_factory=AgentConfig)
    state: StateConfig = Field(default_factory=StateConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Internal fields
    config_file: Optional[Path] = None
    project_path: Optional[Path] = None


class ProjectLoader:
    """Load and manage project configuration"""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.mao_dir = project_path / ".mao"
        self.config_file = self.mao_dir / "config.yaml"

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

        return config

    def save(self, config: ProjectConfig) -> None:
        """Save project configuration"""
        self.mao_dir.mkdir(exist_ok=True)

        config_data = config.model_dump(exclude={"config_file", "project_path"})

        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
