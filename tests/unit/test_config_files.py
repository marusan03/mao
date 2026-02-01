"""
Tests for configuration files (pricing.yaml, defaults.yaml)
"""
import pytest
import yaml
from pathlib import Path
from mao.orchestrator.project_loader import (
    ProjectLoader,
    PricingConfig,
    DefaultsConfig,
    TmuxConfig,
    TmuxGridConfig,
)
from mao.orchestrator.utils.model_utils import calculate_cost, load_pricing_config


class TestPricingConfig:
    """pricing.yaml のテスト"""

    def test_pricing_file_exists(self):
        """pricing.yaml ファイルが存在する"""
        config_dir = Path(__file__).parent.parent.parent / "mao" / "config"
        pricing_file = config_dir / "pricing.yaml"
        assert pricing_file.exists(), "pricing.yaml should exist"

    def test_pricing_file_valid_yaml(self):
        """pricing.yaml が有効なYAMLである"""
        config_dir = Path(__file__).parent.parent.parent / "mao" / "config"
        pricing_file = config_dir / "pricing.yaml"

        with open(pricing_file) as f:
            data = yaml.safe_load(f)

        assert data is not None
        assert "models" in data
        assert "default" in data

    def test_pricing_has_all_models(self):
        """pricing.yaml に全モデルの価格が含まれている"""
        config_dir = Path(__file__).parent.parent.parent / "mao" / "config"
        pricing_file = config_dir / "pricing.yaml"

        with open(pricing_file) as f:
            data = yaml.safe_load(f)

        expected_models = [
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514",
            "claude-haiku-4-20250514",
        ]

        for model in expected_models:
            assert model in data["models"], f"{model} should be in pricing.yaml"
            assert "input" in data["models"][model]
            assert "output" in data["models"][model]

    def test_pricing_values_are_numeric(self):
        """価格が数値である"""
        config_dir = Path(__file__).parent.parent.parent / "mao" / "config"
        pricing_file = config_dir / "pricing.yaml"

        with open(pricing_file) as f:
            data = yaml.safe_load(f)

        for model_name, pricing in data["models"].items():
            assert isinstance(pricing["input"], (int, float)), f"{model_name} input price should be numeric"
            assert isinstance(pricing["output"], (int, float)), f"{model_name} output price should be numeric"
            assert pricing["input"] > 0, f"{model_name} input price should be positive"
            assert pricing["output"] > 0, f"{model_name} output price should be positive"

    def test_load_pricing_config_function(self):
        """load_pricing_config() が正しく動作する"""
        pricing = load_pricing_config()

        assert "models" in pricing
        assert "default" in pricing
        assert "claude-sonnet-4-20250514" in pricing["models"]


class TestDefaultsConfig:
    """defaults.yaml のテスト"""

    def test_defaults_file_exists(self):
        """defaults.yaml ファイルが存在する"""
        config_dir = Path(__file__).parent.parent.parent / "mao" / "config"
        defaults_file = config_dir / "defaults.yaml"
        assert defaults_file.exists(), "defaults.yaml should exist"

    def test_defaults_file_valid_yaml(self):
        """defaults.yaml が有効なYAMLである"""
        config_dir = Path(__file__).parent.parent.parent / "mao" / "config"
        defaults_file = config_dir / "defaults.yaml"

        with open(defaults_file) as f:
            data = yaml.safe_load(f)

        assert data is not None
        assert "tmux" in data
        assert "models" in data
        assert "execution" in data

    def test_defaults_tmux_config(self):
        """tmux設定が含まれている"""
        config_dir = Path(__file__).parent.parent.parent / "mao" / "config"
        defaults_file = config_dir / "defaults.yaml"

        with open(defaults_file) as f:
            data = yaml.safe_load(f)

        assert "grid" in data["tmux"]
        assert "width" in data["tmux"]["grid"]
        assert "height" in data["tmux"]["grid"]
        assert "num_workers" in data["tmux"]["grid"]

        # 値が適切な範囲である
        assert data["tmux"]["grid"]["width"] > 0
        assert data["tmux"]["grid"]["height"] > 0
        assert data["tmux"]["grid"]["num_workers"] > 0


