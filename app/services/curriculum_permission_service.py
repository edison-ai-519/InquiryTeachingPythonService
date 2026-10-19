import datetime as dt

from sqlalchemy.orm import Session

from app.agents.registry import AgentRegistry, get_agent_registry
from app.db.models import CurriculumSourceAgentPermissionModel, CurriculumSourceModel
from sqlalchemy import or_


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


class CurriculumPermissionService:
    @staticmethod
    def allowed_sources_for_role(db: Session, role_category: str) -> list[str]:
        """Return only curated knowledge sources assigned to the given workspace."""
        rows = (
            db.query(CurriculumSourceModel.source)
            .outerjoin(
                CurriculumSourceAgentPermissionModel,
                CurriculumSourceAgentPermissionModel.source == CurriculumSourceModel.source,
            )
            .filter(
                or_(
                    CurriculumSourceModel.category == "rural_revitalization",
                    CurriculumSourceAgentPermissionModel.role_category == role_category,
                )
            )
            .distinct()
            .order_by(CurriculumSourceModel.source.asc())
            .all()
        )
        return [str(row[0]) for row in rows]

    @staticmethod
    def validate_expert_ids(
        expert_ids: list[str],
        registry: AgentRegistry | None = None,
    ) -> list[str]:
        registry = registry or get_agent_registry()
        result: list[str] = []
        seen: set[str] = set()
        invalid: list[str] = []
        for agent_id in expert_ids:
            if agent_id in seen:
                continue
            seen.add(agent_id)
            if registry.selectable_expert(agent_id) is None:
                invalid.append(agent_id)
            else:
                result.append(agent_id)
        if invalid:
            raise ValueError(f"未知或不可选择的专家 Agent：{', '.join(invalid)}")
        return result

    @staticmethod
    def allowed_expert_ids(
        db: Session,
        source: str,
        role_category: str | None = None,
    ) -> list[str]:
        query = (
            db.query(CurriculumSourceAgentPermissionModel)
            .filter(CurriculumSourceAgentPermissionModel.source == source)
        )
        if role_category is not None:
            query = query.filter(
                CurriculumSourceAgentPermissionModel.role_category == role_category
            )
        query = query.order_by(CurriculumSourceAgentPermissionModel.agent_id.asc())
        return [str(row.agent_id) for row in query.all()]

    @staticmethod
    def allowed_sources(
        db: Session,
        expert_id: str,
        role_category: str | None = None,
    ) -> list[str]:
        query = (
            db.query(CurriculumSourceAgentPermissionModel)
            .filter(CurriculumSourceAgentPermissionModel.agent_id == expert_id)
        )
        if role_category is not None:
            query = query.filter(
                CurriculumSourceAgentPermissionModel.role_category == role_category
            )
        query = query.order_by(CurriculumSourceAgentPermissionModel.source.asc())
        return [str(row.source) for row in query.all()]

    @staticmethod
    def permissions_by_source(db: Session) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        rows = (
            db.query(CurriculumSourceAgentPermissionModel)
            .filter(CurriculumSourceAgentPermissionModel.role_category == "teacher")
            .order_by(
                CurriculumSourceAgentPermissionModel.source.asc(),
                CurriculumSourceAgentPermissionModel.agent_id.asc(),
            )
            .all()
        )
        for row in rows:
            result.setdefault(str(row.source), []).append(str(row.agent_id))
        return result

    @staticmethod
    def replace_permissions(
        db: Session,
        source: str,
        expert_ids: list[str],
        role_category: str = "teacher",
    ) -> list[str]:
        normalized = CurriculumPermissionService.validate_expert_ids(expert_ids)
        exists = (
            db.query(CurriculumSourceModel)
            .filter(CurriculumSourceModel.source == source)
            .first()
        )
        if not exists:
            raise LookupError("知识文件不存在")

        db.query(CurriculumSourceAgentPermissionModel).filter(
            CurriculumSourceAgentPermissionModel.source == source,
            CurriculumSourceAgentPermissionModel.role_category == role_category,
        ).delete(synchronize_session=False)
        timestamp = _now_iso()
        for agent_id in normalized:
            db.add(
                CurriculumSourceAgentPermissionModel(
                    source=source,
                    agent_id=agent_id,
                    role_category=role_category,
                    created_at=timestamp,
                )
            )
        db.flush()
        return normalized
