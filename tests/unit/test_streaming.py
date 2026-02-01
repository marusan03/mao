"""
Tests for Streaming Response Support
"""
import pytest
from mao.ui.widgets.manager_chat import ManagerChatWidget, ChatMessage


class TestStreamingSupport:
    """ストリーミング応答のテスト"""

    def test_start_streaming_message(self):
        """ストリーミングメッセージの開始"""
        widget = ManagerChatWidget()

        widget.start_streaming_message()

        assert widget._streaming_buffer == ""
        assert widget._streaming_message is not None
        assert widget._streaming_message.sender == "manager"
        assert widget._streaming_message.message == ""

    def test_append_streaming_chunk(self):
        """ストリーミングチャンクの追加"""
        widget = ManagerChatWidget()

        # ストリーミング開始
        widget.start_streaming_message()

        # チャンクを追加
        widget.append_streaming_chunk("Hello")
        assert widget._streaming_buffer == "Hello"
        assert widget._streaming_message.message == "Hello"

        # 追加のチャンクを追加
        widget.append_streaming_chunk(" World")
        assert widget._streaming_buffer == "Hello World"
        assert widget._streaming_message.message == "Hello World"

    def test_append_streaming_chunk_auto_start(self):
        """ストリーミング開始前のチャンク追加で自動開始"""
        widget = ManagerChatWidget()

        # start を呼ばずにチャンクを追加
        widget.append_streaming_chunk("Auto started")

        assert widget._streaming_message is not None
        assert widget._streaming_buffer == "Auto started"
        assert widget._streaming_message.message == "Auto started"

    def test_complete_streaming_message(self):
        """ストリーミングメッセージの完了"""
        widget = ManagerChatWidget()

        # ストリーミング開始してチャンクを追加
        widget.start_streaming_message()
        widget.append_streaming_chunk("Complete message")

        # 完了
        widget.complete_streaming_message()

        # メッセージリストに追加されている
        assert len(widget.messages) == 1
        assert widget.messages[0].message == "Complete message"
        assert widget.messages[0].sender == "manager"

        # ストリーミング状態がクリア
        assert widget._streaming_message is None
        assert widget._streaming_buffer == ""

    def test_complete_streaming_without_content(self):
        """内容がない場合の完了（何も追加されない）"""
        widget = ManagerChatWidget()

        widget.start_streaming_message()
        widget.complete_streaming_message()

        # 空のメッセージは追加されない
        assert len(widget.messages) == 0
        assert widget._streaming_message is None
        assert widget._streaming_buffer == ""

    def test_multiple_streaming_sessions(self):
        """複数のストリーミングセッション"""
        widget = ManagerChatWidget()

        # 1つ目のストリーミング
        widget.start_streaming_message()
        widget.append_streaming_chunk("First message")
        widget.complete_streaming_message()

        # 2つ目のストリーミング
        widget.start_streaming_message()
        widget.append_streaming_chunk("Second message")
        widget.complete_streaming_message()

        # 両方のメッセージが追加されている
        assert len(widget.messages) == 2
        assert widget.messages[0].message == "First message"
        assert widget.messages[1].message == "Second message"

    def test_streaming_with_newlines(self):
        """改行を含むストリーミング"""
        widget = ManagerChatWidget()

        widget.start_streaming_message()
        widget.append_streaming_chunk("Line 1\n")
        widget.append_streaming_chunk("Line 2\n")
        widget.append_streaming_chunk("Line 3")
        widget.complete_streaming_message()

        assert len(widget.messages) == 1
        assert widget.messages[0].message == "Line 1\nLine 2\nLine 3"

    def test_streaming_mixed_with_regular_messages(self):
        """ストリーミングと通常メッセージの混在"""
        widget = ManagerChatWidget()

        # 通常メッセージ
        widget.add_user_message("User message")

        # ストリーミングメッセージ
        widget.start_streaming_message()
        widget.append_streaming_chunk("Streamed manager response")
        widget.complete_streaming_message()

        # 別の通常メッセージ
        widget.add_user_message("Another user message")

        assert len(widget.messages) == 3
        assert widget.messages[0].message == "User message"
        assert widget.messages[0].sender == "user"
        assert widget.messages[1].message == "Streamed manager response"
        assert widget.messages[1].sender == "manager"
        assert widget.messages[2].message == "Another user message"
        assert widget.messages[2].sender == "user"

    def test_streaming_cancel(self):
        """ストリーミングのキャンセル"""
        widget = ManagerChatWidget()

        # ストリーミング開始
        widget.start_streaming_message()
        widget.append_streaming_chunk("Partial message")

        # キャンセル（complete を呼ばずに状態をクリア）
        widget._streaming_message = None
        widget._streaming_buffer = ""

        # メッセージは追加されない
        assert len(widget.messages) == 0

        # 新しいストリーミングを開始できる
        widget.start_streaming_message()
        widget.append_streaming_chunk("New message")
        widget.complete_streaming_message()

        assert len(widget.messages) == 1
        assert widget.messages[0].message == "New message"

    def test_streaming_unicode_content(self):
        """Unicode文字を含むストリーミング"""
        widget = ManagerChatWidget()

        widget.start_streaming_message()
        widget.append_streaming_chunk("日本語のメッセージ\n")
        widget.append_streaming_chunk("絵文字: 🚀 ✅ 📝\n")
        widget.append_streaming_chunk("特殊文字: café, naïve")
        widget.complete_streaming_message()

        assert len(widget.messages) == 1
        expected = "日本語のメッセージ\n絵文字: 🚀 ✅ 📝\n特殊文字: café, naïve"
        assert widget.messages[0].message == expected

    def test_streaming_max_messages_limit(self):
        """最大メッセージ数の制限とストリーミング"""
        widget = ManagerChatWidget(max_messages=3)

        # 通常メッセージで埋める
        widget.add_user_message("Message 1")
        widget.add_user_message("Message 2")
        widget.add_user_message("Message 3")

        # ストリーミングで追加（最古のメッセージが削除される）
        widget.start_streaming_message()
        widget.append_streaming_chunk("Streamed message")
        widget.complete_streaming_message()

        assert len(widget.messages) == 3
        assert widget.messages[0].message == "Message 2"
        assert widget.messages[1].message == "Message 3"
        assert widget.messages[2].message == "Streamed message"

    def test_streaming_long_content(self):
        """長いコンテンツのストリーミング"""
        widget = ManagerChatWidget()

        widget.start_streaming_message()

        # 1000チャンクを追加
        for i in range(1000):
            widget.append_streaming_chunk(f"Chunk {i}\n")

        widget.complete_streaming_message()

        assert len(widget.messages) == 1
        content = widget.messages[0].message
        assert "Chunk 0" in content
        assert "Chunk 999" in content
        assert content.count("\n") == 1000

    def test_streaming_empty_chunks(self):
        """空チャンクの処理"""
        widget = ManagerChatWidget()

        widget.start_streaming_message()
        widget.append_streaming_chunk("")
        widget.append_streaming_chunk("Content")
        widget.append_streaming_chunk("")
        widget.complete_streaming_message()

        assert len(widget.messages) == 1
        assert widget.messages[0].message == "Content"

    def test_refresh_display_during_streaming(self):
        """ストリーミング中の表示更新"""
        widget = ManagerChatWidget()

        widget.start_streaming_message()
        widget.append_streaming_chunk("First chunk")

        # refresh_display は正常に動作するはず
        # （実際の表示は Textual が管理するため、エラーが出ないことを確認）
        try:
            widget.refresh_display()
            success = True
        except Exception:
            success = False

        assert success is True
