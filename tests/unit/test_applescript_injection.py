"""
Tests for AppleScript injection prevention
"""
import pytest

from mao.orchestrator.agent_executor import escape_applescript, send_mac_notification


class TestAppleScriptInjectionPrevention:
    """AppleScriptインジェクション対策のテスト"""

    def test_escape_applescript_normal_text(self):
        """通常のテキストがそのまま返されることをテスト"""
        text = "Hello, World!"
        escaped = escape_applescript(text)

        assert escaped == "Hello, World!"

    def test_escape_applescript_double_quote(self):
        """ダブルクォートがエスケープされることをテスト"""
        text = 'Say "Hello"'
        escaped = escape_applescript(text)

        # ダブルクォートが \"にエスケープされる
        assert escaped == 'Say \\"Hello\\"'

    def test_escape_applescript_backslash(self):
        """バックスラッシュがエスケープされることをテスト"""
        text = "Path\\to\\file"
        escaped = escape_applescript(text)

        # バックスラッシュが\\にエスケープされる
        assert escaped == "Path\\\\to\\\\file"

    def test_escape_applescript_both_special_chars(self):
        """バックスラッシュとダブルクォート両方がエスケープされることをテスト"""
        text = 'Path\\to\\"file"'
        escaped = escape_applescript(text)

        # 両方エスケープされる
        assert escaped == 'Path\\\\to\\\\\\"file\\"'

    def test_escape_applescript_injection_attempt(self):
        """インジェクション試行がエスケープされることをテスト"""
        # インジェクション試行例
        malicious_texts = [
            '" on error\ndisplay dialog "Hacked!"',
            '"; do shell script "rm -rf /"',
            '" & (do shell script "whoami") & "',
        ]

        for text in malicious_texts:
            escaped = escape_applescript(text)

            # ダブルクォートがエスケープされる
            assert '\\"' in escaped
            # 元のテキストと異なる
            assert escaped != text

    def test_escape_applescript_empty_string(self):
        """空文字列の処理をテスト"""
        text = ""
        escaped = escape_applescript(text)

        assert escaped == ""

    def test_escape_applescript_only_quotes(self):
        """クォートのみの文字列をテスト"""
        text = '"""'
        escaped = escape_applescript(text)

        assert escaped == '\\"\\"\\"'

    def test_escape_applescript_only_backslashes(self):
        """バックスラッシュのみの文字列をテスト"""
        text = "\\\\\\"
        escaped = escape_applescript(text)

        assert escaped == "\\\\\\\\\\\\"

    def test_escape_applescript_unicode(self):
        """Unicode文字を含むテキストをテスト"""
        text = 'こんにちは "世界"'
        escaped = escape_applescript(text)

        # Unicodeはそのまま、クォートだけエスケープ
        assert escaped == 'こんにちは \\"世界\\"'

    def test_escape_applescript_newlines(self):
        """改行を含むテキストをテスト"""
        text = 'Line 1\nLine 2\n"Quote"'
        escaped = escape_applescript(text)

        # 改行はそのまま、クォートだけエスケープ
        assert escaped == 'Line 1\nLine 2\n\\"Quote\\"'

    def test_send_mac_notification_with_safe_text(self):
        """安全なテキストで通知関数が動作することをテスト"""
        # 実際の通知送信はスキップ（macOSでない場合もある）
        # ここでは関数が例外を投げないことだけ確認
        try:
            send_mac_notification("Test", "Hello, World!", sound=False)
            # 成功または失敗（osascriptがない場合）どちらでも良い
        except Exception:
            # 例外は内部でキャッチされるはず
            pytest.fail("send_mac_notification should not raise exceptions")

    def test_send_mac_notification_with_dangerous_text(self):
        """危険なテキストで通知関数が安全に動作することをテスト"""
        dangerous_title = '" on error\ndisplay dialog "Hacked!"'
        dangerous_message = '"; do shell script "rm -rf /"'

        try:
            send_mac_notification(dangerous_title, dangerous_message, sound=False)
            # 成功または失敗どちらでも良い（エスケープされているはず）
        except Exception:
            # 例外は内部でキャッチされるはず
            pytest.fail("send_mac_notification should not raise exceptions")

    def test_escape_preserves_order(self):
        """エスケープ順序が正しいことをテスト（バックスラッシュを先にエスケープ）"""
        # この順序が重要：バックスラッシュを先にエスケープしないと
        # ダブルクォートのエスケープが二重にエスケープされる

        text = '\\"'  # すでに\でエスケープされたクォート
        escaped = escape_applescript(text)

        # 正しくエスケープされる: \\ と \"
        assert escaped == '\\\\\\"'

    def test_escape_applescript_special_applescript_chars(self):
        """AppleScript特有の文字をテスト"""
        # AppleScriptで特別な意味を持つ可能性のある文字
        text = 'test & "value" & otherValue'
        escaped = escape_applescript(text)

        # ダブルクォートのみエスケープ（&はそのまま）
        assert escaped == 'test & \\"value\\" & otherValue'

    def test_multiple_consecutive_quotes(self):
        """連続するクォートのテスト"""
        text = '""""""'
        escaped = escape_applescript(text)

        # 各クォートがエスケープされる
        assert escaped == '\\"\\"\\"\\"\\"\\"'
        assert escaped.count('\\"') == 6

    def test_mixed_content(self):
        """混合コンテンツのテスト"""
        text = 'Agent "worker-1" completed task:\\nResult: 100% success!'
        escaped = escape_applescript(text)

        # クォートとバックスラッシュがエスケープされる
        assert '\\"worker-1\\"' in escaped
        assert '\\\\n' in escaped
