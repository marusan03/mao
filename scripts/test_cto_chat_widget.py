#!/usr/bin/env python3
"""CTO Chatウィジェットの直接テスト"""

import sys
import logging
from pathlib import Path

# プロジェクトルートをPATHに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mao.ui.widgets.cto_chat import CTOChatWidget, ChatMessage

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def test_message_addition():
    """メッセージ追加のテスト"""
    print("=" * 60)
    print("Test 1: メッセージ追加")
    print("=" * 60)

    widget = CTOChatWidget()

    # テスト1: 通常のメッセージ追加
    print("\n[Test] Adding user message...")
    widget.add_user_message("Hello, CTO!")
    print(f"✅ Messages count: {len(widget.messages)}")
    assert len(widget.messages) == 1
    assert widget.messages[0].sender == "user"

    # テスト2: CTOメッセージ追加
    print("\n[Test] Adding CTO message...")
    widget.add_cto_message("Hello! How can I help you?")
    print(f"✅ Messages count: {len(widget.messages)}")
    assert len(widget.messages) == 2
    assert widget.messages[1].sender == "cto"

    # テスト3: ストリーミングメッセージ
    print("\n[Test] Adding streaming message...")
    widget.append_streaming_chunk("This is ")
    widget.append_streaming_chunk("a streaming ")
    widget.append_streaming_chunk("message.")
    widget.complete_streaming_message()
    print(f"✅ Messages count: {len(widget.messages)}")
    assert len(widget.messages) == 3
    assert widget.messages[2].message == "This is a streaming message."

    print("\n✅ All tests passed!")
    return True

def test_refresh_display():
    """refresh_display()のテスト"""
    print("\n" + "=" * 60)
    print("Test 2: refresh_display()")
    print("=" * 60)

    widget = CTOChatWidget()
    widget.add_user_message("Test message 1")
    widget.add_cto_message("Test response 1")

    print("\n[Test] Calling refresh_display()...")
    try:
        widget.refresh_display()
        print("✅ refresh_display() completed without exception")
    except Exception as e:
        print(f"❌ refresh_display() raised exception: {e}")
        raise

    return True

if __name__ == "__main__":
    try:
        test_message_addition()
        test_refresh_display()
        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
