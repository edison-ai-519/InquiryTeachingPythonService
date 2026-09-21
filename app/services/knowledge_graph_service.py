from __future__ import annotations

import datetime as dt
import json
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import (
    CurriculumChunkModel,
    CurriculumSourceModel,
    GlobiInteractionModel,
    KnowledgeEntityMentionModel,
    KnowledgeEntityModel,
    KnowledgeEntitySourceModel,
    KnowledgeEntityTaxonModel,
    KnowledgeRelationEvidenceModel,
    KnowledgeRelationGlobiEvidenceModel,
    KnowledgeRelationModel,
)


CONFIDENCE_WEIGHT = {"high": 3, "medium": 2, "low": 1}
ALLOWED_ENTITY_TYPES = {
    "insect",
    "plant",
    "habitat",
    "season",
    "behavior",
    "concept",
}
DEFAULT_EXPERT_ENTITY_TYPES = {
    "insect_agent": ["insect", "plant", "habitat"],
    "nature_agent": ["plant", "insect", "habitat", "season"],
}
PREDICATE_LABELS = {
    "feeds_on": "取食",
    "visits": "访花",
    "pollinates": "授粉",
    "lives_on": "栖息",
    "lays_eggs_on": "产卵于",
    "damages": "危害",
    "predator_of": "捕食",
    "parasite_of": "寄生",
    "attracted_by": "被吸引",
    "associated_with": "相关",
    "produces": "产生",
    "performs": "进行",
}
ALLOWED_PREDICATES = set(PREDICATE_LABELS)


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


def _json_list(value) -> list[str]:
    if isinstance(value, list):
        return list(
            dict.fromkeys(
                str(item).strip() for item in value if str(item).strip()
            )
        )
    return []


def _empty_graph_payload() -> dict:
    return {
        "entities": [],
        "relations": [],
        "paths": [],
        "recommended_path_ids": [],
    }


def _source_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(
        dict.fromkeys(str(item).strip() for item in value if str(item).strip())
    )


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "").casefold()


@dataclass(frozen=True)
class GraphSelectionValidation:
    valid: bool
    warning: str = ""


