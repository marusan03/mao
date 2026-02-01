"""
CTO Decision Engine - CTOの判断ロジック
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List
import re
import logging


class RiskLevel(str, Enum):
    """リスクレベル"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DecisionAction(str, Enum):
    """判断アクション"""
    APPROVE = "APPROVE"  # 自律的に承認
    ESCALATE = "ESCALATE"  # ユーザーに承認を求める
    REJECT = "REJECT"  # 却下


@dataclass
class Decision:
    """判断結果"""
    action: DecisionAction
    risk_level: RiskLevel
    reason: str
    recommendation: Optional[str] = None
    auto_approved: bool = False


class CTODecisionEngine:
    """CTOの判断エンジン"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def evaluate_task_result(
        self,
        task_description: str,
        result_summary: str,
        files_changed: Optional[List[str]] = None,
        lines_changed: int = 0,
    ) -> Decision:
        """タスク結果を評価して判断を下す

        Args:
            task_description: タスクの説明
            result_summary: 結果のサマリー
            files_changed: 変更されたファイルのリスト
            lines_changed: 変更行数

        Returns:
            判断結果
        """
        files_changed = files_changed or []

        # キーワードベースのリスク評価
        risk_keywords = self._extract_risk_keywords(
            task_description + " " + result_summary
        )

        # ファイルパターンベースのリスク評価
        file_risks = self._evaluate_file_changes(files_changed)

        # 総合的なリスク評価
        overall_risk = self._calculate_overall_risk(
            risk_keywords, file_risks, lines_changed
        )

        # 判断を下す
        return self._make_decision(
            overall_risk,
            risk_keywords,
            file_risks,
            task_description,
            result_summary,
        )

    def _extract_risk_keywords(self, text: str) -> List[str]:
        """リスクキーワードを抽出

        Args:
            text: 検索対象のテキスト

        Returns:
            検出されたリスクキーワードのリスト
        """
        risk_patterns = {
            "deletion": [r"\bdelete\b", r"\bremove\b", r"\brm\b", r"削除"],
            "external_api": [r"\bAPI\b", r"\bhttp[s]?://", r"\brequest\b", r"外部"],
            "database": [r"\bSQL\b", r"\bmigration\b", r"データベース", r"\bDB\b"],
            "config": [r"\.env", r"config", r"設定"],
            "dependencies": [
                r"npm install",
                r"pip install",
                r"yarn add",
                r"依存",
            ],
            "security": [r"password", r"secret", r"token", r"auth", r"認証"],
        }

        detected = []
        text_lower = text.lower()

        for category, patterns in risk_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    detected.append(category)
                    break

        return detected

    def _evaluate_file_changes(self, files: List[str]) -> dict[str, RiskLevel]:
        """ファイル変更のリスク評価

        Args:
            files: 変更されたファイルのリスト

        Returns:
            ファイルごとのリスクレベル
        """
        file_risk_patterns = {
            RiskLevel.CRITICAL: [
                r"\.env$",
                r"\.env\.production$",
                r"secrets?\.ya?ml$",
                r"credentials\.json$",
            ],
            RiskLevel.HIGH: [
                r"config/.*\.ya?ml$",
                r".*\.sql$",
                r"migration.*\.py$",
                r"Dockerfile$",
                r"docker-compose\.ya?ml$",
            ],
            RiskLevel.MEDIUM: [
                r"package\.json$",
                r"requirements\.txt$",
                r"Gemfile$",
                r"go\.mod$",
            ],
            RiskLevel.LOW: [
                r".*_test\.py$",
                r".*\.test\.ts$",
                r".*\.spec\.ts$",
                r".*\.md$",
                r"README.*",
            ],
        }

        risk_map = {}

        for file_path in files:
            file_risk = RiskLevel.LOW  # デフォルト

            for risk_level, patterns in file_risk_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, file_path, re.IGNORECASE):
                        file_risk = risk_level
                        break
                if file_risk != RiskLevel.LOW:
                    break

            risk_map[file_path] = file_risk

        return risk_map

    def _calculate_overall_risk(
        self,
        risk_keywords: List[str],
        file_risks: dict[str, RiskLevel],
        lines_changed: int,
    ) -> RiskLevel:
        """総合的なリスクレベルを計算

        Args:
            risk_keywords: 検出されたリスクキーワード
            file_risks: ファイルごとのリスクレベル
            lines_changed: 変更行数

        Returns:
            総合リスクレベル
        """
        # ファイルリスクの最大値
        max_file_risk = RiskLevel.LOW
        if file_risks:
            risk_levels = [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]
            for level in risk_levels:
                if level in file_risks.values():
                    max_file_risk = level
                    break

        # キーワードベースのリスク
        keyword_risk = RiskLevel.LOW
        high_risk_keywords = {"deletion", "database", "security"}
        medium_risk_keywords = {"external_api", "config", "dependencies"}

        if any(kw in risk_keywords for kw in high_risk_keywords):
            keyword_risk = RiskLevel.HIGH
        elif any(kw in risk_keywords for kw in medium_risk_keywords):
            keyword_risk = RiskLevel.MEDIUM

        # 変更量ベースのリスク
        size_risk = RiskLevel.LOW
        if lines_changed > 500:
            size_risk = RiskLevel.HIGH
        elif lines_changed > 100:
            size_risk = RiskLevel.MEDIUM

        # 最大値を採用
        risk_levels = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
        }

        max_risk_value = max(
            risk_levels[max_file_risk],
            risk_levels[keyword_risk],
            risk_levels[size_risk],
        )

        for level, value in risk_levels.items():
            if value == max_risk_value:
                return level

        return RiskLevel.LOW

    def _make_decision(
        self,
        risk_level: RiskLevel,
        risk_keywords: List[str],
        file_risks: dict[str, RiskLevel],
        task_description: str,
        result_summary: str,
    ) -> Decision:
        """リスクレベルに基づいて判断を下す

        Args:
            risk_level: 総合リスクレベル
            risk_keywords: 検出されたリスクキーワード
            file_risks: ファイルごとのリスクレベル
            task_description: タスク説明
            result_summary: 結果サマリー

        Returns:
            判断結果
        """
        # CRITICAL: 必ず却下またはエスカレーション
        if risk_level == RiskLevel.CRITICAL:
            return Decision(
                action=DecisionAction.ESCALATE,
                risk_level=RiskLevel.CRITICAL,
                reason="機密情報や重要な設定ファイルへの変更を検出しました。慎重な確認が必要です。",
                recommendation="変更内容を詳細に確認し、バックアップを取ることを推奨します。",
            )

        # HIGH: エスカレーション
        if risk_level == RiskLevel.HIGH:
            reasons = []
            if "deletion" in risk_keywords:
                reasons.append("削除操作が含まれています")
            if "database" in risk_keywords:
                reasons.append("データベース変更が含まれています")
            if any(r == RiskLevel.HIGH for r in file_risks.values()):
                high_risk_files = [f for f, r in file_risks.items() if r == RiskLevel.HIGH]
                reasons.append(f"重要ファイルの変更: {', '.join(high_risk_files[:3])}")

            return Decision(
                action=DecisionAction.ESCALATE,
                risk_level=RiskLevel.HIGH,
                reason="高リスクの操作を検出しました: " + "、".join(reasons),
                recommendation="影響範囲を確認してから承認することを推奨します。",
            )

        # MEDIUM: エスカレーション（安全マージンを取る）
        if risk_level == RiskLevel.MEDIUM:
            reasons = []
            if "external_api" in risk_keywords:
                reasons.append("外部API呼び出し")
            if "dependencies" in risk_keywords:
                reasons.append("依存パッケージの追加")
            if "config" in risk_keywords:
                reasons.append("設定変更")

            return Decision(
                action=DecisionAction.ESCALATE,
                risk_level=RiskLevel.MEDIUM,
                reason="中程度のリスク操作を検出しました: " + "、".join(reasons),
                recommendation="内容を確認してから承認してください。",
            )

        # LOW: 自律的に承認
        return Decision(
            action=DecisionAction.APPROVE,
            risk_level=RiskLevel.LOW,
            reason="リスクの低い変更と判断しました。",
            recommendation=None,
            auto_approved=True,
        )

    def is_safe_to_auto_approve(self, decision: Decision) -> bool:
        """自動承認しても安全か判定

        Args:
            decision: 判断結果

        Returns:
            自動承認可能かどうか
        """
        return (
            decision.action == DecisionAction.APPROVE
            and decision.risk_level == RiskLevel.LOW
        )
