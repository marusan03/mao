"""
CLI Completion helpers for MAO
"""
from pathlib import Path
from typing import List
import click


def complete_feedback_ids(ctx, param, incomplete):
    """フィードバックIDの補完

    Args:
        ctx: Click context
        param: Parameter
        incomplete: 入力途中の文字列

    Returns:
        補完候補のリスト
    """
    try:
        from mao.orchestrator.feedback_manager import FeedbackManager

        # プロジェクトパスを取得
        project_dir = ctx.params.get("project_dir", ".")
        project_path = Path(project_dir).resolve()

        # フィードバック一覧を取得
        manager = FeedbackManager(project_path=project_path)
        feedbacks = manager.list_feedbacks()

        # 短縮IDと完全IDの両方を候補に
        candidates = []
        for fb in feedbacks:
            short_id = fb.id[-12:]
            full_id = fb.id

            # タイトルを含めた説明を追加
            title_preview = fb.title[:40] + "..." if len(fb.title) > 40 else fb.title

            # 入力途中の文字列にマッチするものを返す
            if incomplete in short_id or incomplete in full_id:
                # Click 8.0+ では (value, help) のタプルを返せる
                candidates.append((short_id, f"{title_preview} [{fb.status}]"))

        return candidates

    except Exception:
        # エラー時は空リストを返す
        return []


def complete_roles(ctx, param, incomplete):
    """ロール名の補完

    Args:
        ctx: Click context
        param: Parameter
        incomplete: 入力途中の文字列

    Returns:
        補完候補のリスト
    """
    try:
        from mao.config import ConfigLoader

        loader = ConfigLoader()
        roles = loader.list_available_roles()

        # ロール名を返す
        return [
            (role.stem, f"Role: {role.stem}")
            for role in roles
            if incomplete in role.stem
        ]

    except Exception:
        # デフォルトのロール
        default_roles = ["general", "planner", "coder", "reviewer", "tester", "cto"]
        return [
            (role, f"Role: {role}")
            for role in default_roles
            if incomplete in role
        ]


def complete_models(ctx, param, incomplete):
    """モデル名の補完

    Args:
        ctx: Click context
        param: Parameter
        incomplete: 入力途中の文字列

    Returns:
        補完候補のリスト
    """
    # 利用可能なモデル
    models = [
        ("opus", "Claude Opus 4.5 - Most powerful"),
        ("sonnet", "Claude Sonnet 4.5 - Balanced (default)"),
        ("haiku", "Claude Haiku 3.5 - Fast and efficient"),
        ("claude-opus-4-5-20251101", "Full model ID: Opus"),
        ("claude-sonnet-4-20250514", "Full model ID: Sonnet"),
        ("claude-3-5-haiku-20241022", "Full model ID: Haiku"),
    ]

    return [
        (model, desc)
        for model, desc in models
        if incomplete in model
    ]


def complete_session_ids(ctx, param, incomplete):
    """セッションIDの補完

    Args:
        ctx: Click context
        param: Parameter
        incomplete: 入力途中の文字列

    Returns:
        補完候補のリスト
    """
    try:
        from mao.orchestrator.session_manager import SessionManager

        project_dir = ctx.params.get("project_dir", ".")
        project_path = Path(project_dir).resolve()

        # セッション一覧を取得
        session_manager = SessionManager(project_path=project_path)
        sessions = session_manager.list_sessions()

        return [
            (session.session_id, f"Session: {session.created_at[:19]}")
            for session in sessions
            if incomplete in session.session_id
        ]

    except Exception:
        return []


def complete_agent_ids(ctx, param, incomplete):
    """エージェントIDの補完

    Args:
        ctx: Click context
        param: Parameter
        incomplete: 入力途中の文字列

    Returns:
        補完候補のリスト
    """
    # 一般的なエージェントID
    common_agents = [
        "manager",
        "cto",
        "worker-1",
        "worker-2",
        "worker-3",
        "worker-4",
        "worker-5",
        "worker-6",
        "worker-7",
        "worker-8",
    ]

    return [
        (agent, f"Agent: {agent}")
        for agent in common_agents
        if incomplete in agent
    ]
