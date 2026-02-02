"""
Approval panel widgets
"""
from textual.widgets import Static, Button, Label
from textual.containers import Container, Vertical, Horizontal
from textual.app import ComposeResult
from typing import Optional, Callable, Dict, Any


class SkillApprovalPanel(Static):
    """Skill承認パネル"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pending_proposals = []
        self.on_approve: Optional[Callable] = None
        self.on_reject: Optional[Callable] = None

    def add_proposal(self, proposal: Dict[str, Any]):
        """承認待ち提案を追加

        Args:
            proposal: Skill提案情報
        """
        self.pending_proposals.append(proposal)
        self.refresh_display()

    def remove_proposal(self, proposal_id: str):
        """提案を削除"""
        self.pending_proposals = [
            p for p in self.pending_proposals if p.get("id") != proposal_id
        ]
        self.refresh_display()

    def refresh_display(self):
        """表示を更新"""
        lines = ["[bold]Skill承認待ち[/bold]\n"]

        if not self.pending_proposals:
            lines.append("[dim]承認待ちのSkillはありません[/dim]")
        else:
            lines.append(f"[yellow]{len(self.pending_proposals)}件の承認待ち[/yellow]\n")

            for i, proposal in enumerate(self.pending_proposals[:3], 1):  # 最大3件表示
                skill = proposal.get("skill", {})
                review = proposal.get("review", {})

                # リスクレベルの色
                risk_level = review.get("risk_level", "UNKNOWN")
                risk_color = {
                    "SAFE": "green",
                    "WARNING": "yellow",
                    "CRITICAL": "red",
                }.get(risk_level, "white")

                lines.append(f"[cyan]{i}. {skill.get('display_name', 'Unknown')}[/cyan]")
                lines.append(f"   品質: {review.get('quality_score', 0):.1f}/10")
                lines.append(f"   セキュリティ: [{risk_color}]{risk_level}[/{risk_color}]")

                # 警告がある場合
                issues = review.get("security", {}).get("issues", [])
                if issues:
                    lines.append(f"   [yellow]⚠ {len(issues)}件の問題[/yellow]")

                lines.append("")

            if len(self.pending_proposals) > 3:
                remaining = len(self.pending_proposals) - 3
                lines.append(f"[dim]他 {remaining}件...[/dim]")
                lines.append("")

            lines.append("[dim]詳細表示: mao skills proposals[/dim]")

        self.update("\n".join(lines))


class AuditApprovalPanel(Static):
    """監査承認パネル"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pending_audits = []

    def add_audit(self, audit: Dict[str, Any]):
        """承認待ち監査を追加"""
        self.pending_audits.append(audit)
        self.refresh_display()

    def remove_audit(self, audit_id: str):
        """監査を削除"""
        self.pending_audits = [
            a for a in self.pending_audits if a.get("id") != audit_id
        ]
        self.refresh_display()

    def refresh_display(self):
        """表示を更新"""
        lines = ["[bold]監査承認待ち[/bold]\n"]

        if not self.pending_audits:
            lines.append("[dim]承認待ちの監査はありません[/dim]")
        else:
            lines.append(f"[yellow]{len(self.pending_audits)}件の承認待ち[/yellow]\n")

            for i, audit in enumerate(self.pending_audits[:2], 1):  # 最大2件表示
                # リスクレベル
                risk_level = audit.get("overall_risk", "UNKNOWN")
                risk_color = {
                    "LOW": "green",
                    "MEDIUM": "yellow",
                    "HIGH": "red",
                    "CRITICAL": "bold red",
                }.get(risk_level, "white")

                lines.append(f"[cyan]{i}. {audit.get('title', 'Unknown')}[/cyan]")
                lines.append(f"   リスク: [{risk_color}]{risk_level}[/{risk_color}]")

                # セキュリティ問題
                security_issues = audit.get("security", {}).get("issues", [])
                if security_issues:
                    critical = sum(1 for i in security_issues if i.get("severity") == "critical")
                    if critical > 0:
                        lines.append(f"   [red]🔴 重大: {critical}件[/red]")

                lines.append("")

            if len(self.pending_audits) > 2:
                remaining = len(self.pending_audits) - 2
                lines.append(f"[dim]他 {remaining}件...[/dim]")

        self.update("\n".join(lines))