class KnowledgeGraphService:
    def __init__(self, db: Session):
        self.db = db

    def import_graph_json(self, payload: dict) -> dict:
        timestamp = _now_iso()
        entity_count = 0
        relation_count = 0
        entity_sources: dict[str, list[str]] = {}
        entity_sources_configured: set[str] = set()
        requested_sources: set[str] = set()
        payload_entity_ids: set[str] = set()

        entities_payload = payload.get("entities") or []
        relations_payload = payload.get("relations") or []
        if not isinstance(entities_payload, list) or not isinstance(relations_payload, list):
            raise ValueError("图谱必须包含 entities 和 relations 数组")

        for item in entities_payload:
            entity_id = str(item.get("id") or "").strip()
            name = str(item.get("name") or "").strip()
            entity_type = str(item.get("entity_type") or "").strip()
            self._validate_entity_values(name, entity_type)
            if not entity_id:
                raise ValueError("图谱实体必须包含 id")
            payload_entity_ids.add(entity_id)
            if "rag_sources" in item:
                sources = _source_list(item.get("rag_sources"))
                entity_sources[entity_id] = sources
                entity_sources_configured.add(entity_id)
                requested_sources.update(sources)

        existing_entity_ids = {
            row.id for row in self.db.query(KnowledgeEntityModel).all()
        }
        valid_entity_ids = existing_entity_ids | payload_entity_ids
        for item in relations_payload:
            relation_id = str(item.get("id") or "").strip()
            subject_id = str(item.get("subject_entity_id") or "").strip()
            object_id = str(item.get("object_entity_id") or "").strip()
            predicate = str(item.get("predicate") or "").strip()
            if not relation_id or not subject_id or not object_id or not predicate:
                raise ValueError(
                    "图谱关系必须包含 id、subject_entity_id、predicate 和 object_entity_id"
                )
            self._validate_relation_values(subject_id, predicate, object_id, valid_entity_ids)
        node_requested_sources = requested_sources
        if node_requested_sources:
            existing_sources = {
                row.source
                for row in self.db.query(CurriculumSourceModel)
                .filter(CurriculumSourceModel.source.in_(node_requested_sources))
                .all()
            }
            missing_sources = sorted(node_requested_sources - existing_sources)
            if missing_sources:
                raise ValueError(f"知识库不存在：{', '.join(missing_sources)}")

        imported_entity_ids: list[str] = []
        for item in entities_payload:
            entity_id = str(item.get("id") or "").strip()
            row = self.db.get(KnowledgeEntityModel, entity_id)
            if row is None:
                row = KnowledgeEntityModel(id=entity_id, created_at=timestamp)
                self.db.add(row)
                entity_count += 1
            self._assign_entity(
                row,
                name=str(item.get("name") or "").strip(),
                entity_type=str(item.get("entity_type") or "").strip(),
                aliases=_json_list(item.get("aliases")),
                description=str(item.get("description") or "").strip(),
                source=str(item.get("source") or "").strip(),
                timestamp=timestamp,
            )
            self.db.flush()
            imported_entity_ids.append(entity_id)
            if entity_id in entity_sources_configured:
                self.replace_rag_sources(
                    entity_id,
                    entity_sources.get(entity_id, []),
                    timestamp=timestamp,
                )
        self.db.flush()

        for item in relations_payload:
            relation_id = str(item.get("id") or "").strip()
            row = self.db.get(KnowledgeRelationModel, relation_id)
            if row is None:
                row = KnowledgeRelationModel(id=relation_id, created_at=timestamp)
                self.db.add(row)
                relation_count += 1
            self._assign_relation(
                row,
                subject_entity_id=str(item.get("subject_entity_id") or "").strip(),
                predicate=str(item.get("predicate") or "").strip(),
                object_entity_id=str(item.get("object_entity_id") or "").strip(),
                description=str(item.get("description") or "").strip(),
                evidence_source=str(item.get("evidence_source") or "").strip(),
                confidence=str(item.get("confidence") or "medium").strip() or "medium",
                timestamp=timestamp,
            )
            self.db.flush()
            if "evidence_chunk_ids" in item:
                self.replace_relation_evidence(
                    relation_id,
                    [int(value) for value in item.get("evidence_chunk_ids") or []],
                    timestamp=timestamp,
                )

        for entity_id in imported_entity_ids:
            self.rebuild_mentions_for_entity(entity_id)
        self.db.flush()
        return {"entity_count": entity_count, "relation_count": relation_count}

    def create_entity(
        self,
        *,
        name: str,
        entity_type: str,
        aliases: list[str],
        description: str = "",
        source: str = "manual",
    ) -> dict:
        timestamp = _now_iso()
        normalized_name = name.strip()
        normalized_aliases = _json_list(aliases)
        self._validate_entity_values(normalized_name, entity_type)
        self._ensure_unique_entity_names(normalized_name, normalized_aliases)
        row = KnowledgeEntityModel(
            id=f"entity_{uuid.uuid4().hex[:16]}",
            created_at=timestamp,
        )
        self._assign_entity(
            row,
            name=normalized_name,
            entity_type=entity_type,
            aliases=normalized_aliases,
            description=description.strip(),
            source=source.strip() or "manual",
            timestamp=timestamp,
        )
        self.db.add(row)
        self.db.flush()
        self.rebuild_mentions_for_entity(row.id)
        return self.serialize_entity(row)

    def update_entity(
        self,
        entity_id: str,
        *,
        name: str,
        entity_type: str,
        aliases: list[str],
        description: str = "",
        source: str = "manual",
    ) -> dict:
        row = self.db.get(KnowledgeEntityModel, entity_id)
        if row is None:
            raise LookupError("图谱节点不存在")
        normalized_name = name.strip()
        normalized_aliases = _json_list(aliases)
        self._validate_entity_values(normalized_name, entity_type)
        self._ensure_unique_entity_names(
            normalized_name,
            normalized_aliases,
            exclude_entity_id=entity_id,
        )
        self._assign_entity(
            row,
            name=normalized_name,
            entity_type=entity_type,
            aliases=normalized_aliases,
            description=description.strip(),
            source=source.strip() or row.source or "manual",
            timestamp=_now_iso(),
        )
        if (row.origin or "manual") in {"lightrag", "globi"}:
            row.management_mode = "manual_override"
        self.db.flush()
        self.rebuild_mentions_for_entity(entity_id)
        return self.serialize_entity(row)

    def delete_entity(self, entity_id: str) -> None:
        row = self.db.get(KnowledgeEntityModel, entity_id)
        if row is None:
            raise LookupError("图谱节点不存在")
        self.db.delete(row)
        self.db.flush()

    def create_relation(
        self,
        *,
        subject_entity_id: str,
        predicate: str,
        object_entity_id: str,
        description: str = "",
        confidence: str = "medium",
        evidence_chunk_ids: list[int] | None = None,
    ) -> dict:
        timestamp = _now_iso()
        self._validate_relation_values(subject_entity_id, predicate, object_entity_id)
        duplicate = (
            self.db.query(KnowledgeRelationModel)
            .filter(
                KnowledgeRelationModel.subject_entity_id == subject_entity_id,
                KnowledgeRelationModel.predicate == predicate,
                KnowledgeRelationModel.object_entity_id == object_entity_id,
            )
            .first()
        )
        if duplicate is not None:
            raise ValueError("相同起点、关系和终点的图谱关系已存在")
        row = KnowledgeRelationModel(
            id=f"relation_{uuid.uuid4().hex[:16]}",
            origin="manual",
            management_mode="manual",
            status="active",
            created_at=timestamp,
        )
        self._assign_relation(
            row,
            subject_entity_id=subject_entity_id,
            predicate=predicate,
            object_entity_id=object_entity_id,
            description=description.strip(),
            evidence_source="",
            confidence=confidence,
            timestamp=timestamp,
        )
        self.db.add(row)
        self.db.flush()
        self.replace_relation_evidence(
            row.id,
            evidence_chunk_ids or [],
            timestamp=timestamp,
        )
        return self.serialize_relation(row)

    def update_relation(
        self,
        relation_id: str,
        *,
        subject_entity_id: str,
        predicate: str,
        object_entity_id: str,
        description: str = "",
        confidence: str = "medium",
        evidence_chunk_ids: list[int] | None = None,
    ) -> dict:
        row = self.db.get(KnowledgeRelationModel, relation_id)
        if row is None:
            raise LookupError("图谱关系不存在")
        self._validate_relation_values(subject_entity_id, predicate, object_entity_id)
        duplicate = (
            self.db.query(KnowledgeRelationModel)
            .filter(
                KnowledgeRelationModel.id != relation_id,
                KnowledgeRelationModel.subject_entity_id == subject_entity_id,
                KnowledgeRelationModel.predicate == predicate,
                KnowledgeRelationModel.object_entity_id == object_entity_id,
            )
            .first()
        )
        if duplicate is not None:
            raise ValueError("相同起点、关系和终点的图谱关系已存在")
        self._assign_relation(
            row,
            subject_entity_id=subject_entity_id,
            predicate=predicate,
            object_entity_id=object_entity_id,
            description=description.strip(),
            evidence_source=row.evidence_source,
            confidence=confidence,
            timestamp=_now_iso(),
        )
        if (row.origin or "manual") in {"lightrag", "globi"}:
            row.management_mode = "manual_override"
        row.status = "active"
        self.db.flush()
        if evidence_chunk_ids is not None:
            self.replace_relation_evidence(relation_id, evidence_chunk_ids)
        return self.serialize_relation(row)

    def delete_relation(self, relation_id: str) -> None:
        row = self.db.get(KnowledgeRelationModel, relation_id)
        if row is None:
            raise LookupError("图谱关系不存在")
        if (row.origin or "manual") in {"lightrag", "globi"}:
            row.status = "suppressed"
            row.management_mode = "manual_override"
            row.updated_at = _now_iso()
        else:
            self.db.delete(row)
        self.db.flush()

    def restore_auto_relation(self, relation_id: str) -> dict:
        row = self.db.get(KnowledgeRelationModel, relation_id)
        if row is None:
            raise LookupError("图谱关系不存在")
        if (row.origin or "manual") not in {"lightrag", "globi"}:
            raise ValueError("只有自动关系可以恢复自动管理")
        row.status = "active"
        row.management_mode = "auto"
        row.updated_at = _now_iso()
        self.db.flush()
        return self.serialize_relation(row)

    def resolve_or_create_auto_entity(
        self,
        *,
        name: str,
        entity_type: str,
        source: str,
        extractor_model: str,
        extractor_version: str,
    ) -> KnowledgeEntityModel:
        normalized = _normalized_text(name)
        for entity in self.db.query(KnowledgeEntityModel).all():
            variants = [entity.name, *self.aliases(entity)]
            if normalized in {_normalized_text(value) for value in variants}:
                if (
                    (entity.origin or "manual") == "lightrag"
                    and entity.management_mode == "auto"
                ):
                    timestamp = _now_iso()
                    entity.extractor_model = extractor_model
                    entity.extractor_version = extractor_version
                    entity.last_auto_sync_at = timestamp
                    entity.updated_at = timestamp
                    self._bind_auto_entity_source(entity, source)
                return entity
        self._validate_entity_values(name.strip(), entity_type)
        timestamp = _now_iso()
        entity = KnowledgeEntityModel(
            id=f"entity_{uuid.uuid4().hex[:16]}",
            name=name.strip(),
            entity_type=entity_type,
            aliases_json="[]",
            description="",
            source="lightrag",
            origin="lightrag",
            management_mode="auto",
            extractor_model=extractor_model,
            extractor_version=extractor_version,
            last_auto_sync_at=timestamp,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.db.add(entity)
        self.db.flush()
        self._bind_auto_entity_source(entity, source)
        self.rebuild_mentions_for_entity(entity.id)
        return entity

    def _bind_auto_entity_source(
        self,
        entity: KnowledgeEntityModel,
        source: str,
    ) -> None:
        if not source or self.db.get(
            KnowledgeEntitySourceModel,
            {"entity_id": entity.id, "source": source},
        ):
            return
        self.db.add(
            KnowledgeEntitySourceModel(
                entity_id=entity.id,
                source=source,
                created_at=_now_iso(),
            )
        )
        self.db.flush()

    def clear_auto_evidence_for_source(self, source: str) -> None:
        relation_ids = [
            row.id
            for row in self.db.query(KnowledgeRelationModel).filter(
                KnowledgeRelationModel.origin == "lightrag",
                KnowledgeRelationModel.management_mode == "auto",
            )
        ]
        if relation_ids:
            self.db.query(KnowledgeRelationEvidenceModel).filter(
                KnowledgeRelationEvidenceModel.relation_id.in_(relation_ids),
                KnowledgeRelationEvidenceModel.source == source,
            ).delete(synchronize_session=False)
        self.db.flush()

    def clear_auto_entity_sources_for_source(self, source: str) -> None:
        automatic_entity_ids = [
            row.id
            for row in self.db.query(KnowledgeEntityModel).filter(
                KnowledgeEntityModel.origin == "lightrag",
                KnowledgeEntityModel.management_mode == "auto",
            )
        ]
        if automatic_entity_ids:
            self.db.query(KnowledgeEntitySourceModel).filter(
                KnowledgeEntitySourceModel.entity_id.in_(automatic_entity_ids),
                KnowledgeEntitySourceModel.source == source,
            ).delete(synchronize_session=False)
        self.db.flush()

    def upsert_auto_relation(
        self,
        *,
        subject_entity_id: str,
        predicate: str,
        object_entity_id: str,
        description: str,
        evidence_chunk_ids: list[int],
        extractor_model: str,
        extractor_version: str,
    ) -> tuple[KnowledgeRelationModel, bool]:
        self._validate_relation_values(subject_entity_id, predicate, object_entity_id)
        row = (
            self.db.query(KnowledgeRelationModel)
            .filter(
                KnowledgeRelationModel.subject_entity_id == subject_entity_id,
                KnowledgeRelationModel.predicate == predicate,
                KnowledgeRelationModel.object_entity_id == object_entity_id,
            )
            .first()
        )
        timestamp = _now_iso()
        created = row is None
        if row is None:
            row = KnowledgeRelationModel(
                id=f"relation_{uuid.uuid4().hex[:16]}",
                subject_entity_id=subject_entity_id,
                predicate=predicate,
                object_entity_id=object_entity_id,
                description=description.strip(),
                evidence_source="",
                confidence="high",
                origin="lightrag",
                management_mode="auto",
                status="active",
                extractor_model=extractor_model,
                extractor_version=extractor_version,
                last_auto_sync_at=timestamp,
                created_at=timestamp,
                updated_at=timestamp,
            )
            self.db.add(row)
            self.db.flush()
        elif row.status == "suppressed":
            return row, False
        elif row.management_mode == "auto":
            row.description = description.strip() or row.description
            row.confidence = "high"
            row.extractor_model = extractor_model
            row.extractor_version = extractor_version
            row.last_auto_sync_at = timestamp
            row.updated_at = timestamp
            row.status = "active"

        chunks = (
            self.db.query(CurriculumChunkModel)
            .filter(CurriculumChunkModel.id.in_(list(dict.fromkeys(evidence_chunk_ids))))
            .all()
        )
        for chunk in chunks:
            key = {"relation_id": row.id, "chunk_id": int(chunk.id)}
            evidence = self.db.get(KnowledgeRelationEvidenceModel, key)
            if evidence is None:
                self.db.add(
                    KnowledgeRelationEvidenceModel(
                        relation_id=row.id,
                        chunk_id=int(chunk.id),
                        source=chunk.source,
                        evidence_text=chunk.content,
                        created_at=timestamp,
                    )
                )
        self.db.flush()
        sources = [item[0] for item in self.db.query(
            KnowledgeRelationEvidenceModel.source
        ).filter(
            KnowledgeRelationEvidenceModel.relation_id == row.id
        ).distinct().all()]
        row.evidence_source = "、".join(sorted(sources))
        self.db.flush()
        return row, created

    def prune_unverified_auto_relations(self) -> int:
        rows = self.db.query(KnowledgeRelationModel).filter(
            KnowledgeRelationModel.origin == "lightrag",
            KnowledgeRelationModel.management_mode == "auto",
            KnowledgeRelationModel.status == "active",
        ).all()
        evidence_counts = self._evidence_count_map([row.id for row in rows])
        removed = 0
        for row in rows:
            if not evidence_counts.get(row.id):
                self.db.delete(row)
                removed += 1
        self.db.flush()
        return removed

    def prune_orphan_auto_entities(self) -> int:
        rows = self.db.query(KnowledgeEntityModel).filter(
            KnowledgeEntityModel.origin == "lightrag",
            KnowledgeEntityModel.management_mode == "auto",
        ).all()
        removed = 0
        for row in rows:
            has_relation = self.db.query(KnowledgeRelationModel.id).filter(
                or_(
                    KnowledgeRelationModel.subject_entity_id == row.id,
                    KnowledgeRelationModel.object_entity_id == row.id,
                )
            ).first()
            has_mention = self.db.query(KnowledgeEntityMentionModel.entity_id).filter(
                KnowledgeEntityMentionModel.entity_id == row.id
            ).first()
            has_source = self.db.query(KnowledgeEntitySourceModel.entity_id).filter(
                KnowledgeEntitySourceModel.entity_id == row.id
            ).first()
            if not has_relation and not has_mention and not has_source:
                self.db.delete(row)
                removed += 1
        self.db.flush()
        return removed

    def _assign_entity(
        self,
        row: KnowledgeEntityModel,
        *,
        name: str,
        entity_type: str,
        aliases: list[str],
        description: str,
        source: str,
        timestamp: str,
    ) -> None:
        row.name = name
        row.entity_type = entity_type
        row.aliases_json = json.dumps(
            [alias for alias in aliases if _normalized_text(alias) != _normalized_text(name)],
            ensure_ascii=False,
        )
        row.description = description
        row.source = source
        row.updated_at = timestamp

    def _assign_relation(
        self,
        row: KnowledgeRelationModel,
        *,
        subject_entity_id: str,
        predicate: str,
        object_entity_id: str,
        description: str,
        evidence_source: str,
        confidence: str,
        timestamp: str,
    ) -> None:
        if confidence not in CONFIDENCE_WEIGHT:
            raise ValueError("关系置信度必须是 high、medium 或 low")
        row.subject_entity_id = subject_entity_id
        row.predicate = predicate
        row.object_entity_id = object_entity_id
        row.description = description
        row.evidence_source = evidence_source
        row.confidence = confidence
        row.updated_at = timestamp

    def _validate_entity_values(self, name: str, entity_type: str) -> None:
        if not name or not entity_type:
            raise ValueError("图谱实体必须包含 name 和 entity_type")
        if entity_type not in ALLOWED_ENTITY_TYPES:
            raise ValueError(f"不支持的实体类型：{entity_type}")

    def _validate_relation_values(
        self,
        subject_entity_id: str,
        predicate: str,
        object_entity_id: str,
        valid_entity_ids: set[str] | None = None,
    ) -> None:
        if subject_entity_id == object_entity_id:
            raise ValueError("图谱关系的起点和终点不能相同")
        if predicate not in ALLOWED_PREDICATES:
            raise ValueError(f"不支持的关系类型：{predicate}")
        ids = valid_entity_ids
        if ids is None:
            ids = {
                row.id for row in self.db.query(KnowledgeEntityModel.id).all()
            }
        if subject_entity_id not in ids or object_entity_id not in ids:
            raise ValueError("图谱关系引用了不存在的实体")

    def _ensure_unique_entity_names(
        self,
        name: str,
        aliases: list[str],
        *,
        exclude_entity_id: str = "",
    ) -> None:
        requested = {
            _normalized_text(value)
            for value in [name, *aliases]
            if _normalized_text(value)
        }
        for entity in self.db.query(KnowledgeEntityModel).all():
            if entity.id == exclude_entity_id:
                continue
            existing = {
                _normalized_text(value)
                for value in [entity.name, *self.aliases(entity)]
                if _normalized_text(value)
            }
            if requested.intersection(existing):
                raise ValueError(f"节点名称或别名与“{entity.name}”重复")

    def rag_sources_for_entity(self, entity_id: str) -> list[str]:
        rows = (
            self.db.query(KnowledgeEntitySourceModel)
            .filter(KnowledgeEntitySourceModel.entity_id == entity_id)
            .order_by(KnowledgeEntitySourceModel.source.asc())
            .all()
        )
        return [row.source for row in rows]

    def rag_sources_for_entities(self, entity_ids: list[str]) -> dict[str, list[str]]:
        if not entity_ids:
            return {}
        rows = (
            self.db.query(KnowledgeEntitySourceModel)
            .filter(KnowledgeEntitySourceModel.entity_id.in_(entity_ids))
            .order_by(
                KnowledgeEntitySourceModel.entity_id.asc(),
                KnowledgeEntitySourceModel.source.asc(),
            )
            .all()
        )
        result: dict[str, list[str]] = {entity_id: [] for entity_id in entity_ids}
        for row in rows:
            result.setdefault(row.entity_id, []).append(row.source)
        return result

    def replace_rag_sources(
        self,
        entity_id: str,
        sources: list[str],
        *,
        timestamp: str | None = None,
    ) -> list[str]:
        if not self.db.get(KnowledgeEntityModel, entity_id):
            raise LookupError("图谱节点不存在")
        normalized_sources = _source_list(sources)
        if normalized_sources:
            existing_sources = {
                row.source
                for row in self.db.query(CurriculumSourceModel)
                .filter(CurriculumSourceModel.source.in_(normalized_sources))
                .all()
            }
            missing_sources = sorted(set(normalized_sources) - existing_sources)
            if missing_sources:
                raise ValueError(f"知识库不存在：{', '.join(missing_sources)}")
        self.db.query(KnowledgeEntitySourceModel).filter(
            KnowledgeEntitySourceModel.entity_id == entity_id
        ).delete(synchronize_session=False)
        created_at = timestamp or _now_iso()
        for source in normalized_sources:
            self.db.add(
                KnowledgeEntitySourceModel(
                    entity_id=entity_id,
                    source=source,
                    created_at=created_at,
                )
            )
        self.db.flush()
        return normalized_sources

    def rebuild_mentions_for_source(
        self,
        source: str,
        *,
        chunks: list[CurriculumChunkModel] | None = None,
    ) -> int:
        normalized_source = source.strip()
        self.db.query(KnowledgeEntityMentionModel).filter(
            KnowledgeEntityMentionModel.source == normalized_source
        ).delete(synchronize_session=False)
        source_chunks = chunks
        if source_chunks is None:
            source_chunks = (
                self.db.query(CurriculumChunkModel)
                .filter(CurriculumChunkModel.source == normalized_source)
                .order_by(CurriculumChunkModel.source_index.asc())
                .all()
            )
        entities = self.db.query(KnowledgeEntityModel).all()
        created = 0
        for chunk in source_chunks:
            normalized_content = _normalized_text(chunk.content)
            for entity in entities:
                variants = [entity.name, *self.aliases(entity)]
                if any(
                    _normalized_text(variant)
                    and _normalized_text(variant) in normalized_content
                    for variant in variants
                ):
                    self.db.add(
                        KnowledgeEntityMentionModel(
                            entity_id=entity.id,
                            chunk_id=chunk.id,
                            source=normalized_source,
                        )
                    )
                    created += 1
        self.db.flush()
        return created

    def rebuild_mentions_for_entity(self, entity_id: str) -> int:
        entity = self.db.get(KnowledgeEntityModel, entity_id)
        if entity is None:
            raise LookupError("图谱节点不存在")
        self.db.query(KnowledgeEntityMentionModel).filter(
            KnowledgeEntityMentionModel.entity_id == entity_id
        ).delete(synchronize_session=False)
        variants = [
            _normalized_text(value)
            for value in [entity.name, *self.aliases(entity)]
            if _normalized_text(value)
        ]
        created = 0
        for chunk in self.db.query(CurriculumChunkModel).all():
            content = _normalized_text(chunk.content)
            if any(variant in content for variant in variants):
                self.db.add(
                    KnowledgeEntityMentionModel(
                        entity_id=entity_id,
                        chunk_id=chunk.id,
                        source=chunk.source,
                    )
                )
                created += 1
        self.db.flush()
        return created

    def rebuild_all_mentions(self) -> int:
        self.db.query(KnowledgeEntityMentionModel).delete(synchronize_session=False)
        chunks = self.db.query(CurriculumChunkModel).all()
        entities = self.db.query(KnowledgeEntityModel).all()
        created = 0
        for chunk in chunks:
            content = _normalized_text(chunk.content)
            for entity in entities:
                variants = [
                    _normalized_text(value)
                    for value in [entity.name, *self.aliases(entity)]
                    if _normalized_text(value)
                ]
                if any(variant in content for variant in variants):
                    self.db.add(
                        KnowledgeEntityMentionModel(
                            entity_id=entity.id,
                            chunk_id=chunk.id,
                            source=chunk.source,
                        )
                    )
                    created += 1
        self.db.flush()
        return created

    def replace_relation_evidence(
        self,
        relation_id: str,
        chunk_ids: list[int],
        *,
        timestamp: str | None = None,
    ) -> list[dict]:
        if not self.db.get(KnowledgeRelationModel, relation_id):
            raise LookupError("图谱关系不存在")
        normalized_ids = list(dict.fromkeys(int(value) for value in chunk_ids))
        chunks = (
            self.db.query(CurriculumChunkModel)
            .filter(CurriculumChunkModel.id.in_(normalized_ids))
            .all()
            if normalized_ids
            else []
        )
        chunk_by_id = {int(chunk.id): chunk for chunk in chunks}
        missing_ids = sorted(set(normalized_ids) - set(chunk_by_id))
        if missing_ids:
            raise ValueError(
                "知识片段不存在：" + ", ".join(str(value) for value in missing_ids)
            )
        self.db.query(KnowledgeRelationEvidenceModel).filter(
            KnowledgeRelationEvidenceModel.relation_id == relation_id
        ).delete(synchronize_session=False)
        created_at = timestamp or _now_iso()
        for chunk_id in normalized_ids:
            chunk = chunk_by_id[chunk_id]
            self.db.add(
                KnowledgeRelationEvidenceModel(
                    relation_id=relation_id,
                    chunk_id=chunk_id,
                    source=chunk.source,
                    evidence_text=chunk.content,
                    created_at=created_at,
                )
            )
        relation = self.db.get(KnowledgeRelationModel, relation_id)
        if relation is not None:
            relation.evidence_source = "、".join(
                dict.fromkeys(chunk_by_id[value].source for value in normalized_ids)
            )
            relation.updated_at = created_at
        self.db.flush()
        return self.relation_evidence(relation_id)

    def relation_evidence(self, relation_id: str) -> list[dict]:
        rows = (
            self.db.query(KnowledgeRelationEvidenceModel)
            .filter(KnowledgeRelationEvidenceModel.relation_id == relation_id)
            .order_by(
                KnowledgeRelationEvidenceModel.source.asc(),
                KnowledgeRelationEvidenceModel.chunk_id.asc(),
            )
            .all()
        )
        result = []
        for row in rows:
            chunk = self.db.get(CurriculumChunkModel, row.chunk_id)
            if chunk is None:
                continue
            result.append(
                {
                    "chunk_id": int(chunk.id),
                    "source": chunk.source,
                    "source_index": chunk.source_index,
                    "content": row.evidence_text or chunk.content,
                }
            )
        return result

    def evidence_chunks(
        self,
        *,
        source: str = "",
        query: str = "",
        relation_id: str = "",
        limit: int = 50,
    ) -> list[dict]:
        chunk_query = self.db.query(CurriculumChunkModel)
        if source:
            chunk_query = chunk_query.filter(CurriculumChunkModel.source == source)
        candidate_ids: set[int] | None = None
        if relation_id:
            relation = self.db.get(KnowledgeRelationModel, relation_id)
            if relation is None:
                raise LookupError("图谱关系不存在")
            subject_ids = {
                row.chunk_id
                for row in self.db.query(KnowledgeEntityMentionModel)
                .filter(
                    KnowledgeEntityMentionModel.entity_id
                    == relation.subject_entity_id
                )
                .all()
            }
            object_ids = {
                row.chunk_id
                for row in self.db.query(KnowledgeEntityMentionModel)
                .filter(
                    KnowledgeEntityMentionModel.entity_id
                    == relation.object_entity_id
                )
                .all()
            }
            candidate_ids = subject_ids.intersection(object_ids)
            if candidate_ids:
                chunk_query = chunk_query.filter(
                    CurriculumChunkModel.id.in_(candidate_ids)
                )
            else:
                return []
        chunks = chunk_query.order_by(
            CurriculumChunkModel.source.asc(),
            CurriculumChunkModel.source_index.asc(),
        ).all()
        normalized_query = _normalized_text(query)
        result = []
        for chunk in chunks:
            if normalized_query and normalized_query not in _normalized_text(chunk.content):
                continue
            result.append(
                {
                    "chunk_id": int(chunk.id),
                    "source": chunk.source,
                    "source_index": chunk.source_index,
                    "content": chunk.content,
                }
            )
            if len(result) >= max(1, min(limit, 100)):
                break
        return result

    def linked_chunk_ids(
        self,
        *,
        entity_ids: list[str],
        relation_ids: list[str],
        allowed_sources: list[str] | None = None,
    ) -> dict:
        source_filter = set(allowed_sources) if allowed_sources is not None else None
        relation_rows = (
            self.db.query(KnowledgeRelationEvidenceModel)
            .filter(KnowledgeRelationEvidenceModel.relation_id.in_(relation_ids))
            .all()
            if relation_ids
            else []
        )
        relation_chunk_ids = [
            int(row.chunk_id)
            for row in relation_rows
            if source_filter is None or row.source in source_filter
        ]
        mention_rows = (
            self.db.query(KnowledgeEntityMentionModel)
            .filter(KnowledgeEntityMentionModel.entity_id.in_(entity_ids))
            .all()
            if entity_ids
            else []
        )
        mention_chunk_ids = [
            int(row.chunk_id)
            for row in mention_rows
            if source_filter is None or row.source in source_filter
        ]
        return {
            "relation_evidence_chunk_ids": list(dict.fromkeys(relation_chunk_ids)),
            "entity_mention_chunk_ids": list(dict.fromkeys(mention_chunk_ids)),
            "linked_chunk_ids": list(
                dict.fromkeys([*relation_chunk_ids, *mention_chunk_ids])
            ),
        }

    def find_candidate_graph(
        self,
        *,
        message: str,
        expert_id: str = "",
        topic: str = "",
        stage: dict | None = None,
    ) -> dict:
        message_text = (message or "").strip()
        if not message_text:
            return _empty_graph_payload()

        query_text = "\n".join(
            item
            for item in [
                topic,
                str((stage or {}).get("name") or ""),
                str((stage or {}).get("display_direction") or ""),
                message_text,
            ]
            if item
        )
        anchors = self.match_entities(query_text)
        if not anchors:
            return _empty_graph_payload()

        relation_map: dict[str, KnowledgeRelationModel] = {}
        for entity in anchors:
            for relation in self._relations_for_entity(entity.id):
                relation_map[relation.id] = relation
                next_id = self._other_entity_id(relation, entity.id)
                for second in self._relations_for_entity(next_id):
                    relation_map[second.id] = second

        entity_ids = {entity.id for entity in anchors}
        for relation in relation_map.values():
            entity_ids.add(relation.subject_entity_id)
            entity_ids.add(relation.object_entity_id)
        entities = (
            self.db.query(KnowledgeEntityModel)
            .filter(KnowledgeEntityModel.id.in_(list(entity_ids)))
            .all()
            if entity_ids
            else []
        )
        relations = list(relation_map.values())
        paths = self._build_paths(anchors, relations)
        recommended_path_ids = [path["id"] for path in paths[:5]]
        return {
            "entities": [self.serialize_entity(entity) for entity in entities],
            "relations": [self.serialize_relation(relation) for relation in relations],
            "paths": paths,
            "recommended_path_ids": recommended_path_ids,
        }

    def all_graph(self) -> dict:
        entities = (
            self.db.query(KnowledgeEntityModel)
            .order_by(KnowledgeEntityModel.name.asc())
            .all()
        )
        relations = (
            self.db.query(KnowledgeRelationModel)
            .order_by(KnowledgeRelationModel.id.asc())
            .all()
        )
        return {
            "entities": [self.serialize_entity(entity) for entity in entities],
            "relations": [self.serialize_relation(relation) for relation in relations],
            "paths": [],
            "recommended_path_ids": [],
        }

    def expand_neighbors(
        self,
        entity_id: str,
        *,
        hops: int = 1,
        predicates: list[str] | None = None,
        node_limit: int = 20,
        relation_limit: int = 40,
    ) -> dict:
        anchor = self.db.get(KnowledgeEntityModel, entity_id)
        if anchor is None:
            return {
                "entities": [],
                "relations": [],
                "paths": [],
                "recommended_path_ids": [],
            }
        max_hops = min(max(hops, 1), 2)
        seen_entities = {entity_id}
        frontier = {entity_id}
        relation_map: dict[str, KnowledgeRelationModel] = {}
        for _ in range(max_hops):
            next_frontier: set[str] = set()
            for current_id in sorted(frontier):
                for relation in self._relations_for_entity(current_id, predicates):
                    if len(relation_map) >= relation_limit:
                        break
                    relation_map[relation.id] = relation
                    next_id = self._other_entity_id(relation, current_id)
                    if next_id not in seen_entities and len(seen_entities) < node_limit:
                        seen_entities.add(next_id)
                        next_frontier.add(next_id)
                if len(relation_map) >= relation_limit:
                    break
            frontier = next_frontier
            if not frontier or len(relation_map) >= relation_limit:
                break
        entities = (
            self.db.query(KnowledgeEntityModel)
            .filter(KnowledgeEntityModel.id.in_(list(seen_entities)))
            .all()
        )
        relations = list(relation_map.values())
        paths = self._build_paths([anchor], relations)
        return {
            "entities": [self.serialize_entity(entity) for entity in entities],
            "relations": [self.serialize_relation(relation) for relation in relations],
            "paths": paths,
            "recommended_path_ids": [path["id"] for path in paths[:5]],
        }

    def validate_selection(
        self,
        *,
        message: str,
        selected_path_ids: list[str],
        selected_relation_ids: list[str],
        selected_entity_ids: list[str],
    ) -> GraphSelectionValidation:
        if not selected_path_ids and not selected_relation_ids and not selected_entity_ids:
            return GraphSelectionValidation(False, "请先选择至少一条图谱链路。")
        relation_ids = set(selected_relation_ids)
        relation_ids.update(self._relation_ids_from_paths(selected_path_ids))
        selected_ids = set(selected_entity_ids)
        if relation_ids:
            relations = (
                self.db.query(KnowledgeRelationModel)
                .filter(
                    KnowledgeRelationModel.id.in_(list(relation_ids)),
                    KnowledgeRelationModel.status == "active",
                )
                .all()
            )
            relations = self._runtime_relations(relations)
            if len(relations) != len(relation_ids):
                return GraphSelectionValidation(False, "选择中包含不存在的图谱关系。")
            for relation in relations:
                selected_ids.add(relation.subject_entity_id)
                selected_ids.add(relation.object_entity_id)
        matched_ids = {entity.id for entity in self.match_entities(message)}
        if matched_ids and selected_ids and matched_ids.isdisjoint(selected_ids):
            return GraphSelectionValidation(
                False,
                "您选择的图谱链路与当前问题中的核心实体关联较弱，请调整链路或仅作为类比材料。",
            )
        return GraphSelectionValidation(True, "")

    def selected_graph_payload(
        self,
        *,
        selected_path_ids: list[str],
        selected_relation_ids: list[str],
        selected_entity_ids: list[str],
    ) -> dict:
        relation_ids = list(
            dict.fromkeys(
                selected_relation_ids
                + self._relation_ids_from_paths(selected_path_ids)
            )
        )
        relations = (
            self.db.query(KnowledgeRelationModel)
            .filter(
                KnowledgeRelationModel.id.in_(relation_ids),
                KnowledgeRelationModel.status == "active",
            )
            .all()
            if relation_ids
            else []
        )
        relations = self._runtime_relations(relations)
        entity_ids = set(selected_entity_ids)
        for relation in relations:
            entity_ids.add(relation.subject_entity_id)
            entity_ids.add(relation.object_entity_id)
        entities = (
            self.db.query(KnowledgeEntityModel)
            .filter(KnowledgeEntityModel.id.in_(list(entity_ids)))
            .all()
            if entity_ids
            else []
        )
        paths = self._build_paths(entities, relations)
        selected_path_set = set(selected_path_ids)
        if selected_path_set:
            paths = [
                path for path in paths if path["id"] in selected_path_set
            ] or paths
        return {
            "entities": [self.serialize_entity(entity) for entity in entities],
            "relations": [self.serialize_relation(relation) for relation in relations],
            "paths": paths,
            "selected_entity_ids": list(dict.fromkeys(selected_entity_ids)),
            "selected_relation_ids": [relation.id for relation in relations],
            "selected_path_ids": list(dict.fromkeys(selected_path_ids)),
        }

    def format_selected_graph_context(self, payload: dict) -> str:
        if not payload.get("relations"):
            return ""
        entity_by_id = {
            item["id"]: item for item in payload.get("entities", [])
        }
        lines = [
            "<knowledge_graph_reference>",
            "以下为教师确认的知识图谱链路。已关联证据的关系可作为事实依据；待补证关系只能作为观察假设，不能表述为确定事实。",
            "仅有 GloBI 证据的关系属于全球物种交互记录，不能据此声称该关系已在九龙山、门头沟或其他具体本地场景被观察到。",
            "两种昆虫连接到同一植物只说明存在共享生态关联，不代表两种昆虫之间存在直接作用或因果关系。",
        ]
        for index, relation in enumerate(payload.get("relations", []), start=1):
            subject = entity_by_id.get(relation["subject_entity_id"], {})
            obj = entity_by_id.get(relation["object_entity_id"], {})
            status = "已关联证据" if relation.get("evidence_status") == "verified" else "待补证"
            lines.append(
                f"[{index}][{status}] "
                f"{subject.get('name', relation['subject_entity_id'])} "
                f"--{relation.get('predicate_label') or relation['predicate']}--> "
                f"{obj.get('name', relation['object_entity_id'])}"
            )
            if relation.get("description"):
                lines.append(f"说明：{relation['description']}")
            for evidence in relation.get("evidence", [])[:2]:
                lines.append(
                    f"证据：{evidence['source']} / 片段 {evidence['source_index']}："
                    f"{evidence['content']}"
                )
            for evidence in relation.get("globi_evidence", [])[:2]:
                citation = evidence.get("study_source_citation") or evidence.get("study_source_id") or "GloBI"
                location = evidence.get("locality") or "未提供具体地域"
                lines.append(
                    f"GloBI 全球关系证据：{citation}；地域：{location}；"
                    f"原始关系：{evidence.get('raw_interaction_type') or relation['predicate']}"
                )
        lines.append("</knowledge_graph_reference>")
        return "\n".join(lines)

    def graph_rag_queries(self, message: str, entity_ids: list[str]) -> list[str]:
        entities = (
            self.db.query(KnowledgeEntityModel)
            .filter(KnowledgeEntityModel.id.in_(entity_ids))
            .all()
            if entity_ids
            else []
        )
        entity_terms = []
        for entity in entities:
            entity_terms.extend([entity.name, *self.aliases(entity), entity.description])
        query = " ".join(
            item.strip()
            for item in [message, *entity_terms]
            if item and item.strip()
        )
        return [query] if query else []

    def match_entities(self, text: str) -> list[KnowledgeEntityModel]:
        normalized = _normalized_text(text)
        taxon_variants: dict[str, list[str]] = {}
        for taxon in self.db.query(KnowledgeEntityTaxonModel).all():
            variants = [taxon.scientific_name, taxon.verbatim_name]
            try:
                variants.extend(json.loads(taxon.common_names_json or "[]"))
            except json.JSONDecodeError:
                pass
            taxon_variants.setdefault(taxon.entity_id, []).extend(variants)
        matches = []
        for entity in (
            self.db.query(KnowledgeEntityModel)
            .order_by(KnowledgeEntityModel.name.asc())
            .all()
        ):
            names = [
                entity.name,
                *self.aliases(entity),
                *taxon_variants.get(entity.id, []),
            ]
            if any(
                _normalized_text(name)
                and _normalized_text(name) in normalized
                for name in names
            ):
                matches.append(entity)
        return matches

    def default_entities_for_expert(
        self, expert_id: str
    ) -> list[KnowledgeEntityModel]:
        entity_types = DEFAULT_EXPERT_ENTITY_TYPES.get(expert_id or "")
        if not entity_types:
            return []
        return (
            self.db.query(KnowledgeEntityModel)
            .filter(KnowledgeEntityModel.entity_type.in_(entity_types))
            .order_by(KnowledgeEntityModel.name.asc())
            .limit(3)
            .all()
        )

    def aliases(self, entity: KnowledgeEntityModel) -> list[str]:
        try:
            return _json_list(json.loads(entity.aliases_json or "[]"))
        except json.JSONDecodeError:
            return []

    def _relations_for_entity(
        self,
        entity_id: str,
        predicates: list[str] | None = None,
    ) -> list[KnowledgeRelationModel]:
        query = self.db.query(KnowledgeRelationModel).filter(
            KnowledgeRelationModel.status == "active",
            or_(
                KnowledgeRelationModel.subject_entity_id == entity_id,
                KnowledgeRelationModel.object_entity_id == entity_id,
            )
        )
        if predicates:
            query = query.filter(KnowledgeRelationModel.predicate.in_(predicates))
        rows = self._runtime_relations(query.all())
        evidence_counts = self._evidence_count_map([row.id for row in rows])
        local_counts = self._local_evidence_count_map([row.id for row in rows])
        return sorted(
            rows,
            key=lambda row: (
                -int(local_counts.get(row.id, 0) > 0),
                -int(evidence_counts.get(row.id, 0) > 0),
                -CONFIDENCE_WEIGHT.get(row.confidence, 0),
                row.predicate,
                row.id,
            ),
        )

    def _runtime_relations(
        self,
        rows: list[KnowledgeRelationModel],
    ) -> list[KnowledgeRelationModel]:
        """Automatic facts are queryable only while traceable evidence exists."""
        automatic_ids = [
            row.id
            for row in rows
            if (row.origin or "manual") in {"lightrag", "globi"}
            and row.management_mode == "auto"
        ]
        evidence_counts = self._evidence_count_map(automatic_ids)
        return [
            row
            for row in rows
            if row.id not in automatic_ids
            or evidence_counts.get(row.id, 0) > 0
        ]

    def _relation_ids_from_paths(self, path_ids: list[str]) -> list[str]:
        relation_ids: list[str] = []
        for path_id in path_ids:
            if not path_id.startswith("path_"):
                continue
            relation_part = path_id[5:]
            relation_ids.extend(
                item for item in relation_part.split("__") if item
            )
        return list(dict.fromkeys(relation_ids))

    def _build_paths(
        self,
        anchors: list[KnowledgeEntityModel | None],
        relations: list[KnowledgeRelationModel],
    ) -> list[dict]:
        relation_by_id = {relation.id: relation for relation in relations}
        adjacency: dict[str, list[KnowledgeRelationModel]] = {}
        for relation in relations:
            adjacency.setdefault(relation.subject_entity_id, []).append(relation)
            adjacency.setdefault(relation.object_entity_id, []).append(relation)
        entity_ids = set(adjacency)
        entity_by_id = {
            row.id: row
            for row in (
                self.db.query(KnowledgeEntityModel)
                .filter(KnowledgeEntityModel.id.in_(list(entity_ids)))
                .all()
                if entity_ids
                else []
            )
        }
        evidence_counts = self._evidence_count_map(list(relation_by_id))
        local_evidence_counts = self._local_evidence_count_map(list(relation_by_id))
        globi_evidence_counts = self._globi_evidence_count_map(list(relation_by_id))
        starts = [entity.id for entity in anchors if entity is not None]
        if not starts:
            starts = sorted(entity_ids)

        path_by_key: dict[tuple[str, ...], dict] = {}

        def register(
            path_relations: list[KnowledgeRelationModel],
            ordered_entity_ids: list[str],
        ) -> None:
            relation_ids = [relation.id for relation in path_relations]
            key = tuple(sorted(relation_ids))
            evidence_values = [
                evidence_counts.get(relation.id, 0) for relation in path_relations
            ]
            if evidence_values and all(value > 0 for value in evidence_values):
                evidence_status = "verified"
            elif any(value > 0 for value in evidence_values):
                evidence_status = "partial"
            else:
                evidence_status = "unverified"
            entity_types = [
                entity_by_id[entity_id].entity_type
                for entity_id in ordered_entity_ids
                if entity_id in entity_by_id
            ]
            is_insect_plant_bridge = (
                len(entity_types) == 3
                and entity_types[0] == "insect"
                and entity_types[1] == "plant"
                and entity_types[2] == "insect"
            )
            score = sum(
                CONFIDENCE_WEIGHT.get(relation.confidence, 1)
                + (3 if local_evidence_counts.get(relation.id, 0) else 0)
                + (
                    1
                    if not local_evidence_counts.get(relation.id, 0)
                    and globi_evidence_counts.get(relation.id, 0)
                    else 0
                )
                for relation in path_relations
            )
            if is_insect_plant_bridge:
                score += 3
                reason = "发现两种昆虫通过同一植物形成两跳生态关联"
            elif evidence_status == "verified":
                if all(local_evidence_counts.get(relation.id, 0) for relation in path_relations):
                    reason = "关系具有可回查的本地知识片段证据"
                elif all(globi_evidence_counts.get(relation.id, 0) for relation in path_relations):
                    reason = "关系具有可追溯的 GloBI 全球数据库证据"
                else:
                    reason = "关系具有本地资料或 GloBI 可追溯证据"
            elif len(path_relations) == 2:
                reason = "发现与问题实体相连的两跳关系"
            else:
                reason = "发现与问题实体直接相连的关系"
            candidate = {
                "id": "path_" + "__".join(relation_ids),
                "entity_ids": ordered_entity_ids,
                "relation_ids": relation_ids,
                "score": score,
                "evidence_status": evidence_status,
                "reason": reason,
            }
            existing = path_by_key.get(key)
            if existing is None or candidate["score"] > existing["score"]:
                path_by_key[key] = candidate

        for start_id in starts:
            for first in adjacency.get(start_id, []):
                middle_id = self._other_entity_id(first, start_id)
                register([first], [start_id, middle_id])
                for second in adjacency.get(middle_id, []):
                    if second.id == first.id:
                        continue
                    end_id = self._other_entity_id(second, middle_id)
                    if end_id == start_id:
                        continue
                    register(
                        [first, second],
                        [start_id, middle_id, end_id],
                    )

        paths = list(path_by_key.values())
        paths.sort(
            key=lambda item: (
                -item["score"],
                0 if item["evidence_status"] == "verified" else 1,
                -len(item["relation_ids"]),
                item["id"],
            )
        )
        return paths[:10]

    @staticmethod
    def _other_entity_id(
        relation: KnowledgeRelationModel,
        entity_id: str,
    ) -> str:
        if relation.subject_entity_id == entity_id:
            return relation.object_entity_id
        return relation.subject_entity_id

    def _evidence_count_map(self, relation_ids: list[str]) -> dict[str, int]:
        local = self._local_evidence_count_map(relation_ids)
        globi = self._globi_evidence_count_map(relation_ids)
        return {
            relation_id: local.get(relation_id, 0) + globi.get(relation_id, 0)
            for relation_id in relation_ids
        }

    def _local_evidence_count_map(self, relation_ids: list[str]) -> dict[str, int]:
        result = {relation_id: 0 for relation_id in relation_ids}
        if not relation_ids:
            return result
        rows = (
            self.db.query(KnowledgeRelationEvidenceModel)
            .filter(KnowledgeRelationEvidenceModel.relation_id.in_(relation_ids))
            .all()
        )
        for row in rows:
            result[row.relation_id] = result.get(row.relation_id, 0) + 1
        return result

    def _globi_evidence_count_map(self, relation_ids: list[str]) -> dict[str, int]:
        result = {relation_id: 0 for relation_id in relation_ids}
        if not relation_ids:
            return result
        globi_rows = (
            self.db.query(KnowledgeRelationGlobiEvidenceModel)
            .filter(KnowledgeRelationGlobiEvidenceModel.relation_id.in_(relation_ids))
            .all()
        )
        for row in globi_rows:
            result[row.relation_id] = result.get(row.relation_id, 0) + 1
        return result

    def _relation_score(self, relation: KnowledgeRelationModel) -> int:
        if self._local_evidence_count_map([relation.id]).get(relation.id):
            evidence_bonus = 3
        elif self._globi_evidence_count_map([relation.id]).get(relation.id):
            evidence_bonus = 1
        else:
            evidence_bonus = 0
        return CONFIDENCE_WEIGHT.get(relation.confidence, 1) + evidence_bonus

    def serialize_entity(self, entity: KnowledgeEntityModel) -> dict:
        mention_count = (
            self.db.query(KnowledgeEntityMentionModel)
            .filter(KnowledgeEntityMentionModel.entity_id == entity.id)
            .count()
        )
        taxa = (
            self.db.query(KnowledgeEntityTaxonModel)
            .filter(KnowledgeEntityTaxonModel.entity_id == entity.id)
            .order_by(
                KnowledgeEntityTaxonModel.authority.asc(),
                KnowledgeEntityTaxonModel.external_id.asc(),
            )
            .all()
        )
        return {
            "id": entity.id,
            "name": entity.name,
            "entity_type": entity.entity_type,
            "aliases": self.aliases(entity),
            "description": entity.description,
            "source": entity.source,
            "origin": entity.origin or "manual",
            "management_mode": entity.management_mode or "manual",
            "extractor_model": entity.extractor_model or "",
            "extractor_version": entity.extractor_version or "",
            "last_auto_sync_at": entity.last_auto_sync_at or "",
            "rag_sources": self.rag_sources_for_entity(entity.id),
            "mention_count": mention_count,
            "taxa": [
                {
                    "authority": row.authority,
                    "external_id": row.external_id,
                    "scientific_name": row.scientific_name,
                    "taxon_rank": row.taxon_rank,
                    "common_names": _json_list(json.loads(row.common_names_json or "[]")),
                    "match_method": row.match_method,
                    "match_confidence": row.match_confidence,
                }
                for row in taxa
            ],
        }

    def serialize_relation(self, relation: KnowledgeRelationModel) -> dict:
        evidence = self.relation_evidence(relation.id)
        globi_evidence = self.globi_evidence(relation.id)
        evidence_types = []
        if evidence:
            evidence_types.append("local_document")
        if globi_evidence:
            evidence_types.append("globi")
        if not evidence_types and relation.origin == "manual":
            evidence_types.append("manual")
        if evidence and globi_evidence:
            geographic_scope = "mixed"
        elif globi_evidence:
            geographic_scope = "global"
        elif evidence:
            geographic_scope = "local"
        else:
            geographic_scope = "unknown"
        return {
            "id": relation.id,
            "subject_entity_id": relation.subject_entity_id,
            "predicate": relation.predicate,
            "predicate_label": PREDICATE_LABELS.get(
                relation.predicate, relation.predicate
            ),
            "object_entity_id": relation.object_entity_id,
            "description": relation.description,
            "evidence_source": relation.evidence_source,
            "confidence": relation.confidence,
            "origin": relation.origin or "manual",
            "management_mode": relation.management_mode or "manual",
            "status": relation.status or "active",
            "extractor_model": relation.extractor_model or "",
            "extractor_version": relation.extractor_version or "",
            "last_auto_sync_at": relation.last_auto_sync_at or "",
            "evidence_status": "verified" if evidence or globi_evidence else "unverified",
            "evidence": evidence,
            "evidence_types": evidence_types,
            "geographic_scope": geographic_scope,
            "global_only": bool(globi_evidence and not evidence),
            "globi_evidence_count": len(globi_evidence),
            "globi_evidence": globi_evidence,
        }

    def globi_evidence(self, relation_id: str, limit: int = 20) -> list[dict]:
        rows = (
            self.db.query(GlobiInteractionModel)
            .join(
                KnowledgeRelationGlobiEvidenceModel,
                KnowledgeRelationGlobiEvidenceModel.interaction_id == GlobiInteractionModel.id,
            )
            .filter(KnowledgeRelationGlobiEvidenceModel.relation_id == relation_id)
            .order_by(GlobiInteractionModel.created_at.asc())
            .limit(max(1, min(limit, 100)))
            .all()
        )
        return [
            {
                "id": row.id,
                "raw_interaction_type": row.raw_interaction_type,
                "study_source_id": row.study_source_id,
                "study_source_citation": row.study_source_citation,
                "study_url": row.study_url,
                "study_doi": row.study_doi,
                "study_source_archive_uri": row.study_source_archive_uri,
                "locality": row.locality,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "event_date": row.event_date,
                "region_status": row.region_status,
            }
            for row in rows
        ]
