"""
Model utilities for cost calculation and name conversion
"""
from typing import Union, Dict, Any, Optional
from pathlib import Path
import yaml


def calculate_cost(
    model: str,
    usage: Union[Dict[str, int], Any],
    pricing_config: Optional[Dict[str, Any]] = None,
) -> float:
    """コストを計算（概算）

    Args:
        model: モデル名
        usage: トークン使用量（Dict または Usage オブジェクト）
        pricing_config: 価格設定（Noneの場合はデフォルト価格を使用）

    Returns:
        コスト（USD）
    """
    # 価格表を取得（設定がある場合は使用、なければデフォルト）
    if pricing_config:
        # PricingConfig から価格を取得
        pricing = {}
        if "models" in pricing_config:
            for model_name, price_data in pricing_config["models"].items():
                pricing[model_name] = {
                    "input": price_data.get("input", 3.0),
                    "output": price_data.get("output", 15.0),
                }
        default_price = pricing_config.get("default", {"input": 3.0, "output": 15.0})
        if isinstance(default_price, dict):
            default_price = {
                "input": default_price.get("input", 3.0),
                "output": default_price.get("output", 15.0),
            }
    else:
        # デフォルト価格表（$per 1M tokens）- 2026年1月時点
        pricing = {
            "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
            "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
            "claude-haiku-4-20250514": {"input": 0.25, "output": 1.25},
        }
        default_price = {"input": 3.0, "output": 15.0}

    # モデルに対応する価格を取得（デフォルト価格にフォールバック）
    price = pricing.get(model, default_price)

    # usageから入出力トークン数を取得（Dict or Object）
    if isinstance(usage, dict):
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
    else:
        # Usage オブジェクト
        input_tokens = getattr(usage, "input_tokens", 0)
        output_tokens = getattr(usage, "output_tokens", 0)

    input_cost = input_tokens / 1_000_000 * price["input"]
    output_cost = output_tokens / 1_000_000 * price["output"]

    return input_cost + output_cost


def load_pricing_config() -> Dict[str, Any]:
    """Load pricing configuration from global config file

    Returns:
        価格設定の辞書
    """
    config_dir = Path(__file__).parent.parent.parent / "config"
    pricing_file = config_dir / "pricing.yaml"

    if not pricing_file.exists():
        # ファイルがない場合は空の辞書を返す（デフォルト価格が使用される）
        return {}

    with open(pricing_file) as f:
        return yaml.safe_load(f)


def convert_model_name(model: str) -> str:
    """モデル名を短縮名に変換

    Args:
        model: フルモデル名

    Returns:
        短縮名（opus, sonnet, haiku）
    """
    model_lower = model.lower()
    if "opus" in model_lower:
        return "opus"
    elif "sonnet" in model_lower:
        return "sonnet"
    elif "haiku" in model_lower:
        return "haiku"
    else:
        # デフォルトはsonnet
        return "sonnet"
