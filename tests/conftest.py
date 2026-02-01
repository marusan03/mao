"""Pytest configuration and shared fixtures"""
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    """Create a temporary project directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mao_project_dir(temp_project_dir: Path) -> Path:
    """Create a temporary MAO project with .mao directory"""
    mao_dir = temp_project_dir / ".mao"
    mao_dir.mkdir()
    (mao_dir / "coding_standards").mkdir()
    (mao_dir / "roles").mkdir()
    (mao_dir / "context").mkdir()
    (mao_dir / "logs").mkdir()

    # Create default config
    config_file = mao_dir / "config.yaml"
    config_file.write_text("""project_name: test-project
default_language: python

agents:
  default_model: sonnet
  enable_parallel: true
  max_workers: 5

state:
  backend: sqlite

logging:
  level: INFO
  file: .mao/orchestrator.log
""")

    return temp_project_dir


@pytest.fixture
def mock_anthropic_api_key(monkeypatch):
    """Set mock ANTHROPIC_API_KEY for tests"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-mock-key-12345")


@pytest.fixture
def no_anthropic_api_key(monkeypatch):
    """Remove ANTHROPIC_API_KEY for tests"""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
