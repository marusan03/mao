"""
Agent-specific logging
"""
from pathlib import Path
import logging
import sys
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

        # フォーマット（tmuxで見やすいように）
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S"
        )

        # ファイルハンドラー
        file_handler = logging.FileHandler(self.log_file, mode="w")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # StreamHandler（標準出力へもログを出力）- tmuxのtail -fでリアルタイム表示可能
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        logger.propagate = False
        return logger

    def _flush_handlers(self) -> None:
        """すべてのハンドラーを強制的にflush"""
        for handler in self.logger.handlers:
            handler.flush()

    def info(self, message: str) -> None:
        """情報ログ"""
        self.logger.info(message)
        self._flush_handlers()

    def thinking(self, message: str) -> None:
        """思考プロセスログ"""
        self.logger.info(f"💭 {message}")
        self._flush_handlers()

    def action(self, tool: str, description: str) -> None:
        """アクション実行ログ"""
        self.logger.info(f"🔧 [{tool}] {description}")
        self._flush_handlers()

    def result(self, message: str) -> None:
        """結果ログ"""
        self.logger.info(f"✓ {message}")
        self._flush_handlers()

    def error(self, message: str) -> None:
        """エラーログ"""
        self.logger.error(f"✗ {message}")
        self._flush_handlers()

    def warning(self, message: str) -> None:
        """警告ログ"""
        self.logger.warning(f"⚠ {message}")
        self._flush_handlers()

    def api_request(self, model: str, tokens: int) -> None:
        """APIリクエストログ"""
        self.logger.debug(f"→ API Request | Model: {model} | Est. tokens: {tokens}")
        self._flush_handlers()

    def api_response(self, tokens: int, cost: float) -> None:
        """APIレスポンスログ"""
        self.logger.debug(f"← API Response | Tokens: {tokens} | Cost: ${cost:.4f}")
        self._flush_handlers()
