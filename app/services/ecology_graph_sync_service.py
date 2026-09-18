from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.database import SessionLocal
from app.db.models import (
    CurriculumChunkModel,
    CurriculumSourceModel,
    EcologyGraphSourceStateModel,
    EcologyGraphSyncJobModel,
    KnowledgeEntityModel,
)
from app.services.ecology_lightrag_service import (
    LIGHTRAG_EXTRACTOR_VERSION,
    EcologyExtractionResult,
    EcologyLightRagExtractor,
    ExtractedEntity,
    ExtractedRelation,
)
from app.services.knowledge_graph_service import KnowledgeGraphService


logger = logging.getLogger(__name__)

AUTO_PREDICATES = {
    "feeds_on": ("取食", "食用", "啃食", "吸食", "采食", "为食"),
    "visits": ("访花", "访问花", "造访花", "停落在花"),
    "pollinates": ("授粉", "传粉"),
    "lives_on": ("栖息", "居住", "生活在", "寄居"),
    "lays_eggs_on": ("产卵", "卵产在"),
    "damages": ("危害", "损害", "蛀食", "侵害"),
    "predator_of": ("捕食", "捕捉", "猎食", "天敌"),
    "parasite_of": ("寄生",),
}
ENTITY_TYPE_ALIASES = {
    "insect": "insect",
    "insects": "insect",
    "昆虫": "insect",
    "plant": "plant",
    "plants": "plant",
    "植物": "plant",
    "habitat": "habitat",
    "habitats": "habitat",
    "栖息地": "habitat",
}


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


def _future_iso(seconds: int) -> str:
    return (
        dt.datetime.now(dt.timezone.utc).astimezone()
        + dt.timedelta(seconds=seconds)
    ).isoformat()


def _normalized(value: str) -> str:
    return re.sub(r"\s+", "", value or "").casefold()


@dataclass(frozen=True)
class ValidatedAutoRelation:
    subject_name: str
    subject_type: str
    predicate: str
    object_name: str
    object_type: str
    description: str
    chunk_ids: tuple[int, ...]


