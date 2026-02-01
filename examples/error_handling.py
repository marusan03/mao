"""
Error handling examples following MAO coding standards.

See docs/CODING_STANDARDS.md for full guidelines.
"""
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


# カスタム例外定義
class ConfigurationError(Exception):
    """設定関連のエラー"""

    pass


class DataLoadError(Exception):
    """データ読み込みエラー"""

    pass


# データモデル
class Config(BaseModel):
    """設定データ"""

    name: str
    value: int


# ✅ 良い例: 明示的なエラーハンドリング
def load_config_good(path: Path) -> Config:
    """
    設定ファイルを読み込む（良い例）

    Args:
        path: 設定ファイルパス

    Returns:
        読み込んだ設定

    Raises:
        ConfigurationError: 設定ファイルの読み込みまたは検証に失敗
    """
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError as e:
        logger.error(f"Config file not found: {path}")
        raise ConfigurationError(f"Missing config file: {path}") from e
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config: {path}")
        raise ConfigurationError(f"Invalid JSON format: {path}") from e

    try:
        return Config.model_validate(data)
    except ValidationError as e:
        logger.error(f"Config validation failed: {e}")
        raise ConfigurationError(f"Invalid config data in {path}") from e


# ❌ 悪い例: サイレントフォールバック
def load_config_bad(path: Path) -> Config:
    """設定ファイルを読み込む（悪い例 - 使わないこと）"""
    try:
        with open(path) as f:
            data = json.load(f)
        return Config.model_validate(data)
    except Exception:  # ❌ 汎用的すぎる
        return Config(name="default", value=0)  # ❌ サイレントフォールバック


# ✅ 良い例: やむを得ないフォールバック（ログ必須）
def get_cached_value_good(key: str, cache: dict[str, str]) -> str | None:
    """
    キャッシュから値を取得（フォールバック許容）

    Args:
        key: キャッシュキー
        cache: キャッシュストア

    Returns:
        キャッシュ値、なければNone
    """
    try:
        return cache[key]
    except KeyError as e:
        # ⚠️ フォールバックするが、ログに記録
        logger.debug(
            f"Cache miss for key: {key}",
            extra={"key": key, "available_keys": list(cache.keys())},
        )
        return None


# ✅ 良い例: リトライ付きフォールバック
def load_with_fallback_good(
    primary_path: Path,
    fallback_path: Path,
) -> dict[str, Any]:
    """
    プライマリファイルを読み込み、失敗時はフォールバック

    Args:
        primary_path: プライマリファイルパス
        fallback_path: フォールバックファイルパス

    Returns:
        読み込んだデータ

    Raises:
        DataLoadError: 両方のファイル読み込みに失敗
    """
    try:
        with open(primary_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # ⚠️ フォールバックを試すが、ログに記録
        logger.warning(
            f"Primary file failed, trying fallback: {primary_path} -> {fallback_path}",
            extra={
                "primary": str(primary_path),
                "fallback": str(fallback_path),
                "error": str(e),
            },
        )

        try:
            with open(fallback_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as fallback_error:
            logger.error(f"Fallback file also failed: {fallback_path}")
            raise DataLoadError(
                f"Both files failed: {primary_path}, {fallback_path}"
            ) from fallback_error


# ✅ 良い例: エラーチェーンを保持
def process_data_good(data: str) -> dict[str, Any]:
    """
    データを処理（エラーチェーン保持）

    Args:
        data: JSON文字列

    Returns:
        パース済みデータ

    Raises:
        DataLoadError: データのパースに失敗
    """
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        raise DataLoadError(f"Invalid JSON data: {data[:100]}...") from e


# ✅ 良い例: ログレベルの使い分け
def risky_operation_good(critical: bool = False) -> None:
    """
    リスクのある操作（ログレベル適切に使用）

    Args:
        critical: クリティカルな操作かどうか
    """

    class ExpectedError(Exception):
        pass

    class UnexpectedError(Exception):
        pass

    class CriticalError(Exception):
        pass

    try:
        if critical:
            raise CriticalError("Critical failure")
        # ... operation
    except ExpectedError as e:
        # 想定内のエラー: WARNING
        logger.warning(f"Expected error occurred: {e}")
        # リトライなど
    except UnexpectedError as e:
        # 想定外のエラー: ERROR（スタックトレース付き）
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise
    except CriticalError as e:
        # クリティカルなエラー: CRITICAL
        logger.critical(f"Critical system error: {e}", exc_info=True)
        # システム停止など
        raise


if __name__ == "__main__":
    # ロガー設定
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 良い例のデモ
    print("=== Good Examples ===\n")

    # 例1: 設定読み込み
    try:
        config = load_config_good(Path("nonexistent.json"))
    except ConfigurationError as e:
        print(f"✅ Caught ConfigurationError: {e}")

    # 例2: キャッシュ取得
    cache: dict[str, str] = {"key1": "value1"}
    result = get_cached_value_good("key2", cache)
    print(f"✅ Cache result (with logging): {result}")

    # 例3: フォールバック
    try:
        data = load_with_fallback_good(
            Path("nonexistent.json"),
            Path("also_nonexistent.json"),
        )
    except DataLoadError as e:
        print(f"✅ Caught DataLoadError: {e}")
