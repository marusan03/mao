"""CTO Chat Widget - CTOとの対話ウィジェット"""
from textual.widgets import Static, Input
from textual.containers import Container, Vertical, VerticalScroll
from textual._context import NoActiveAppError
from rich.text import Text
from collections import deque
from typing import Deque, Callable, Optional, List, Dict
import datetime


class ChatMessage:
    """チャットメッセージ"""

    def __init__(self, sender: str, message: str, timestamp: Optional[datetime.datetime] = None):
        self.sender = sender  # "user" or "cto"
        self.message = message
        self.timestamp = timestamp or datetime.datetime.now()

    def format(self) -> Text:
        """メッセージをフォーマット"""
        text = Text()
        time_str = self.timestamp.strftime("%H:%M:%S")

        if self.sender == "user":
            # ユーザーメッセージ
            text.append(f"[{time_str}] ", style="dim")
            text.append("You", style="bold cyan")
            text.append(f": {self.message}", style="white")
        elif self.sender == "cto":
            # CTOメッセージ
            text.append(f"[{time_str}] ", style="dim")
            text.append("CTO", style="bold green")
            text.append(f": {self.message}", style="white")
        else:
            # システムメッセージ
            text.append(f"[{time_str}] ", style="dim")
            text.append("System", style="bold yellow")
            text.append(f": {self.message}", style="italic dim")

        return text


class CTOChatWidget(Static, can_focus=True):
    """CTOとのチャットウィジェット"""

    BINDINGS = [
        ("up", "scroll_up", "Scroll Up"),
        ("down", "scroll_down", "Scroll Down"),
        ("pageup", "page_up", "Page Up"),
        ("pagedown", "page_down", "Page Down"),
    ]

    def __init__(self, *args, max_messages: int = 50, **kwargs):
        super().__init__(*args, **kwargs)
        self.messages: Deque[ChatMessage] = deque(maxlen=max_messages)
        self.on_send_callback: Optional[Callable[[str], None]] = None
        self._streaming_message: Optional[ChatMessage] = None
        self._streaming_buffer: str = ""
        self._thinking_text: str = ""  # 途中経過テキスト

    def add_user_message(self, message: str):
        """ユーザーメッセージを追加"""
        self.messages.append(ChatMessage("user", message))
        self.refresh_display()

    def add_cto_message(self, message: str):
        """CTOメッセージを追加"""
        import logging
        logger = logging.getLogger("mao.ui.cto_chat")

        logger.debug(f"[CTOChat] add_cto_message called: {message[:50]}...")
        self.messages.append(ChatMessage("cto", message))
        self.refresh_display()
        logger.debug(f"[CTOChat] add_cto_message completed, total messages: {len(self.messages)}")

    def add_system_message(self, message: str):
        """システムメッセージを追加"""
        msg = ChatMessage("system", message)
        self.messages.append(msg)
        self.refresh_display()

    def start_streaming_message(self):
        """ストリーミングメッセージを開始"""
        self._streaming_buffer = ""
        self._streaming_message = ChatMessage("cto", "")

    def append_streaming_chunk(self, chunk: str):
        """ストリーミングメッセージにチャンクを追加

        Args:
            chunk: 追加するテキストチャンク
        """
        import logging
        logger = logging.getLogger("mao.ui.cto_chat")

        if self._streaming_message is None:
            logger.debug("[CTOChat] Starting new streaming message")
            self.start_streaming_message()

        self._streaming_buffer += chunk
        if self._streaming_message:
            self._streaming_message.message = self._streaming_buffer
            logger.debug(f"[CTOChat] append_streaming_chunk: buffer length = {len(self._streaming_buffer)}")
            self.refresh_display()

    def complete_streaming_message(self):
        """ストリーミングメッセージを完了"""
        import logging
        logger = logging.getLogger("mao.ui.cto_chat")

        if self._streaming_message and self._streaming_buffer:
            logger.debug(f"[CTOChat] Completing streaming message: {len(self._streaming_buffer)} chars")
            # ストリーミングメッセージを正式にメッセージリストに追加
            self.messages.append(self._streaming_message)
            self.refresh_display()
            logger.debug(f"[CTOChat] Streaming complete, total messages: {len(self.messages)}")
        else:
            logger.warning("[CTOChat] complete_streaming_message called but no streaming message exists")

        # ストリーミング状態をクリア
        self._streaming_message = None
        self._streaming_buffer = ""
        self._thinking_text = ""

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """会話履歴を取得（Claude API形式）

        Returns:
            会話履歴のリスト [{"role": "user"|"assistant", "content": "..."}]
        """
        history = []
        for msg in self.messages:
            if msg.sender == "user":
                history.append({"role": "user", "content": msg.message})
            elif msg.sender == "cto":
                history.append({"role": "assistant", "content": msg.message})
            # システムメッセージは履歴に含めない
        return history

    def set_thinking(self, text: str):
        """途中経過（thinking）を設定"""
        self._thinking_text = text
        self.refresh_display()

    def clear_thinking(self):
        """途中経過をクリア"""
        self._thinking_text = ""
        self.refresh_display()

    def set_send_callback(self, callback: Callable[[str], None]):
        """メッセージ送信時のコールバックを設定"""
        self.on_send_callback = callback

    def refresh_display(self):
        """表示を更新"""
        import logging
        logger = logging.getLogger("mao.ui.cto_chat")

        content = Text()
        content.append("[CTO Chat]\n", style="bold cyan")

        if not self.messages and not self._streaming_message and not self._thinking_text:
            content.append("CTOと対話できます。下のフィールドに入力してください。\n", style="dim")
        else:
            # 通常のメッセージを表示
            for msg in self.messages:
                content.append(msg.format())
                content.append("\n")

            # 途中経過（thinking）を表示
            if self._thinking_text:
                content.append("\n")
                content.append("💭 考え中... ", style="bold yellow")
                content.append(f"{self._thinking_text}\n", style="italic dim")

            # ストリーミング中のメッセージを表示
            if self._streaming_message:
                content.append(self._streaming_message.format())
                content.append("\n")

        # Appコンテキスト内でのみ更新
        try:
            # self.app にアクセスしてAppコンテキストを確認
            _ = self.app
            logger.debug(f"[CTOChat] refresh_display: Updating widget with {len(self.messages)} messages")
            self.update(content)
            self.scroll_end(animate=False)
            logger.debug("[CTOChat] refresh_display: Update successful")
        except NoActiveAppError:
            # Appコンテキストがない場合はスキップ（テスト環境など）
            logger.debug("[CTOChat] refresh_display: Skipped (App not available)")
        except Exception as e:
            logger.error(f"[CTOChat] refresh_display FAILED: {e}", exc_info=True)
            # エラーを再スロー（デバッグ時）
            if logger.level <= logging.DEBUG:
                raise


