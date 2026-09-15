from __future__ import annotations

import datetime as dt
import re
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import (
    CurriculumSourceModel,
    KnowledgeSourceReviewEventModel,
    KnowledgeSourceTopicModel,
)
from app.services.curriculum_knowledge_service import CurriculumFileError, now_iso


POLICY_LAYERS = {
    "foundation",
    "annual_action",
    "ceo_talent",
    "grassroots_compliance",
}
DOCUMENT_TYPES = {
    "law",
    "local_regulation",
    "policy_plan",
    "administrative_measure",
    "notice",
    "training_program",
    "case_material",
    "official_information",
    "guide",
    "reference",
}
AUTHORITY_SCOPES = {"", "national", "beijing", "district"}
VALIDITY_STATUSES = {
    "current",
    "expired",
    "repealed",
    "unknown",
    "not_applicable",
}
REVIEW_STATUSES = {"draft", "in_review", "published", "archived"}
TOPIC_CODES = {
    "organization_governance",
    "land_homestead",
    "collective_assets",
    "industry_development",
    "agritourism",
    "project_finance",
    "talent_development",
    "public_services",
    "ecology_environment",
    "safety_emergency",
    "digital_rural",
}
OPTIONAL_DOCUMENT_NUMBER_TYPES = {
    "training_program",
    "case_material",
    "official_information",
}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _clean(value: object) -> str:
    return str(value or "").strip()


def _validate_date(value: str, field_name: str) -> str:
    value = _clean(value)
    if not value:
        return ""
    if not DATE_RE.fullmatch(value):
        raise CurriculumFileError(f"{field_name} 必须使用 YYYY-MM-DD 格式")
    try:
        dt.date.fromisoformat(value)
    except ValueError as exc:
        raise CurriculumFileError(f"{field_name} 不是有效日期") from exc
    return value


