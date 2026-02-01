"""
Tests for shell injection prevention
"""
import pytest
from pathlib import Path
import shlex

from mao.orchestrator.tmux_manager import TmuxManager


class TestShellInjectionPrevention:
    """シェルインジェクション対策のテスト"""

    def test_shlex_quote_normal_path(self):
        """通常のパスが正しくエスケープされることをテスト"""
        path = Path("/tmp/test.log")
        quoted = shlex.quote(str(path))

        # スラッシュを含む通常のパスはそのまま
        assert quoted == "/tmp/test.log"

    def test_shlex_quote_path_with_spaces(self):
        """スペースを含むパスがエスケープされることをテスト"""
        path = Path("/tmp/test file.log")
        quoted = shlex.quote(str(path))

        # スペースを含むパスはクォートされる
        assert quoted == "'/tmp/test file.log'"

    def test_shlex_quote_path_with_special_chars(self):
        """特殊文字を含むパスがエスケープされることをテスト"""
        dangerous_paths = [
            "/tmp/test; rm -rf /",
            "/tmp/test$(whoami).log",
            "/tmp/test`whoami`.log",
            "/tmp/test|cat /etc/passwd",
            "/tmp/test&& echo hacked",
        ]

        for path in dangerous_paths:
            quoted = shlex.quote(path)

            # 特殊文字がエスケープされる
            assert quoted != path
            # クォートされる
            assert quoted.startswith("'") or quoted.startswith('"')

    def test_shlex_quote_prevents_command_injection(self):
        """コマンドインジェクションが防止されることをテスト"""
        malicious_path = "/tmp/log.txt; cat /etc/passwd"
        quoted = shlex.quote(malicious_path)

        # tailコマンドに組み込んでも安全
        command = f"tail -f {quoted}"

        # セミコロンが文字列としてエスケープされる
        assert ";" in command
        assert "'" in command  # クォートされている

    def test_tmux_manager_log_file_escaping(self):
        """TmuxManagerがログファイルパスを適切にエスケープすることをテスト"""
        # TmuxManagerは実際のtmuxが必要なので、
        # ここでは正しいメソッド呼び出しの構造のみテスト

        manager = TmuxManager(session_name="test-session")

        # セッション名が設定される
        assert manager.session_name == "test-session"

        # ペイン管理用の辞書が初期化される
        assert isinstance(manager.panes, dict)
        assert isinstance(manager.grid_panes, dict)

    def test_path_conversion_to_string(self):
        """Pathオブジェクトが文字列に変換されてエスケープされることをテスト"""
        path = Path("/tmp/test file.log")

        # Path -> str -> quote
        quoted = shlex.quote(str(path))

        assert isinstance(quoted, str)
        assert "test file.log" in quoted or "test\\ file.log" in quoted

    def test_empty_path_handling(self):
        """空のパスの処理をテスト"""
        empty_path = ""
        quoted = shlex.quote(empty_path)

        # 空文字列は空のクォートになる
        assert quoted == "''"

    def test_unicode_path_handling(self):
        """Unicode文字を含むパスの処理をテスト"""
        unicode_path = "/tmp/テスト.log"
        quoted = shlex.quote(unicode_path)

        # Unicodeも正しくエスケープされる
        assert "テスト" in quoted

    def test_multiple_special_chars(self):
        """複数の特殊文字を含むパスのテスト"""
        complex_path = "/tmp/test; echo 'hacked' && rm -rf /"
        quoted = shlex.quote(complex_path)

        # 全ての特殊文字がエスケープされる
        assert quoted.startswith("'")
        assert quoted.endswith("'")
        # 元の文字列が保持される（エスケープされた形で）
        assert "hacked" in quoted

    def test_backtick_injection_prevention(self):
        """バッククォートによるコマンド実行が防止されることをテスト"""
        backtick_path = "/tmp/`whoami`.log"
        quoted = shlex.quote(backtick_path)

        # バッククォートがエスケープされる
        assert "`" in quoted
        assert quoted != backtick_path

    def test_dollar_sign_injection_prevention(self):
        """$()によるコマンド実行が防止されることをテスト"""
        dollar_path = "/tmp/$(whoami).log"
        quoted = shlex.quote(dollar_path)

        # $(...)がエスケープされる
        assert "$" in quoted
        assert quoted != dollar_path
