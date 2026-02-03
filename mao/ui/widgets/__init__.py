"""UI Widgets for MAO Dashboard"""

from .header import HeaderWidget
from .agent_list import AgentListWidget
from .log_viewer_simple import SimpleLogViewer
from .cto_chat import CTOChatWidget, CTOChatInput, CTOChatPanel
from .progress_widget import TaskProgressWidget, AgentActivityWidget, MetricsWidget
from .approval_request import (
    ApprovalRequest,
    ApprovalRequestWidget,
    ApprovalQueueWidget,
    RiskLevel,
)

__all__ = [
    "HeaderWidget",
    "AgentListWidget",
    "SimpleLogViewer",
    "CTOChatWidget",
    "CTOChatInput",
    "CTOChatPanel",
    "TaskProgressWidget",
    "AgentActivityWidget",
    "MetricsWidget",
    "ApprovalRequest",
    "ApprovalRequestWidget",
    "ApprovalQueueWidget",
    "RiskLevel",
]
