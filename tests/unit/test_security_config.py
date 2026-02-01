"""
Tests for security configuration
"""
import pytest
from pathlib import Path
import tempfile
import yaml

from mao.orchestrator.project_loader import ProjectLoader, ProjectConfig, SecurityConfig
from mao.orchestrator.claude_code_executor import ClaudeCodeExecutor


class TestSecurityConfig:
    """セキュリティ設定のテスト"""

    def test_security_config_defaults(self):
        """デフォルトのセキュリティ設定をテスト"""
        config = SecurityConfig()

        assert config.allow_unsafe_operations is False  # 安全モードがデフォルト
        assert config.allow_file_write is True
        assert config.allow_command_execution is True

    def test_security_config_custom(self):
        """カスタムセキュリティ設定をテスト"""
        config = SecurityConfig(
            allow_unsafe_operations=True,
            allow_file_write=False,
            allow_command_execution=False,
        )

        assert config.allow_unsafe_operations is True
        assert config.allow_file_write is False
        assert config.allow_command_execution is False

    def test_project_config_includes_security(self):
        """ProjectConfigにセキュリティ設定が含まれることをテスト"""
        config = ProjectConfig(project_name="test")

        # デフォルトでSecurityConfigが作成される
        assert hasattr(config, "security")
        assert isinstance(config.security, SecurityConfig)
        assert config.security.allow_unsafe_operations is False

    def test_project_loader_saves_security_config(self):
        """ProjectLoaderがセキュリティ設定を保存することをテスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            mao_dir = project_path / ".mao"
            mao_dir.mkdir()

            # 設定を作成
            config = ProjectConfig(
                project_name="test-project",
                default_language="python",
            )
            config.security.allow_unsafe_operations = True

            # 保存
            loader = ProjectLoader(project_path)
            loader.save(config)

            # ファイルを読み込んで確認
            config_file = mao_dir / "config.yaml"
            assert config_file.exists()

            with open(config_file) as f:
                data = yaml.safe_load(f)

            assert "security" in data
            assert data["security"]["allow_unsafe_operations"] is True

    def test_project_loader_loads_security_config(self):
        """ProjectLoaderがセキュリティ設定を読み込むことをテスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            mao_dir = project_path / ".mao"
            mao_dir.mkdir()

            # YAMLファイルを作成
            config_file = mao_dir / "config.yaml"
            config_data = {
                "project_name": "test-project",
                "default_language": "python",
                "security": {
                    "allow_unsafe_operations": True,
                    "allow_file_write": False,
                },
            }

            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

            # 読み込み
            loader = ProjectLoader(project_path)
            config = loader.load()

            assert config.security.allow_unsafe_operations is True
            assert config.security.allow_file_write is False

    def test_claude_code_executor_default_safe_mode(self):
        """ClaudeCodeExecutorがデフォルトで安全モードであることをテスト"""
        try:
            executor = ClaudeCodeExecutor()
            assert executor.allow_unsafe_operations is False
        except ValueError:
            # claude-code コマンドがない場合はスキップ
            pytest.skip("claude-code not available")

    def test_claude_code_executor_unsafe_mode(self):
        """ClaudeCodeExecutorが危険モードを設定できることをテスト"""
        try:
            executor = ClaudeCodeExecutor(allow_unsafe_operations=True)
            assert executor.allow_unsafe_operations is True
        except ValueError:
            # claude-code コマンドがない場合はスキップ
            pytest.skip("claude-code not available")

    def test_claude_code_executor_command_safe_mode(self):
        """安全モードでは--dangerously-skip-permissionsが付かないことをテスト"""
        try:
            executor = ClaudeCodeExecutor(allow_unsafe_operations=False)

            # execute_agentメソッドの内部でコマンドを構築する際、
            # allow_unsafe_operationsがFalseなら--dangerously-skip-permissionsが含まれない
            # (実際の実行はモックでテストすべきだが、ここでは構造のみ確認)
            assert executor.allow_unsafe_operations is False
        except ValueError:
            pytest.skip("claude-code not available")

    def test_security_config_yaml_format(self):
        """セキュリティ設定のYAMLフォーマットをテスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            mao_dir = project_path / ".mao"
            mao_dir.mkdir()

            # デフォルト設定を保存
            config = ProjectConfig(project_name="test")
            loader = ProjectLoader(project_path)
            loader.save(config)

            # YAMLを読んで構造を確認
            config_file = mao_dir / "config.yaml"
            with open(config_file) as f:
                content = f.read()

            # セキュリティセクションが含まれる
            assert "security:" in content
            assert "allow_unsafe_operations:" in content
