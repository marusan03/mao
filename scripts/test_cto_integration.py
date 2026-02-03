#!/usr/bin/env python3
"""CTO統合テスト（ダッシュボード経由）"""

import asyncio
import sys
from pathlib import Path

# プロジェクトルートをPATHに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_cto_message_flow():
    """CTOメッセージフローのテスト"""
    from mao.ui.dashboard_interactive import Dashboard
    from mao.orchestrator.session_manager import SessionManager

    print("=" * 60)
    print("Test: CTO Message Flow (Dashboard Integration)")
    print("=" * 60)

    # セッションマネージャー初期化
    project_path = Path.cwd()
    session_manager = SessionManager(project_path)

    print("\n[Test] Creating dashboard...")
    # ダッシュボード初期化（App外でのテスト）
    dashboard = Dashboard(
        project_path=project_path,
        session_manager=session_manager,
        sequential_mode=False,
        initial_prompt=None
    )

    # CTOチャットパネルが存在するか確認
    print(f"✅ Dashboard created")
    print(f"   cto_chat_panel exists: {dashboard.cto_chat_panel is not None}")

    if not dashboard.cto_chat_panel:
        print("❌ cto_chat_panel is None!")
        return False

    # 直接メッセージを追加
    print("\n[Test] Adding test message to CTO chat...")
    dashboard.cto_chat_panel.chat_widget.add_user_message("Test user message")
    dashboard.cto_chat_panel.chat_widget.add_cto_message("Test CTO response")

    print(f"✅ Messages added")
    print(f"   Total messages: {len(dashboard.cto_chat_panel.chat_widget.messages)}")

    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_cto_message_flow())
        if result:
            print("\n" + "=" * 60)
            print("🎉 Integration test passed!")
            print("=" * 60)
        else:
            print("\n❌ Integration test failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