class UnifiedApprovalPanel(Static):
    """統合承認パネル"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.skill_proposals = []
        self.audit_requests = []
        self.plan_approvals = []
        self.worker_approvals = []  # ワーカータスク承認

    def add_skill_proposal(self, proposal: Dict[str, Any]):
        """Skill提案を追加"""
        self.skill_proposals.append(proposal)
        self.refresh_display()

    def add_audit_request(self, audit: Dict[str, Any]):
        """監査リクエストを追加"""
        self.audit_requests.append(audit)
        self.refresh_display()

    def add_plan_approval(self, plan: Dict[str, Any]):
        """プラン承認を追加"""
        self.plan_approvals.append(plan)
        self.refresh_display()

    def add_worker_approval(self, worker_task: Dict[str, Any]):
        """ワーカータスク承認を追加"""
        self.worker_approvals.append(worker_task)
        self.refresh_display()

    def remove_worker_approval(self, item_id: str):
        """ワーカータスク承認を削除"""
        self.worker_approvals = [
            w for w in self.worker_approvals if w.get("id") != item_id
        ]
        self.refresh_display()

    def get_total_pending(self) -> int:
        """承認待ち総数"""
        return (len(self.skill_proposals) + len(self.audit_requests) +
                len(self.plan_approvals) + len(self.worker_approvals))

    def refresh_display(self):
        """表示を更新"""
        lines = ["[bold]承認パネル[/bold]\n"]

        total = self.get_total_pending()

        if total == 0:
            lines.append("[dim]承認待ちの項目はありません[/dim]")
        else:
            lines.append(f"[yellow]合計 {total}件の承認待ち[/yellow]\n")

            # Skill提案
            if self.skill_proposals:
                lines.append(f"[cyan]💡 Skill提案: {len(self.skill_proposals)}件[/cyan]")
                for proposal in self.skill_proposals[:2]:
                    skill = proposal.get("skill", {})
                    review = proposal.get("review", {})
                    risk = review.get("risk_level", "UNKNOWN")
                    risk_icon = {"SAFE": "✓", "WARNING": "⚠", "CRITICAL": "🔴"}.get(risk, "•")
                    lines.append(f"  {risk_icon} {skill.get('display_name', 'Unknown')}")

                if len(self.skill_proposals) > 2:
                    lines.append(f"  [dim]他 {len(self.skill_proposals) - 2}件...[/dim]")
                lines.append("")

            # 監査リクエスト
            if self.audit_requests:
                lines.append(f"[red]🛡️ 監査承認: {len(self.audit_requests)}件[/red]")
                for audit in self.audit_requests[:2]:
                    risk = audit.get("overall_risk", "UNKNOWN")
                    lines.append(f"  🔴 {audit.get('title', 'Unknown')} ({risk})")

                if len(self.audit_requests) > 2:
                    lines.append(f"  [dim]他 {len(self.audit_requests) - 2}件...[/dim]")
                lines.append("")

            # プラン承認
            if self.plan_approvals:
                lines.append(f"[blue]📋 プラン承認: {len(self.plan_approvals)}件[/blue]")
                for plan in self.plan_approvals[:2]:
                    lines.append(f"  📋 {plan.get('title', 'Unknown')}")

                if len(self.plan_approvals) > 2:
                    lines.append(f"  [dim]他 {len(self.plan_approvals) - 2}件...[/dim]")
                lines.append("")

            # ワーカータスク承認
            if self.worker_approvals:
                lines.append(f"[green]👷 ワーカー完了: {len(self.worker_approvals)}件[/green]")
                for worker_task in self.worker_approvals[:3]:
                    worker_id = worker_task.get('worker_id', 'Unknown')
                    role = worker_task.get('role', 'Unknown')
                    task_desc = worker_task.get('task_description', 'Unknown task')[:40]
                    changed_files = worker_task.get('changed_files', [])
                    file_count = len(changed_files) if changed_files else 0
                    lines.append(f"  ✓ {worker_id} ({role}): {task_desc}... ({file_count}ファイル変更)")

                if len(self.worker_approvals) > 3:
                    lines.append(f"  [dim]他 {len(self.worker_approvals) - 3}件...[/dim]")
                lines.append("")

            lines.append("[dim]/approve <id> で承認 / /reject <id> で却下 / /diff <id> で差分表示[/dim]")

        self.update("\n".join(lines))
