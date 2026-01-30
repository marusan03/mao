"""
Agent-specific logging
"""
from pathlib import Path
import logging
from typing import Optional


class AgentLogger:
    """エージェントごとの専用ロガー"""

    def __init__(self, agent_id: str, agent_name: str, log_dir: Path):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # ログファイル
        self.log_file = log_dir / f"{agent_id}.log"

        # ロガー設定
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """ロガーをセットアップ"""
        logger = logging.getLogger(f"mao.agent.{self.agent_id}")
        logger.setLevel(logging.DEBUG)

        # 既存のハンドラーをクリア
        logger.handlers.clear()

        # ファイルハンドラー
        handler = logging.FileHandler(self.log_file, mode="w")
        handler.setLevel(logging.DEBUG)

        # フォーマット（tmuxで見やすいように）
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.propagate = False
        return logger

    def info(self, message: str) -> None:
        """情報ログ"""
        self.logger.info(message)

    def thinking(self, message: str) -> None:
        """思考プロセスログ"""
        self.logger.info(f"💭 {message}")

    def action(self, tool: str, description: str) -> None:
        """アクション実行ログ"""
        self.logger.info(f"🔧 [{tool}] {description}")

    def result(self, message: str) -> None:
        """結果ログ"""
        self.logger.info(f"✓ {message}")

    def error(self, message: str) -> None:
        """エラーログ"""
        self.logger.error(f"✗ {message}")

    def warning(self, message: str) -> None:
        """警告ログ"""
        self.logger.warning(f"⚠ {message}")

    def api_request(self, model: str, tokens: int) -> None:
        """APIリクエストログ"""
        self.logger.debug(f"→ API Request | Model: {model} | Est. tokens: {tokens}")

    def api_response(self, tokens: int, cost: float) -> None:
        """APIレスポンスログ"""
        self.logger.debug(f"← API Response | Tokens: {tokens} | Cost: ${cost:.4f}")
