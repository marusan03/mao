"""
CTO Orchestrator - CTOの監視とエージェント管理
"""
import asyncio
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
import uuid

from mao.orchestrator.task_queue import TaskQueue, Task, TaskStatus
from mao.orchestrator.cto_decision import (
    CTODecisionEngine,
    Decision,
    DecisionAction,
    RiskLevel as DecisionRiskLevel,
)
from mao.orchestrator.state_manager import StateManager, AgentStatus
from mao.ui.widgets.approval_request import ApprovalRequest, RiskLevel


class CTOOrchestrator:
    """CTO orchestrator - エージェントの監視と管理"""

    def __init__(
        self,
        project_path: Path,
        num_agents: int = 8,
        poll_interval: float = 2.0,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Args:
            project_path: プロジェクトパス
            num_agents: エージェント数
            poll_interval: ポーリング間隔（秒）
            logger: ロガー
        """
        self.project_path = project_path
        self.num_agents = num_agents
        self.poll_interval = poll_interval
        self.logger = logger or logging.getLogger(__name__)

        # タスクキュー
        self.task_queue = TaskQueue(project_path, logger=logger)

        # 判断エンジン
        self.decision_engine = CTODecisionEngine(logger=logger)

        # 状態管理
        self.state_manager = StateManager(project_path, logger=logger)

        # 承認コールバック
        self.on_approval_request: Optional[Callable[[ApprovalRequest], None]] = None
        self.on_auto_approved: Optional[Callable[[str, str], None]] = None

        # 監視タスク
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False

        # 承認待ちリクエスト
        self.pending_approvals: Dict[str, ApprovalRequest] = {}

    def set_approval_callback(
        self,
        callback: Callable[[ApprovalRequest], None]
    ) -> None:
        """承認リクエストコールバックを設定

        Args:
            callback: 承認リクエスト時に呼ばれるコールバック
        """
        self.on_approval_request = callback

    def set_auto_approved_callback(
        self,
        callback: Callable[[str, str], None]
    ) -> None:
        """自動承認コールバックを設定

        Args:
            callback: 自動承認時に呼ばれるコールバック(agent_id, reason)
        """
        self.on_auto_approved = callback

    async def start_monitoring(self) -> None:
        """監視ループを開始"""
        if self._running:
            self.logger.warning("Monitoring already running")
            return

        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("CTO monitoring started")

    async def stop_monitoring(self) -> None:
        """監視ループを停止"""
        if not self._running:
            return

        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        self.logger.info("CTO monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """監視ループのメイン処理"""
        while self._running:
            try:
                # 完了済みエージェントの結果を確認
                completed_roles = self.task_queue.list_completed_results()

                for role in completed_roles:
                    await self._process_agent_result(role)

                # ポーリング間隔待機
                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def _process_agent_result(self, role: str) -> None:
        """エージェントの結果を処理

        Args:
            role: エージェントロール（agent-1, agent-2, etc.）
        """
        # 結果を取得
        task = self.task_queue.get_result(role)
        if not task:
            return

        self.logger.info(f"Processing result from {role}: {task.task_id}")

        # タスクが失敗している場合
        if task.status == TaskStatus.FAILED:
            self.logger.warning(f"Task {task.task_id} failed: {task.error}")
            # TODO: ユーザーに通知
            return

        # 成果物をレビュー
        decision = self.decision_engine.evaluate_task_result(
            task_description=task.prompt,
            result_summary=task.result,
            files_changed=[],  # TODO: 実際の変更ファイルを取得
            lines_changed=0,  # TODO: 実際の変更行数を取得
        )

        self.logger.info(
            f"Decision for {role}: {decision.action} (risk: {decision.risk_level})"
        )

        # 判断に基づいて処理
        if decision.action == DecisionAction.APPROVE:
            # 自動承認
            await self._auto_approve_task(role, task, decision)

        elif decision.action == DecisionAction.ESCALATE:
            # ユーザーに承認を求める
            await self._request_user_approval(role, task, decision)

        elif decision.action == DecisionAction.REJECT:
            # 却下
            await self._reject_task(role, task, decision)

    async def _auto_approve_task(
        self,
        role: str,
        task: Task,
        decision: Decision
    ) -> None:
        """タスクを自動承認

        Args:
            role: エージェントロール
            task: タスク
            decision: 判断結果
        """
        self.logger.info(f"Auto-approving task {task.task_id} from {role}")

        # 状態を更新
        await self.state_manager.update_state(
            agent_id=role,
            role=role,
            status=AgentStatus.COMPLETED,
            current_task=f"Completed: {task.prompt[:30]}...",
        )

        # コールバックを呼ぶ
        if self.on_auto_approved:
            self.on_auto_approved(role, decision.reason)

    async def _request_user_approval(
        self,
        role: str,
        task: Task,
        decision: Decision
    ) -> None:
        """ユーザーに承認を求める

        Args:
            role: エージェントロール
            task: タスク
            decision: 判断結果
        """
        request_id = f"req-{uuid.uuid4().hex[:8]}"

        self.logger.info(f"Requesting user approval for {task.task_id} ({request_id})")

        # リスクレベルを変換
        risk_level_map = {
            DecisionRiskLevel.LOW: RiskLevel.LOW,
            DecisionRiskLevel.MEDIUM: RiskLevel.MEDIUM,
            DecisionRiskLevel.HIGH: RiskLevel.HIGH,
            DecisionRiskLevel.CRITICAL: RiskLevel.CRITICAL,
        }

        # 承認リクエストを作成
        approval_request = ApprovalRequest(
            request_id=request_id,
            worker_id=role,
            task_description=task.prompt,
            operation=task.result[:100] + "..." if len(task.result) > 100 else task.result,
            risk_level=risk_level_map.get(decision.risk_level, RiskLevel.MEDIUM),
            reason=decision.reason,
            recommendation=decision.recommendation,
            details=task.result,
        )

        # 承認待ちリストに追加
        self.pending_approvals[request_id] = approval_request

        # 状態を更新
        await self.state_manager.update_state(
            agent_id=role,
            role=role,
            status=AgentStatus.WAITING,
            current_task=f"Awaiting approval: {task.prompt[:30]}...",
        )

        # コールバックを呼ぶ
        if self.on_approval_request:
            self.on_approval_request(approval_request)

    async def _reject_task(
        self,
        role: str,
        task: Task,
        decision: Decision
    ) -> None:
        """タスクを却下

        Args:
            role: エージェントロール
            task: タスク
            decision: 判断結果
        """
        self.logger.warning(f"Rejecting task {task.task_id} from {role}: {decision.reason}")

        # 状態を更新
        await self.state_manager.update_state(
            agent_id=role,
            role=role,
            status=AgentStatus.ERROR,
            current_task=f"Rejected: {task.prompt[:30]}...",
            error_message=decision.reason,
        )

    async def approve_request(self, request_id: str) -> None:
        """承認リクエストを承認

        Args:
            request_id: リクエストID
        """
        if request_id not in self.pending_approvals:
            self.logger.warning(f"Approval request {request_id} not found")
            return

        approval = self.pending_approvals.pop(request_id)
        self.logger.info(f"User approved request {request_id}")

        # エージェントの状態を更新
        await self.state_manager.update_state(
            agent_id=approval.agent_id,
            role=approval.agent_id,
            status=AgentStatus.COMPLETED,
            current_task=f"Approved: {approval.task_description[:30]}...",
        )

    async def reject_request(self, request_id: str) -> None:
        """承認リクエストを却下

        Args:
            request_id: リクエストID
        """
        if request_id not in self.pending_approvals:
            self.logger.warning(f"Approval request {request_id} not found")
            return

        approval = self.pending_approvals.pop(request_id)
        self.logger.info(f"User rejected request {request_id}")

        # エージェントの状態を更新
        await self.state_manager.update_state(
            agent_id=approval.agent_id,
            role=approval.agent_id,
            status=AgentStatus.ERROR,
            current_task=f"Rejected: {approval.task_description[:30]}...",
            error_message="User rejected the changes",
        )

    def assign_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """タスクをエージェントに割り当て

        Args:
            tasks: タスクリスト
                [
                    {"role": "agent-1", "prompt": "..."},
                    {"role": "agent-2", "prompt": "..."},
                ]
        """
        for task_data in tasks:
            task = Task(
                task_id=f"task-{uuid.uuid4().hex[:8]}",
                role=task_data["role"],
                prompt=task_data["prompt"],
                model=task_data.get("model", "sonnet"),
            )

            self.task_queue.assign_task(task)
            self.logger.info(f"Assigned task {task.task_id} to {task.role}")
