"""Approval Request Widget - 承認リクエスト表示"""
from textual.widgets import Static, Button
from textual.containers import Container, Horizontal, Vertical
from textual.app import ComposeResult
from rich.text import Text
from typing import Callable, Optional
from dataclasses import dataclass
from enum import Enum
import subprocess
import platform


class RiskLevel(str, Enum):
    """リスクレベル"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class ApprovalRequest:
    """承認リクエスト"""
    request_id: str
    worker_id: str
    task_description: str
    operation: str
    risk_level: RiskLevel
    reason: str
    recommendation: Optional[str] = None
    details: Optional[str] = None


class ApprovalRequestWidget(Container, can_focus=True):
    """承認リクエストウィジェット"""

    BINDINGS = [
        ("a", "approve", "Approve"),
        ("r", "reject", "Reject"),
        ("enter", "approve", "Approve"),
    ]

    def __init__(
        self,
        request: ApprovalRequest,
        on_approve: Optional[Callable[[str], None]] = None,
        on_reject: Optional[Callable[[str], None]] = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.request = request
        self.on_approve_callback = on_approve
        self.on_reject_callback = on_reject

    def compose(self) -> ComposeResult:
        """UIを構成"""
        # リスクレベルに応じた色
        risk_colors = {
            RiskLevel.LOW: "green",
            RiskLevel.MEDIUM: "yellow",
            RiskLevel.HIGH: "red",
            RiskLevel.CRITICAL: "bright_red",
        }

        risk_icons = {
            RiskLevel.LOW: "ℹ️",
            RiskLevel.MEDIUM: "⚠️",
            RiskLevel.HIGH: "🚨",
            RiskLevel.CRITICAL: "🛑",
        }

        with Vertical(classes="approval-request-container"):
            # ヘッダー
            with Horizontal(classes="approval-header"):
                icon = risk_icons.get(self.request.risk_level, "❓")
                yield Static(
                    f"{icon} 承認リクエスト",
                    classes="approval-title"
                )
                risk_color = risk_colors.get(self.request.risk_level, "white")
                yield Static(
                    f"[{risk_color}]{self.request.risk_level}[/]",
                    classes="risk-badge"
                )

            # ワーカー情報
            yield Static(
                f"ワーカー: {self.request.worker_id}",
                classes="worker-info"
            )

            # 操作内容
            yield Static(
                f"操作: {self.request.operation}",
                classes="operation-info"
            )

            # タスク説明
            yield Static(
                f"タスク: {self.request.task_description}",
                classes="task-info"
            )

            # 理由
            with Container(classes="reason-container"):
                yield Static("【理由】", classes="section-title")
                yield Static(self.request.reason, classes="reason-text")

            # 推奨事項
            if self.request.recommendation:
                with Container(classes="recommendation-container"):
                    yield Static("【推奨】", classes="section-title")
                    yield Static(
                        self.request.recommendation,
                        classes="recommendation-text"
                    )

            # 詳細
            if self.request.details:
                with Container(classes="details-container"):
                    yield Static("【詳細】", classes="section-title")
                    yield Static(self.request.details, classes="details-text")

            # ボタン
            with Horizontal(classes="approval-buttons"):
                yield Button(
                    "✅ 承認",
                    id=f"approve-{self.request.request_id}",
                    variant="success",
                    classes="approve-button"
                )
                yield Button(
                    "❌ 却下",
                    id=f"reject-{self.request.request_id}",
                    variant="error",
                    classes="reject-button"
                )
                yield Button(
                    "📋 詳細を確認",
                    id=f"details-{self.request.request_id}",
                    variant="primary",
                    classes="details-button"
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """ボタン押下時の処理"""
        button_id = event.button.id

        if button_id and button_id.startswith("approve-"):
            if self.on_approve_callback:
                self.on_approve_callback(self.request.request_id)
            self.remove()

        elif button_id and button_id.startswith("reject-"):
            if self.on_reject_callback:
                self.on_reject_callback(self.request.request_id)
            self.remove()

        elif button_id and button_id.startswith("details-"):
            # 詳細表示をトグル
            self._toggle_details()

    def _toggle_details(self) -> None:
        """詳細表示のトグル"""
        # 実装はダッシュボード側で行う
        pass

    def action_approve(self) -> None:
        """承認アクション"""
        if self.on_approve_callback:
            self.on_approve_callback(self.request.request_id)
        self.remove()

    def action_reject(self) -> None:
        """却下アクション"""
        if self.on_reject_callback:
            self.on_reject_callback(self.request.request_id)
        self.remove()


class ApprovalQueueWidget(Container, can_focus=True):
    """承認キューウィジェット（複数の承認リクエストを表示）"""

    BINDINGS = [
        ("up", "select_previous", "Previous Request"),
        ("down", "select_next", "Next Request"),
        ("a", "approve_selected", "Approve"),
        ("r", "reject_selected", "Reject"),
        ("enter", "approve_selected", "Approve"),
    ]

    def __init__(
        self,
        on_approve: Optional[Callable[[str], None]] = None,
        on_reject: Optional[Callable[[str], None]] = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.on_approve_callback = on_approve
        self.on_reject_callback = on_reject
        self.requests: dict[str, ApprovalRequest] = {}
        self.selected_index = 0

    def add_request(self, request: ApprovalRequest) -> None:
        """承認リクエストを追加

        Args:
            request: 承認リクエスト
        """
        self.requests[request.request_id] = request
        self._refresh_display()

        # 通知を送信
        self._send_notification(request)

    def remove_request(self, request_id: str) -> None:
        """承認リクエストを削除

        Args:
            request_id: リクエストID
        """
        if request_id in self.requests:
            del self.requests[request_id]
            self._refresh_display()

    def _refresh_display(self) -> None:
        """表示を更新"""
        # 既存のウィジェットをクリア
        self.remove_children()

        if not self.requests:
            # リクエストがない場合
            self.mount(
                Static(
                    "承認待ちのリクエストはありません",
                    classes="no-requests"
                )
            )
        else:
            # リクエストを表示（新しい順）
            sorted_requests = sorted(
                self.requests.values(),
                key=lambda r: r.request_id,
                reverse=True
            )

            for request in sorted_requests:
                widget = ApprovalRequestWidget(
                    request=request,
                    on_approve=self.on_approve_callback,
                    on_reject=self.on_reject_callback,
                )
                self.mount(widget)

    def get_pending_count(self) -> int:
        """保留中のリクエスト数を取得

        Returns:
            リクエスト数
        """
        return len(self.requests)

    def _send_notification(self, request: ApprovalRequest) -> None:
        """承認リクエストの通知を送信

        Args:
            request: 承認リクエスト
        """
        # macOSの場合のみ通知を送る
        if platform.system() != "Darwin":
            return

        try:
            risk_icons = {
                RiskLevel.LOW: "ℹ️",
                RiskLevel.MEDIUM: "⚠️",
                RiskLevel.HIGH: "🚨",
                RiskLevel.CRITICAL: "🛑",
            }
            icon = risk_icons.get(request.risk_level, "❓")

            title = f"{icon} MAO - 承認リクエスト"
            message = f"{request.worker_id}: {request.operation}\nリスク: {request.risk_level}"

            # AppleScriptで通知を送信
            script = f'''
                display notification "{message}" with title "{title}" sound name "Glass"
            '''
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=5
            )
        except Exception:
            # 通知失敗は無視
            pass

    def _get_selected_request(self) -> Optional[ApprovalRequest]:
        """選択中のリクエストを取得

        Returns:
            選択中のリクエスト、なければNone
        """
        if not self.requests:
            return None

        request_list = sorted(
            self.requests.values(),
            key=lambda r: r.request_id,
            reverse=True
        )

        if 0 <= self.selected_index < len(request_list):
            return request_list[self.selected_index]
        return None

    def action_select_next(self) -> None:
        """次のリクエストを選択"""
        if self.requests:
            self.selected_index = (self.selected_index + 1) % len(self.requests)
            self._highlight_selected()

    def action_select_previous(self) -> None:
        """前のリクエストを選択"""
        if self.requests:
            self.selected_index = (self.selected_index - 1) % len(self.requests)
            self._highlight_selected()

    def action_approve_selected(self) -> None:
        """選択中のリクエストを承認"""
        request = self._get_selected_request()
        if request and self.on_approve_callback:
            self.on_approve_callback(request.request_id)

    def action_reject_selected(self) -> None:
        """選択中のリクエストを却下"""
        request = self._get_selected_request()
        if request and self.on_reject_callback:
            self.on_reject_callback(request.request_id)

    def _highlight_selected(self) -> None:
        """選択中のリクエストをハイライト表示"""
        # 実装: 選択中のウィジェットにフォーカスを当てる
        # Textualでは、フォーカスを使ってハイライトを実現
        widgets = list(self.query(ApprovalRequestWidget))
        if 0 <= self.selected_index < len(widgets):
            widgets[self.selected_index].focus()
