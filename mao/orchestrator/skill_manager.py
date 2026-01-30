"""
Skill management system
"""
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
import json
from datetime import datetime


class SkillDefinition:
    """Skill定義"""

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.name = data.get("name")
        self.display_name = data.get("display_name")
        self.description = data.get("description")
        self.version = data.get("version", "1.0")
        self.parameters = data.get("parameters", [])
        self.commands = data.get("commands", [])
        self.script = data.get("script")
        self.examples = data.get("examples", [])

    def to_dict(self) -> Dict[str, Any]:
        """辞書に変換"""
        return self.data

    def to_yaml(self) -> str:
        """YAMLに変換"""
        return yaml.dump(self.data, default_flow_style=False, allow_unicode=True)


class SkillReview:
    """Skillレビュー結果"""

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.status = data.get("status")  # APPROVED, NEEDS_REVISION, REJECTED
        self.security = data.get("security", {})
        self.quality_score = data.get("quality_score", 0)
        self.recommendations = data.get("recommendations", [])
        self.approval_needed = data.get("approval_needed", True)
        self.auditor_review_needed = data.get("auditor_review_needed", False)

    @property
    def is_approved(self) -> bool:
        """承認されているか"""
        return self.status == "APPROVED"

    @property
    def is_rejected(self) -> bool:
        """却下されているか"""
        return self.status == "REJECTED"

    @property
    def needs_revision(self) -> bool:
        """修正が必要か"""
        return self.status == "NEEDS_REVISION"

    @property
    def risk_level(self) -> str:
        """リスクレベル"""
        return self.security.get("risk_level", "UNKNOWN")

    def to_dict(self) -> Dict[str, Any]:
        """辞書に変換"""
        return self.data


class SkillProposal:
    """Skill提案（抽出 + レビュー）"""

    def __init__(
        self,
        skill: SkillDefinition,
        review: SkillReview,
        extraction_metadata: Optional[Dict] = None,
    ):
        self.skill = skill
        self.review = review
        self.extraction_metadata = extraction_metadata or {}
        self.proposed_at = datetime.utcnow().isoformat()
        self.status = "pending"  # pending, approved, rejected

    def to_dict(self) -> Dict[str, Any]:
        """辞書に変換"""
        return {
            "skill": self.skill.to_dict(),
            "review": self.review.to_dict(),
            "extraction_metadata": self.extraction_metadata,
            "proposed_at": self.proposed_at,
            "status": self.status,
        }


class SkillManager:
    """Skill管理クラス"""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.skills_dir = project_path / ".mao" / "skills"
        self.proposals_dir = project_path / ".mao" / "skill_proposals"

        # ディレクトリ作成
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.proposals_dir.mkdir(parents=True, exist_ok=True)

    def list_skills(self) -> List[SkillDefinition]:
        """登録済みのskill一覧を取得"""
        skills = []

        for yaml_file in self.skills_dir.glob("*.yaml"):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                    skills.append(SkillDefinition(data))
            except Exception as e:
                print(f"Warning: Failed to load skill from {yaml_file}: {e}")

        return skills

    def get_skill(self, name: str) -> Optional[SkillDefinition]:
        """特定のskillを取得"""
        skill_file = self.skills_dir / f"{name}.yaml"

        if not skill_file.exists():
            return None

        with open(skill_file) as f:
            data = yaml.safe_load(f)
            return SkillDefinition(data)

    def save_skill(self, skill: SkillDefinition) -> Path:
        """Skillを保存"""
        skill_file = self.skills_dir / f"{skill.name}.yaml"

        with open(skill_file, "w") as f:
            f.write(skill.to_yaml())

        # スクリプトファイルがある場合は保存
        if skill.script:
            script_file = self.skills_dir / f"{skill.name}.sh"
            with open(script_file, "w") as f:
                f.write(skill.script)
            script_file.chmod(0o755)  # 実行権限付与

        return skill_file

    def delete_skill(self, name: str) -> bool:
        """Skillを削除"""
        skill_file = self.skills_dir / f"{name}.yaml"
        script_file = self.skills_dir / f"{name}.sh"

        deleted = False

        if skill_file.exists():
            skill_file.unlink()
            deleted = True

        if script_file.exists():
            script_file.unlink()

        return deleted

    def save_proposal(self, proposal: SkillProposal) -> Path:
        """Skill提案を保存"""
        proposal_file = (
            self.proposals_dir
            / f"{proposal.skill.name}_{int(datetime.utcnow().timestamp())}.json"
        )

        with open(proposal_file, "w") as f:
            json.dump(proposal.to_dict(), f, indent=2)

        return proposal_file

    def list_proposals(self) -> List[SkillProposal]:
        """保留中のSkill提案一覧"""
        proposals = []

        for json_file in self.proposals_dir.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)

                    # pending状態のもののみ
                    if data.get("status") == "pending":
                        skill = SkillDefinition(data["skill"])
                        review = SkillReview(data["review"])
                        proposal = SkillProposal(
                            skill=skill,
                            review=review,
                            extraction_metadata=data.get("extraction_metadata"),
                        )
                        proposal.proposed_at = data.get("proposed_at")
                        proposal.status = data.get("status")
                        proposals.append(proposal)

            except Exception as e:
                print(f"Warning: Failed to load proposal from {json_file}: {e}")

        return proposals

    def approve_proposal(self, proposal: SkillProposal) -> Path:
        """Skill提案を承認"""
        # Skillとして保存
        skill_file = self.save_skill(proposal.skill)

        # 提案ステータスを更新
        proposal.status = "approved"
        self._update_proposal_status(proposal)

        return skill_file

    def reject_proposal(self, proposal: SkillProposal, reason: str = "") -> None:
        """Skill提案を却下"""
        proposal.status = "rejected"
        if reason:
            proposal.extraction_metadata["rejection_reason"] = reason

        self._update_proposal_status(proposal)

    def _update_proposal_status(self, proposal: SkillProposal) -> None:
        """提案ステータスを更新"""
        # 既存の提案ファイルを探して更新
        for json_file in self.proposals_dir.glob(f"{proposal.skill.name}_*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)

                if data.get("proposed_at") == proposal.proposed_at:
                    # ステータス更新
                    data["status"] = proposal.status
                    data["extraction_metadata"] = proposal.extraction_metadata

                    with open(json_file, "w") as f:
                        json.dump(data, f, indent=2)
                    break

            except Exception as e:
                print(f"Warning: Failed to update proposal status: {e}")

    def skill_exists(self, name: str) -> bool:
        """Skillが既に存在するか"""
        return (self.skills_dir / f"{name}.yaml").exists()

    def get_skill_count(self) -> int:
        """登録済みskill数"""
        return len(list(self.skills_dir.glob("*.yaml")))

    def get_proposal_count(self) -> int:
        """保留中の提案数"""
        return len(self.list_proposals())