class EcologyGraphSyncService:
    def __init__(self, db: Session):
        self.db = db

    def enqueue_source(self, source: str, *, force: bool = False) -> dict | None:
        row = self.db.get(CurriculumSourceModel, source)
        if row is None or row.category != "ecology":
            return None
        if not force:
            state = self.db.get(EcologyGraphSourceStateModel, source)
            if state is not None and state.source_checksum == row.checksum and state.status == "ready":
                return self.serialize_state(state)
        active = (
            self.db.query(EcologyGraphSyncJobModel)
            .filter(
                EcologyGraphSyncJobModel.source == source,
                EcologyGraphSyncJobModel.source_checksum == (row.checksum or ""),
                EcologyGraphSyncJobModel.operation == "sync",
                EcologyGraphSyncJobModel.status.in_(["queued", "running"]),
            )
            .first()
        )
        if active is not None:
            return self.serialize_job(active)
        timestamp = _now_iso()
        job = EcologyGraphSyncJobModel(
            id=f"ecology_job_{uuid.uuid4().hex}",
            source=source,
            source_checksum=row.checksum or "",
            operation="sync",
            status="queued",
            attempts=0,
            stats_json="{}",
            last_error="",
            lease_until="",
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.db.add(job)
        state = self.db.get(EcologyGraphSourceStateModel, source)
        if state is None:
            state = EcologyGraphSourceStateModel(source=source, updated_at=timestamp)
            self.db.add(state)
        state.source_checksum = row.checksum or ""
        state.status = "queued"
        state.last_job_id = job.id
        state.last_error = ""
        state.updated_at = timestamp
        self.db.flush()
        return self.serialize_job(job)

    def enqueue_all(self, *, force: bool = False) -> list[dict]:
        sources = [
            row.source
            for row in self.db.query(CurriculumSourceModel)
            .filter(CurriculumSourceModel.category == "ecology")
            .order_by(CurriculumSourceModel.source.asc())
            .all()
        ]
        result = []
        for source in sources:
            item = self.enqueue_source(source, force=force)
            if item is not None:
                result.append(item)
        return result

    def enqueue_delete(self, source: str, checksum: str = "") -> dict:
        timestamp = _now_iso()
        stale_sync_jobs = (
            self.db.query(EcologyGraphSyncJobModel)
            .filter(
                EcologyGraphSyncJobModel.source == source,
                EcologyGraphSyncJobModel.operation == "sync",
                EcologyGraphSyncJobModel.status.in_(["queued", "running"]),
            )
            .all()
        )
        for stale in stale_sync_jobs:
            stale.status = "cancelled"
            stale.lease_until = ""
            stale.finished_at = timestamp
            stale.updated_at = timestamp
        active = (
            self.db.query(EcologyGraphSyncJobModel)
            .filter(
                EcologyGraphSyncJobModel.source == source,
                EcologyGraphSyncJobModel.operation == "delete",
                EcologyGraphSyncJobModel.status.in_(["queued", "running"]),
            )
            .first()
        )
        if active is not None:
            return self.serialize_job(active)
        job = EcologyGraphSyncJobModel(
            id=f"ecology_job_{uuid.uuid4().hex}",
            source=source,
            source_checksum=checksum,
            operation="delete",
            status="queued",
            attempts=0,
            stats_json="{}",
            last_error="",
            lease_until="",
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.db.add(job)
        state = self.db.get(EcologyGraphSourceStateModel, source)
        if state is not None:
            state.status = "queued"
            state.last_job_id = job.id
            state.last_error = ""
            state.updated_at = timestamp
        self.db.flush()
        return self.serialize_job(job)

    def status_payload(self, limit: int = 100) -> dict:
        jobs = (
            self.db.query(EcologyGraphSyncJobModel)
            .order_by(EcologyGraphSyncJobModel.created_at.desc())
            .limit(max(1, min(limit, 200)))
            .all()
        )
        states = (
            self.db.query(EcologyGraphSourceStateModel)
            .order_by(EcologyGraphSourceStateModel.source.asc())
            .all()
        )
        return {
            "jobs": [self.serialize_job(row) for row in jobs],
            "sources": [self.serialize_state(row) for row in states],
        }

    @staticmethod
    def serialize_job(row: EcologyGraphSyncJobModel) -> dict:
        try:
            stats = json.loads(row.stats_json or "{}")
        except json.JSONDecodeError:
            stats = {}
        return {
            "id": row.id,
            "source": row.source,
            "source_checksum": row.source_checksum,
            "operation": row.operation,
            "status": row.status,
            "attempts": row.attempts,
            "stats": stats,
            "last_error": row.last_error,
            "created_at": row.created_at,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
            "updated_at": row.updated_at,
        }

    @staticmethod
    def serialize_state(row: EcologyGraphSourceStateModel) -> dict:
        return {
            "source": row.source,
            "source_checksum": row.source_checksum,
            "lightrag_doc_id": row.lightrag_doc_id,
            "status": row.status,
            "last_job_id": row.last_job_id,
            "entity_count": row.entity_count,
            "relation_count": row.relation_count,
            "rejected_count": row.rejected_count,
            "last_error": row.last_error,
            "last_synced_at": row.last_synced_at,
            "updated_at": row.updated_at,
        }


class EcologyGraphJobProcessor:
    def __init__(
        self,
        settings: Settings | None = None,
        extractor: EcologyLightRagExtractor | None = None,
    ):
        self.settings = settings or get_settings()
        self.extractor = extractor or EcologyLightRagExtractor(self.settings)

    async def process_next(self) -> bool:
        job_id = self._claim_next_job()
        if not job_id:
            return False
        await self.process_job(job_id)
        return True

    def _claim_next_job(self) -> str:
        db = SessionLocal()
        try:
            now = _now_iso()
            query = db.query(EcologyGraphSyncJobModel).filter(
                or_(
                    EcologyGraphSyncJobModel.status == "queued",
                    (
                        (EcologyGraphSyncJobModel.status == "running")
                        & (EcologyGraphSyncJobModel.lease_until < now)
                    ),
                )
            )
            candidate = query.order_by(EcologyGraphSyncJobModel.created_at.asc()).first()
            if candidate is None:
                return ""
            job_id = candidate.id
            claimed = (
                db.query(EcologyGraphSyncJobModel)
                .filter(
                    EcologyGraphSyncJobModel.id == job_id,
                    or_(
                        EcologyGraphSyncJobModel.status == "queued",
                        (
                            (EcologyGraphSyncJobModel.status == "running")
                            & (EcologyGraphSyncJobModel.lease_until < now)
                        ),
                    ),
                )
                .update(
                    {
                        EcologyGraphSyncJobModel.status: "running",
                        EcologyGraphSyncJobModel.attempts: EcologyGraphSyncJobModel.attempts + 1,
                        EcologyGraphSyncJobModel.started_at: candidate.started_at or now,
                        EcologyGraphSyncJobModel.lease_until: _future_iso(900),
                        EcologyGraphSyncJobModel.updated_at: now,
                    },
                    synchronize_session=False,
                )
            )
            if claimed != 1:
                db.rollback()
                return ""
            state = db.get(EcologyGraphSourceStateModel, candidate.source)
            if state is not None:
                state.status = "running"
                state.last_job_id = job_id
                state.updated_at = now
            db.commit()
            return job_id
        finally:
            db.close()

    async def process_job(self, job_id: str) -> None:
        db = SessionLocal()
        try:
            job = db.get(EcologyGraphSyncJobModel, job_id)
            if job is None:
                return
            operation = job.operation
            source = job.source
            checksum = job.source_checksum
            if operation == "delete":
                graph = KnowledgeGraphService(db)
                removed = graph.prune_unverified_auto_relations()
                removed_entities = graph.prune_orphan_auto_entities()
                cleanup = getattr(self.extractor, "delete_source_artifacts", None)
                if callable(cleanup):
                    cleanup(source)
                state = db.get(EcologyGraphSourceStateModel, source)
                if state is not None:
                    db.delete(state)
                self._complete_job(
                    db,
                    job,
                    {
                        "removed_relations": removed,
                        "removed_entities": removed_entities,
                    },
                )
                db.commit()
                return
            source_row = db.get(CurriculumSourceModel, source)
            if source_row is None or source_row.category != "ecology":
                job.status = "cancelled"
                job.last_error = "生态知识来源不存在或分类已变化"
                job.lease_until = ""
                job.finished_at = _now_iso()
                job.updated_at = job.finished_at
                db.commit()
                return
            if checksum and checksum != (source_row.checksum or ""):
                job.status = "cancelled"
                job.lease_until = ""
                job.finished_at = _now_iso()
                job.updated_at = job.finished_at
                db.commit()
                EcologyGraphSyncService(db).enqueue_source(source, force=True)
                db.commit()
                return
            chunks = (
                db.query(CurriculumChunkModel)
                .filter(CurriculumChunkModel.source == source)
                .order_by(CurriculumChunkModel.source_index.asc())
                .all()
            )
            chunk_payload = [(int(row.id), row.content) for row in chunks]
            checksum = source_row.checksum or checksum
        except Exception as exc:
            self._fail_job(db, job_id, exc)
            db.commit()
            return
        finally:
            db.close()

        try:
            result = await self.extractor.extract(
                source=source,
                checksum=checksum,
                chunks=[content for _, content in chunk_payload],
            )
            db = SessionLocal()
            try:
                job = db.get(EcologyGraphSyncJobModel, job_id)
                if job is None:
                    return
                source_row = db.get(CurriculumSourceModel, source)
                if (
                    job.status == "cancelled"
                    or source_row is None
                    or source_row.category != "ecology"
                    or (checksum and checksum != (source_row.checksum or ""))
                ):
                    job.status = "cancelled"
                    job.lease_until = ""
                    job.finished_at = _now_iso()
                    job.updated_at = job.finished_at
                    db.commit()
                    if source_row is not None and source_row.category == "ecology":
                        EcologyGraphSyncService(db).enqueue_source(source, force=True)
                        db.commit()
                    return
                stats = self._apply_extraction(
                    db,
                    source=source,
                    checksum=checksum,
                    chunk_payload=chunk_payload,
                    result=result,
                )
                self._complete_job(db, job, stats)
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            db = SessionLocal()
            try:
                self._fail_job(db, job_id, exc)
                db.commit()
            finally:
                db.close()

    def _apply_extraction(
        self,
        db: Session,
        *,
        source: str,
        checksum: str,
        chunk_payload: list[tuple[int, str]],
        result: EcologyExtractionResult,
    ) -> dict:
        graph = KnowledgeGraphService(db)
        validated, rejected = self.validate_relations(
            db,
            result,
            chunk_payload,
        )
        graph.clear_auto_evidence_for_source(source)
        graph.clear_auto_entity_sources_for_source(source)
        entity_ids: set[str] = set()
        relation_ids: set[str] = set()
        created_relations = 0
        for item in validated:
            subject = graph.resolve_or_create_auto_entity(
                name=item.subject_name,
                entity_type=item.subject_type,
                source=source,
                extractor_model=self.settings.ecology_graph_extract_model,
                extractor_version=LIGHTRAG_EXTRACTOR_VERSION,
            )
            object_entity = graph.resolve_or_create_auto_entity(
                name=item.object_name,
                entity_type=item.object_type,
                source=source,
                extractor_model=self.settings.ecology_graph_extract_model,
                extractor_version=LIGHTRAG_EXTRACTOR_VERSION,
            )
            relation, created = graph.upsert_auto_relation(
                subject_entity_id=subject.id,
                predicate=item.predicate,
                object_entity_id=object_entity.id,
                description=item.description,
                evidence_chunk_ids=list(item.chunk_ids),
                extractor_model=self.settings.ecology_graph_extract_model,
                extractor_version=LIGHTRAG_EXTRACTOR_VERSION,
            )
            entity_ids.update([subject.id, object_entity.id])
            relation_ids.add(relation.id)
            created_relations += int(created)
        removed_relations = graph.prune_unverified_auto_relations()
        removed_entities = graph.prune_orphan_auto_entities()
        timestamp = _now_iso()
        state = db.get(EcologyGraphSourceStateModel, source)
        if state is None:
            state = EcologyGraphSourceStateModel(source=source, updated_at=timestamp)
            db.add(state)
        state.source_checksum = checksum
        state.lightrag_doc_id = result.document_id
        state.status = "ready"
        state.entity_count = len(entity_ids)
        state.relation_count = len(relation_ids)
        state.rejected_count = rejected
        state.last_error = ""
        state.last_synced_at = timestamp
        state.updated_at = timestamp
        db.flush()
        return {
            "entities": len(entity_ids),
            "relations": len(relation_ids),
            "created_relations": created_relations,
            "rejected": rejected,
            "removed_relations": removed_relations,
            "removed_entities": removed_entities,
        }

    def validate_relations(
        self,
        db: Session,
        result: EcologyExtractionResult,
        chunks: list[tuple[int, str]],
    ) -> tuple[list[ValidatedAutoRelation], int]:
        validated: dict[tuple[str, str, str], ValidatedAutoRelation] = {}
        rejected = 0
        for edge in result.relations:
            subject_entity = result.entities.get(edge.subject) or ExtractedEntity(edge.subject, "")
            object_entity = result.entities.get(edge.object) or ExtractedEntity(edge.object, "")
            subject_type = self._entity_type(db, subject_entity)
            object_type = self._entity_type(db, object_entity)
            if not {subject_type, object_type}.issubset({"insect", "plant", "habitat"}):
                rejected += 1
                continue
            item = self._validate_edge(
                edge,
                subject_entity.name,
                subject_type,
                self._entity_variants(db, subject_entity.name),
                object_entity.name,
                object_type,
                self._entity_variants(db, object_entity.name),
                chunks,
            )
            if item is None:
                rejected += 1
                continue
            key = (
                _normalized(item.subject_name),
                item.predicate,
                _normalized(item.object_name),
            )
            existing = validated.get(key)
            if existing is None:
                validated[key] = item
            else:
                validated[key] = ValidatedAutoRelation(
                    **{
                        **existing.__dict__,
                        "chunk_ids": tuple(dict.fromkeys([*existing.chunk_ids, *item.chunk_ids])),
                    }
                )
        return list(validated.values()), rejected

    def _entity_type(self, db: Session, entity: ExtractedEntity) -> str:
        normalized = _normalized(entity.name)
        graph = KnowledgeGraphService(db)
        for row in db.query(KnowledgeEntityModel).all():
            variants = [row.name, *graph.aliases(row)]
            if normalized in {_normalized(value) for value in variants}:
                return row.entity_type
        return ENTITY_TYPE_ALIASES.get(entity.entity_type.strip().casefold(), "")

    def _entity_variants(self, db: Session, name: str) -> tuple[str, ...]:
        normalized = _normalized(name)
        graph = KnowledgeGraphService(db)
        for row in db.query(KnowledgeEntityModel).all():
            variants = [row.name, *graph.aliases(row)]
            if normalized in {_normalized(value) for value in variants}:
                return tuple(dict.fromkeys([name, *variants]))
        return (name,)

    def _validate_edge(
        self,
        edge: ExtractedRelation,
        subject_name: str,
        subject_type: str,
        subject_variants: tuple[str, ...],
        object_name: str,
        object_type: str,
        object_variants: tuple[str, ...],
        chunks: list[tuple[int, str]],
    ) -> ValidatedAutoRelation | None:
        if subject_type == "insect" and object_type in {"plant", "habitat"}:
            left = (subject_name, subject_type)
            right = (object_name, object_type)
            left_variants, right_variants = subject_variants, object_variants
            allowed = {"feeds_on", "visits", "pollinates", "lives_on", "lays_eggs_on", "damages"}
        elif object_type == "insect" and subject_type in {"plant", "habitat"}:
            left = (object_name, object_type)
            right = (subject_name, subject_type)
            left_variants, right_variants = object_variants, subject_variants
            allowed = {"feeds_on", "visits", "pollinates", "lives_on", "lays_eggs_on", "damages"}
        elif subject_type == object_type == "insect":
            left = (subject_name, subject_type)
            right = (object_name, object_type)
            left_variants, right_variants = subject_variants, object_variants
            allowed = {"predator_of", "parasite_of"}
        else:
            return None

        evidence_by_predicate: dict[tuple[str, bool], list[int]] = {}
        normalized_left_variants = tuple(_normalized(value) for value in left_variants)
        normalized_right_variants = tuple(_normalized(value) for value in right_variants)
        for chunk_id, content in chunks:
            for segment in re.split(r"[。！？!?；;]+", content):
                normalized_segment = _normalized(segment)
                left_normalized = next(
                    (
                        value
                        for value in normalized_left_variants
                        if value in normalized_segment
                    ),
                    "",
                )
                right_normalized = next(
                    (
                        value
                        for value in normalized_right_variants
                        if value in normalized_segment
                    ),
                    "",
                )
                if not left_normalized or not right_normalized:
                    continue
                for predicate in allowed:
                    terms = AUTO_PREDICATES[predicate]
                    # 模型输出不能替代原文证据：双方实体与关系词必须共现于同一句。
                    if not any(
                        _normalized(term) in normalized_segment for term in terms
                    ):
                        continue
                    reverse = False
                    if predicate in {"predator_of", "parasite_of"}:
                        reverse = self._is_reverse_relation(
                            normalized_segment,
                            left_normalized,
                            right_normalized,
                            terms,
                        )
                    evidence_by_predicate.setdefault((predicate, reverse), []).append(
                        chunk_id
                    )
        if not evidence_by_predicate:
            return None
        predicate, reverse = max(
            evidence_by_predicate,
            key=lambda value: len(evidence_by_predicate[value]),
        )
        if reverse:
            left, right = right, left
        return ValidatedAutoRelation(
            subject_name=left[0],
            subject_type=left[1],
            predicate=predicate,
            object_name=right[0],
            object_type=right[1],
            description=edge.description or edge.keywords,
            chunk_ids=tuple(dict.fromkeys(evidence_by_predicate[(predicate, reverse)])),
        )

    @staticmethod
    def _is_reverse_relation(
        content: str,
        left: str,
        right: str,
        terms: tuple[str, ...],
    ) -> bool:
        for term in terms:
            normalized_term = _normalized(term)
            if normalized_term not in content:
                continue
            if f"{left}被{right}{normalized_term}" in content:
                return True
            if f"{right}被{left}{normalized_term}" in content:
                return False
            if normalized_term == "天敌":
                if f"{left}是{right}的天敌" in content:
                    return False
                if f"{right}是{left}的天敌" in content:
                    return True
                if f"{left}的天敌是{right}" in content:
                    return True
                if f"{right}的天敌是{left}" in content:
                    return False
            forward = content.find(left) < content.find(normalized_term) < content.rfind(right)
            reverse = content.find(right) < content.find(normalized_term) < content.rfind(left)
            if forward:
                return False
            if reverse:
                return True
        return False

    @staticmethod
    def _complete_job(db: Session, job: EcologyGraphSyncJobModel, stats: dict) -> None:
        timestamp = _now_iso()
        job.status = "completed"
        job.stats_json = json.dumps(stats, ensure_ascii=False)
        job.last_error = ""
        job.lease_until = ""
        job.finished_at = timestamp
        job.updated_at = timestamp

    def _fail_job(self, db: Session, job_id: str, exc: Exception) -> None:
        job = db.get(EcologyGraphSyncJobModel, job_id)
        if job is None:
            return
        if job.status == "cancelled":
            return
        timestamp = _now_iso()
        retry = int(job.attempts or 0) < self.settings.ecology_graph_job_max_attempts
        job.status = "queued" if retry else "failed"
        job.last_error = f"{type(exc).__name__}: {exc}"
        job.lease_until = ""
        job.finished_at = "" if retry else timestamp
        job.updated_at = timestamp
        state = db.get(EcologyGraphSourceStateModel, job.source)
        if state is not None:
            state.status = "queued" if retry else "failed"
            state.last_error = job.last_error
            state.updated_at = timestamp


class EcologyGraphWorker:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.processor = EcologyGraphJobProcessor(self.settings)
        self._stopped = asyncio.Event()

    async def run(self) -> None:
        if not self.settings.ecology_graph_auto_sync_enabled:
            return
        db = SessionLocal()
        try:
            EcologyGraphSyncService(db).enqueue_all()
            db.commit()
        finally:
            db.close()
        while not self._stopped.is_set():
            try:
                processed = await self.processor.process_next()
            except Exception:
                logger.exception("Ecology graph worker iteration failed")
                processed = False
            if not processed:
                try:
                    await asyncio.wait_for(
                        self._stopped.wait(),
                        timeout=self.settings.ecology_graph_worker_poll_seconds,
                    )
                except asyncio.TimeoutError:
                    pass

    def stop(self) -> None:
        self._stopped.set()