class KnowledgeSourceService:
    def __init__(self, db: Session):
        self.db = db

    def by_id(self, source_id: str) -> CurriculumSourceModel:
        row = (
            self.db.query(CurriculumSourceModel)
            .filter(CurriculumSourceModel.id == source_id)
            .first()
        )
        if row is None:
            raise LookupError("知识来源不存在")
        return row

    def topics(self, source_id: str) -> list[str]:
        return [
            row.topic_code
            for row in self.db.query(KnowledgeSourceTopicModel)
            .filter(KnowledgeSourceTopicModel.source_id == source_id)
            .order_by(KnowledgeSourceTopicModel.topic_code.asc())
            .all()
        ]

    def replace_topics(self, source_id: str, topics: list[str]) -> list[str]:
        normalized = sorted({_clean(topic).lower() for topic in topics if _clean(topic)})
        invalid = [topic for topic in normalized if topic not in TOPIC_CODES]
        if invalid:
            raise CurriculumFileError(f"未知主题标签：{', '.join(invalid)}")
        self.db.query(KnowledgeSourceTopicModel).filter(
            KnowledgeSourceTopicModel.source_id == source_id
        ).delete(synchronize_session=False)
        self.db.add_all(
            KnowledgeSourceTopicModel(source_id=source_id, topic_code=topic)
            for topic in normalized
        )
        return normalized

    def update_metadata(self, row: CurriculumSourceModel, payload: dict) -> None:
        if not isinstance(payload, dict):
            raise CurriculumFileError("metadata_json 必须是 JSON 对象")
        string_fields = {
            "title",
            "region_code",
            "issuing_authority",
            "document_number",
            "source_url",
            "review_note",
            "replaces_source_id",
        }
        for field in string_fields:
            if field in payload:
                setattr(row, field, _clean(payload[field]))

        if "policy_layer" in payload:
            layer = _clean(payload["policy_layer"]).lower() or None
            if layer is not None and layer not in POLICY_LAYERS:
                raise CurriculumFileError("乡村振兴政策层次无效")
            row.policy_layer = layer
        if "document_type" in payload:
            value = _clean(payload["document_type"]).lower()
            if value not in DOCUMENT_TYPES:
                raise CurriculumFileError("资料性质无效")
            row.document_type = value
        if "authority_scope" in payload:
            value = _clean(payload["authority_scope"]).lower()
            if value not in AUTHORITY_SCOPES:
                raise CurriculumFileError("地域层级无效")
            row.authority_scope = value
        if "validity_status" in payload:
            value = _clean(payload["validity_status"]).lower()
            if value not in VALIDITY_STATUSES:
                raise CurriculumFileError("效力状态无效")
            row.validity_status = value
        for field in ("publish_date", "effective_date", "expiry_date", "last_verified_at"):
            if field in payload:
                setattr(row, field, _validate_date(payload[field], field))

        if row.category != "rural_revitalization":
            row.policy_layer = None
        row.updated_at = now_iso()

    def publish_errors(self, row: CurriculumSourceModel) -> list[str]:
        if row.category != "rural_revitalization":
            return []
        required = {
            "policy_layer": "四层主归属",
            "title": "标题",
            "document_type": "资料性质",
            "authority_scope": "地域层级",
            "region_code": "行政区划代码",
            "issuing_authority": "发文机关",
            "publish_date": "发布日期",
            "source_url": "官网来源",
            "validity_status": "效力状态",
            "last_verified_at": "核验日期",
            "checksum": "内容校验和",
        }
        errors = [label for field, label in required.items() if not _clean(getattr(row, field, ""))]
        if row.policy_layer not in POLICY_LAYERS:
            errors.append("有效的四层主归属")
        if row.document_type not in DOCUMENT_TYPES:
            errors.append("有效的资料性质")
        if row.authority_scope not in AUTHORITY_SCOPES - {""}:
            errors.append("有效的地域层级")
        if row.validity_status not in VALIDITY_STATUSES - {"unknown"}:
            errors.append("明确的效力状态")
        if row.document_type not in OPTIONAL_DOCUMENT_NUMBER_TYPES and not row.document_number:
            errors.append("文号")
        if not row.source_url.startswith(("https://", "http://")):
            errors.append("有效的官网URL")
        if int(row.chunk_count or 0) < 1:
            errors.append("可用解析片段")
        return list(dict.fromkeys(errors))

    def review(self, row: CurriculumSourceModel, action: str, actor_user_id: str, note: str = "") -> None:
        action = _clean(action).lower()
        transitions = {
            "submit": ({"draft"}, "in_review"),
            "return": ({"in_review"}, "draft"),
            "publish": ({"in_review"}, "published"),
            "archive": ({"published"}, "archived"),
        }
        if action not in transitions:
            raise CurriculumFileError("审核操作无效")
        allowed_from, target = transitions[action]
        current = row.review_status or "draft"
        if current not in allowed_from:
            raise CurriculumFileError(f"不能从 {current} 执行 {action}")
        if action == "publish":
            errors = self.publish_errors(row)
            if errors:
                raise CurriculumFileError("发布前需补齐：" + "、".join(errors))
        timestamp = now_iso()
        self.db.add(
            KnowledgeSourceReviewEventModel(
                id=uuid.uuid4().hex,
                source_id=row.id,
                action=action,
                from_status=current,
                to_status=target,
                note=_clean(note),
                actor_user_id=actor_user_id,
                created_at=timestamp,
            )
        )
        row.review_status = target
        row.review_note = _clean(note)
        row.reviewed_by_user_id = actor_user_id
        row.reviewed_at = timestamp
        row.updated_at = timestamp

    def invalidate_publication(
        self,
        row: CurriculumSourceModel,
        action: str,
        actor_user_id: str,
        note: str,
    ) -> None:
        if row.category != "rural_revitalization":
            return
        current = row.review_status or "draft"
        if current == "draft":
            return
        timestamp = now_iso()
        self.db.add(
            KnowledgeSourceReviewEventModel(
                id=uuid.uuid4().hex,
                source_id=row.id,
                action=action,
                from_status=current,
                to_status="draft",
                note=_clean(note),
                actor_user_id=actor_user_id,
                created_at=timestamp,
            )
        )
        row.review_status = "draft"
        row.review_note = _clean(note)
        row.reviewed_by_user_id = actor_user_id
        row.reviewed_at = timestamp
        row.updated_at = timestamp

    def review_events(self, source_id: str) -> list[dict]:
        rows = (
            self.db.query(KnowledgeSourceReviewEventModel)
            .filter(KnowledgeSourceReviewEventModel.source_id == source_id)
            .order_by(KnowledgeSourceReviewEventModel.created_at.asc())
            .all()
        )
        return [
            {
                "id": row.id,
                "action": row.action,
                "from_status": row.from_status,
                "to_status": row.to_status,
                "note": row.note,
                "actor_user_id": row.actor_user_id,
                "created_at": row.created_at,
            }
            for row in rows
        ]

    def serialize(self, row: CurriculumSourceModel, *, include_review_events: bool = False) -> dict:
        data = {
            "id": row.id,
            "source": row.source,
            "category": row.category or "curriculum",
            "extension": Path(row.source).suffix.lower(),
            "title": row.title or Path(row.source).stem,
            "policy_layer": row.policy_layer,
            "document_type": row.document_type or "reference",
            "authority_scope": row.authority_scope or "",
            "region_code": row.region_code or "",
            "issuing_authority": row.issuing_authority or "",
            "document_number": row.document_number or "",
            "source_url": row.source_url or "",
            "publish_date": row.publish_date or "",
            "effective_date": row.effective_date or "",
            "expiry_date": row.expiry_date or "",
            "validity_status": row.validity_status or "unknown",
            "review_status": row.review_status or "draft",
            "review_note": row.review_note or "",
            "reviewed_by_user_id": row.reviewed_by_user_id or "",
            "reviewed_at": row.reviewed_at or "",
            "last_verified_at": row.last_verified_at or "",
            "replaces_source_id": row.replaces_source_id or "",
            "topics": self.topics(row.id),
            "checksum": row.checksum or "",
            "chunk_count": int(row.chunk_count or 0),
            "vector_chunk_count": int(row.vector_chunk_count or 0),
            "vector_status": row.vector_status or "pending",
            "embedding_model": row.embedding_model or "",
            "last_error": row.last_error or "",
            "updated_at": row.updated_at or "",
            "publish_errors": self.publish_errors(row),
        }
        if include_review_events:
            data["review_events"] = self.review_events(row.id)
        return data