class CTOChatInput(Input):
    """CTOチャット用の入力フィールド"""

    def __init__(self, *args, **kwargs):
        super().__init__(
            placeholder="CTOに送信するメッセージを入力... (Enter で送信)",
            *args,
            **kwargs
        )
        self.on_submit_callback: Optional[Callable[[str], None]] = None

    def set_submit_callback(self, callback: Callable[[str], None]):
        """送信時のコールバックを設定"""
        self.on_submit_callback = callback

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enterキーで送信"""
        message = event.value.strip()
        if message and self.on_submit_callback:
            self.on_submit_callback(message)
            self.value = ""  # 入力をクリア


class CTOChatPanel(Container):
    """CTOチャットパネル（チャット表示+入力フィールド）"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_widget = CTOChatWidget()
        self.input_widget = CTOChatInput()

    def compose(self):
        """ウィジェットを構成"""
        with VerticalScroll(id="cto_chat_scroll"):
            yield self.chat_widget
        yield self.input_widget

    def set_send_callback(self, callback: Callable[[str], None]):
        """メッセージ送信時のコールバックを設定"""
        def on_submit(message: str):
            # ユーザーメッセージを表示
            self.chat_widget.add_user_message(message)
            # コールバックを呼び出し
            if callback:
                callback(message)

        self.input_widget.set_submit_callback(on_submit)

    def add_cto_message(self, message: str):
        """CTOメッセージを追加"""
        self.chat_widget.add_cto_message(message)

    def add_system_message(self, message: str):
        """システムメッセージを追加"""
        self.chat_widget.add_system_message(message)
