"""
Tests for model utilities
"""
import pytest
from mao.orchestrator.utils.model_utils import calculate_cost, convert_model_name


class TestCalculateCost:
    """calculate_cost関数のテスト"""

    def test_cost_with_dict_usage(self):
        """Dict型のusageでコストを計算"""
        usage = {"input_tokens": 1000, "output_tokens": 2000}
        cost = calculate_cost("claude-sonnet-4-20250514", usage)

        # 入力: 1000 / 1M * 3.0 = 0.003
        # 出力: 2000 / 1M * 15.0 = 0.03
        # 合計: 0.033
        assert cost == pytest.approx(0.033, rel=1e-6)

    def test_cost_with_object_usage(self):
        """オブジェクト型のusageでコストを計算"""
        class Usage:
            def __init__(self, input_tokens, output_tokens):
                self.input_tokens = input_tokens
                self.output_tokens = output_tokens

        usage = Usage(input_tokens=500000, output_tokens=1000000)
        cost = calculate_cost("claude-opus-4-20250514", usage)

        # 入力: 500000 / 1M * 15.0 = 7.5
        # 出力: 1000000 / 1M * 75.0 = 75.0
        # 合計: 82.5
        assert cost == pytest.approx(82.5, rel=1e-6)

    def test_cost_with_haiku_model(self):
        """Haikuモデルのコスト計算"""
        usage = {"input_tokens": 100000, "output_tokens": 50000}
        cost = calculate_cost("claude-haiku-4-20250514", usage)

        # 入力: 100000 / 1M * 0.25 = 0.025
        # 出力: 50000 / 1M * 1.25 = 0.0625
        # 合計: 0.0875
        assert cost == pytest.approx(0.0875, rel=1e-6)

    def test_cost_with_unknown_model(self):
        """未知のモデルはデフォルト価格（Sonnet）を使用"""
        usage = {"input_tokens": 1000, "output_tokens": 2000}
        cost = calculate_cost("unknown-model", usage)

        # デフォルト: Sonnetの価格
        expected_cost = 1000 / 1_000_000 * 3.0 + 2000 / 1_000_000 * 15.0
        assert cost == pytest.approx(expected_cost, rel=1e-6)

    def test_cost_with_missing_tokens(self):
        """トークン数が欠けている場合は0として扱う"""
        usage = {"input_tokens": 1000}
        cost = calculate_cost("claude-sonnet-4-20250514", usage)

        # 出力トークンが0
        expected_cost = 1000 / 1_000_000 * 3.0
        assert cost == pytest.approx(expected_cost, rel=1e-6)

    def test_cost_with_empty_dict(self):
        """空のDictの場合はコストは0"""
        usage = {}
        cost = calculate_cost("claude-sonnet-4-20250514", usage)
        assert cost == 0.0

    def test_cost_with_zero_tokens(self):
        """トークン数が0の場合"""
        usage = {"input_tokens": 0, "output_tokens": 0}
        cost = calculate_cost("claude-sonnet-4-20250514", usage)
        assert cost == 0.0


class TestConvertModelName:
    """convert_model_name関数のテスト"""

    def test_convert_opus(self):
        """Opusモデル名を変換"""
        assert convert_model_name("claude-opus-4-20250514") == "opus"
        assert convert_model_name("OPUS") == "opus"
        assert convert_model_name("some-opus-model") == "opus"

    def test_convert_sonnet(self):
        """Sonnetモデル名を変換"""
        assert convert_model_name("claude-sonnet-4-20250514") == "sonnet"
        assert convert_model_name("SONNET") == "sonnet"
        assert convert_model_name("some-sonnet-model") == "sonnet"

    def test_convert_haiku(self):
        """Haikuモデル名を変換"""
        assert convert_model_name("claude-haiku-4-20250514") == "haiku"
        assert convert_model_name("HAIKU") == "haiku"
        assert convert_model_name("some-haiku-model") == "haiku"

    def test_convert_unknown_model(self):
        """未知のモデルはデフォルト（sonnet）を返す"""
        assert convert_model_name("unknown-model") == "sonnet"
        assert convert_model_name("") == "sonnet"
        assert convert_model_name("random") == "sonnet"

    def test_convert_case_insensitive(self):
        """大文字小文字を区別しない"""
        assert convert_model_name("CLAUDE-OPUS-4") == "opus"
        assert convert_model_name("Claude-Sonnet-4") == "sonnet"
        assert convert_model_name("claude-HAIKU-4") == "haiku"


class TestIntegration:
    """統合テスト"""

    def test_both_functions_with_typical_usage(self):
        """典型的な使用ケース"""
        model = "claude-sonnet-4-20250514"
        usage = {"input_tokens": 10000, "output_tokens": 5000}

        # モデル名変換
        short_name = convert_model_name(model)
        assert short_name == "sonnet"

        # コスト計算
        cost = calculate_cost(model, usage)
        assert cost > 0
        assert cost == pytest.approx(0.105, rel=1e-6)