class TestProjectLoaderWithConfigs:
    """ProjectLoader による設定読み込みテスト"""

    def test_pricing_config_loads(self, tmp_path):
        """PricingConfigが正しく読み込まれる"""
        # プロジェクト設定を作成
        mao_dir = tmp_path / ".mao"
        mao_dir.mkdir()

        config_file = mao_dir / "config.yaml"
        config_file.write_text(
            """
project_name: test
default_language: python
"""
        )

        loader = ProjectLoader(tmp_path)
        config = loader.load()

        assert config.pricing is not None
        assert config.pricing.default.input > 0
        assert config.pricing.default.output > 0

    def test_defaults_config_loads(self, tmp_path):
        """DefaultsConfigが正しく読み込まれる"""
        # プロジェクト設定を作成
        mao_dir = tmp_path / ".mao"
        mao_dir.mkdir()

        config_file = mao_dir / "config.yaml"
        config_file.write_text(
            """
project_name: test
default_language: python
"""
        )

        loader = ProjectLoader(tmp_path)
        config = loader.load()

        assert config.defaults is not None
        assert config.defaults.tmux.grid.width > 0
        assert config.defaults.tmux.grid.height > 0
        assert config.defaults.tmux.grid.num_workers > 0


class TestCalculateCostWithPricing:
    """calculate_cost() の pricing_config パラメータテスト"""

    def test_calculate_cost_with_custom_pricing(self):
        """カスタム価格設定でコストを計算"""
        usage = {"input_tokens": 1000, "output_tokens": 2000}

        custom_pricing = {
            "models": {
                "custom-model": {"input": 10.0, "output": 50.0}
            },
            "default": {"input": 5.0, "output": 25.0}
        }

        cost = calculate_cost("custom-model", usage, pricing_config=custom_pricing)

        # 入力: 1000 / 1M * 10.0 = 0.01
        # 出力: 2000 / 1M * 50.0 = 0.1
        # 合計: 0.11
        assert cost == pytest.approx(0.11, rel=1e-6)

    def test_calculate_cost_with_custom_default(self):
        """未知のモデルでカスタムデフォルト価格を使用"""
        usage = {"input_tokens": 1000, "output_tokens": 2000}

        custom_pricing = {
            "models": {},
            "default": {"input": 100.0, "output": 200.0}
        }

        cost = calculate_cost("unknown-model", usage, pricing_config=custom_pricing)

        # デフォルト価格が使用される
        expected_cost = 1000 / 1_000_000 * 100.0 + 2000 / 1_000_000 * 200.0
        assert cost == pytest.approx(expected_cost, rel=1e-6)

    def test_calculate_cost_without_pricing_uses_defaults(self):
        """pricing_config なしでデフォルト価格を使用"""
        usage = {"input_tokens": 1000, "output_tokens": 2000}

        cost = calculate_cost("claude-sonnet-4-20250514", usage)

        # デフォルト価格表を使用
        expected_cost = 1000 / 1_000_000 * 3.0 + 2000 / 1_000_000 * 15.0
        assert cost == pytest.approx(expected_cost, rel=1e-6)

    def test_calculate_cost_with_loaded_pricing(self):
        """実際のpricing.yamlを読み込んで計算"""
        usage = {"input_tokens": 100000, "output_tokens": 50000}

        pricing = load_pricing_config()
        cost = calculate_cost("claude-sonnet-4-20250514", usage, pricing_config=pricing)

        # pricing.yamlの価格を使用
        assert cost > 0
        assert cost == pytest.approx(0.3 + 0.75, rel=1e-6)


class TestTmuxConfigIntegration:
    """TmuxConfig の統合テスト"""

    def test_tmux_grid_config_defaults(self):
        """TmuxGridConfig のデフォルト値"""
        grid_config = TmuxGridConfig()

        assert grid_config.width == 240
        assert grid_config.height == 60
        assert grid_config.num_workers == 8
        assert grid_config.default_layout == "tiled"

    def test_tmux_config_with_custom_values(self):
        """カスタム値でTmuxConfigを作成"""
        grid_config = TmuxGridConfig(width=300, height=80, num_workers=12)

        assert grid_config.width == 300
        assert grid_config.height == 80
        assert grid_config.num_workers == 12

    def test_defaults_config_structure(self):
        """DefaultsConfig の構造"""
        defaults = DefaultsConfig()

        assert defaults.tmux is not None
        assert defaults.tmux.grid is not None
        assert defaults.execution is not None
        assert defaults.execution.max_tokens == 4096
        assert defaults.execution.temperature == 1.0
