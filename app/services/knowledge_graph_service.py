from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import (
    CurriculumSourceModel,
    KnowledgeEntityModel,
    KnowledgeEntitySourceModel,
    KnowledgeRelationModel,
)


SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "knowledge_graph_seed.json"
CONFIDENCE_WEIGHT = {"high": 3, "medium": 2, "low": 1}
DEFAULT_EXPERT_ENTITY_TYPES = {
    "nature_agent": ["plant", "habitat", "season"],
}
DEFAULT_EXPERT_ENTITY_IDS = {
    "insect_agent": ["insect_aphid", "insect_ladybug"],
}
PREDICATE_LABELS = {
    "feeds_on": "取食",
    "predator_of": "捕食",
    "produces": "产生",
    "attracted_by": "被吸引",
    "performs": "进行",
}
DEFAULT_CANDIDATE_ANCHOR_LIMIT = 3
DEFAULT_CANDIDATE_NODE_LIMIT = 24
DEFAULT_CANDIDATE_RELATION_LIMIT = 48


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


def _json_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _source_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))


@dataclass(frozen=True)
class GraphSelectionValidation:
    valid: bool
    warning: str = ""


class KnowledgeGraphService:
    def __init__(self, db: Session):
        self.db = db

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def load_seed_graph(self) -> dict:
        with SEED_PATH.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return self.import_graph_json(payload)

    def import_graph_json(self, payload: dict) -> dict:
        timestamp = _now_iso()
        entity_count = 0
        relation_count = 0
        entity_sources: dict[str, list[str]] = {}
        entity_sources_configured: set[str] = set()
        requested_sources = set()
        payload_entity_ids: set[str] = set()
        for item in payload.get("entities") or []:
            entity_id = str(item.get("id") or "").strip()
            name = str(item.get("name") or "").strip()
            entity_type = str(item.get("entity_type") or "").strip()
            if not entity_id or not name or not entity_type:
                raise ValueError("图谱实体必须包含 id、name 和 entity_type")
            payload_entity_ids.add(entity_id)
            if entity_id and "rag_sources" in item:
                sources = _source_list(item.get("rag_sources"))
                entity_sources[entity_id] = sources
                entity_sources_configured.add(entity_id)
                requested_sources.update(sources)
        existing_entity_ids = {
            row.id for row in self.db.query(KnowledgeEntityModel).all()
        }
        valid_entity_ids = existing_entity_ids | payload_entity_ids
        for item in payload.get("relations") or []:
            relation_id = str(item.get("id") or "").strip()
            subject_id = str(item.get("subject_entity_id") or "").strip()
            object_id = str(item.get("object_entity_id") or "").strip()
            predicate = str(item.get("predicate") or "").strip()
            if not relation_id or not subject_id or not object_id or not predicate:
                raise ValueError("图谱关系必须包含 id、subject_entity_id、predicate 和 object_entity_id")
            if subject_id not in valid_entity_ids or object_id not in valid_entity_ids:
                raise ValueError(f"图谱关系引用了不存在的实体：{relation_id}")
        if requested_sources:
            existing_sources = {
                row.source
                for row in self.db.query(CurriculumSourceModel)
                .filter(CurriculumSourceModel.source.in_(requested_sources))
                .all()
            }
            missing_sources = sorted(requested_sources - existing_sources)
            if missing_sources:
                raise ValueError(f"知识库不存在：{', '.join(missing_sources)}")
        for item in payload.get("entities") or []:
            entity_id = str(item.get("id") or "").strip()
            name = str(item.get("name") or "").strip()
            entity_type = str(item.get("entity_type") or "").strip()
            if not entity_id or not name or not entity_type:
                continue
            row = self.db.get(KnowledgeEntityModel, entity_id)
            if row is None:
                row = KnowledgeEntityModel(id=entity_id, created_at=timestamp)
                self.db.add(row)
                entity_count += 1
            row.name = name
            row.entity_type = entity_type
            row.aliases_json = json.dumps(_json_list(item.get("aliases")), ensure_ascii=False)
            row.description = str(item.get("description") or "").strip()
            row.source = str(item.get("source") or "").strip()
            row.updated_at = timestamp
            self.db.flush()
            if entity_id in entity_sources_configured:
                self.replace_rag_sources(
                    entity_id,
                    entity_sources.get(entity_id, []),
                    timestamp=timestamp,
                )
        self.db.flush()

        for item in payload.get("relations") or []:
            relation_id = str(item.get("id") or "").strip()
            subject_id = str(item.get("subject_entity_id") or "").strip()
            object_id = str(item.get("object_entity_id") or "").strip()
            predicate = str(item.get("predicate") or "").strip()
            if not relation_id or not subject_id or not object_id or not predicate:
                continue
            if not self.db.get(KnowledgeEntityModel, subject_id):
                continue
            if not self.db.get(KnowledgeEntityModel, object_id):
                continue
            row = self.db.get(KnowledgeRelationModel, relation_id)
            if row is None:
                row = KnowledgeRelationModel(id=relation_id, created_at=timestamp)
                self.db.add(row)
                relation_count += 1
            row.subject_entity_id = subject_id
            row.predicate = predicate
            row.object_entity_id = object_id
            row.description = str(item.get("description") or "").strip()
            row.evidence_source = str(item.get("evidence_source") or "").strip()
            row.confidence = str(item.get("confidence") or "medium").strip() or "medium"
            row.updated_at = timestamp
        self.db.flush()
        return {"entity_count": entity_count, "relation_count": relation_count}

    def preview_import_graph_json(self, payload: dict) -> dict:
        errors = []
        requested_sources = set()
        payload_entity_ids = set()
        new_entity_count = 0
        updated_entity_count = 0
        new_relation_count = 0
        updated_relation_count = 0
        affected_existing_relation_ids: set[str] = set()

        existing_entity_ids = {row.id for row in self.db.query(KnowledgeEntityModel).all()}
        existing_relation_ids = {row.id for row in self.db.query(KnowledgeRelationModel).all()}

        for index, item in enumerate(payload.get("entities") or [], start=1):
            entity_id = str(item.get("id") or "").strip()
            name = str(item.get("name") or "").strip()
            entity_type = str(item.get("entity_type") or "").strip()
            if not entity_id or not name or not entity_type:
                errors.append(f"第 {index} 个图谱实体必须包含 id、name 和 entity_type")
                continue
            payload_entity_ids.add(entity_id)
            if entity_id in existing_entity_ids:
                updated_entity_count += 1
                related_relations = self.db.query(KnowledgeRelationModel).filter(
                    or_(
                        KnowledgeRelationModel.subject_entity_id == entity_id,
                        KnowledgeRelationModel.object_entity_id == entity_id,
                    )
                ).all()
                affected_existing_relation_ids.update(relation.id for relation in related_relations)
            else:
                new_entity_count += 1
            requested_sources.update(_source_list(item.get("rag_sources")))

        valid_entity_ids = existing_entity_ids | payload_entity_ids
        for index, item in enumerate(payload.get("relations") or [], start=1):
            relation_id = str(item.get("id") or "").strip()
            subject_id = str(item.get("subject_entity_id") or "").strip()
            object_id = str(item.get("object_entity_id") or "").strip()
            predicate = str(item.get("predicate") or "").strip()
            if not relation_id or not subject_id or not object_id or not predicate:
                errors.append(f"第 {index} 条图谱关系必须包含 id、subject_entity_id、predicate 和 object_entity_id")
                continue
            if subject_id not in valid_entity_ids or object_id not in valid_entity_ids:
                errors.append(f"图谱关系引用了不存在的实体：{relation_id}")
                continue
            if relation_id in existing_relation_ids:
                updated_relation_count += 1
                affected_existing_relation_ids.add(relation_id)
            else:
                new_relation_count += 1

        existing_sources = {
            row.source
            for row in self.db.query(CurriculumSourceModel)
            .filter(CurriculumSourceModel.source.in_(requested_sources))
            .all()
        } if requested_sources else set()
        missing_sources = sorted(requested_sources - existing_sources)
        return {
            "new_entity_count": new_entity_count,
            "updated_entity_count": updated_entity_count,
            "new_relation_count": new_relation_count,
            "updated_relation_count": updated_relation_count,
            "missing_sources": missing_sources,
            "errors": errors,
            "affected_relation_ids": sorted(affected_existing_relation_ids),
            "can_import": not errors and not missing_sources,
        }

    def create_entity(self, payload: dict) -> dict:
        entity_id = str(payload.get("id") or self._new_id("entity")).strip()
        if not entity_id:
            raise ValueError("图谱节点 id 不能为空")
        if self.db.get(KnowledgeEntityModel, entity_id):
            raise ValueError("图谱节点已存在")
        timestamp = _now_iso()
        entity = KnowledgeEntityModel(id=entity_id, created_at=timestamp)
        self.db.add(entity)
        self._apply_entity_payload(entity, payload, timestamp)
        self.replace_rag_sources(entity_id, payload.get("rag_sources", []), timestamp=timestamp)
        return self.serialize_entity(entity)

    def update_entity(self, entity_id: str, payload: dict) -> dict:
        entity = self.db.get(KnowledgeEntityModel, entity_id)
        if not entity:
            raise LookupError("图谱节点不存在")
        timestamp = _now_iso()
        self._apply_entity_payload(entity, payload, timestamp)
        self.replace_rag_sources(entity_id, payload.get("rag_sources", []), timestamp=timestamp)
        return self.serialize_entity(entity)

    def delete_entity(self, entity_id: str) -> dict:
        entity = self.db.get(KnowledgeEntityModel, entity_id)
        if not entity:
            raise LookupError("图谱节点不存在")
        relation_count = self.db.query(KnowledgeRelationModel).filter(
            or_(
                KnowledgeRelationModel.subject_entity_id == entity_id,
                KnowledgeRelationModel.object_entity_id == entity_id,
            )
        ).delete(synchronize_session=False)
        self.db.query(KnowledgeEntitySourceModel).filter(
            KnowledgeEntitySourceModel.entity_id == entity_id
        ).delete(synchronize_session=False)
        self.db.delete(entity)
        self.db.flush()
        return {"deleted_relation_count": relation_count}

    def clear_graph(self) -> dict:
        binding_count = self.db.query(KnowledgeEntitySourceModel).delete(synchronize_session=False)
        relation_count = self.db.query(KnowledgeRelationModel).delete(synchronize_session=False)
        entity_count = self.db.query(KnowledgeEntityModel).delete(synchronize_session=False)
        self.db.flush()
        return {
            "deleted_entity_count": entity_count,
            "deleted_relation_count": relation_count,
            "deleted_binding_count": binding_count,
        }

    def create_relation(self, payload: dict) -> dict:
        relation_id = str(payload.get("id") or self._new_id("rel")).strip()
        if not relation_id:
            raise ValueError("图谱关系 id 不能为空")
        if self.db.get(KnowledgeRelationModel, relation_id):
            raise ValueError("图谱关系已存在")
        timestamp = _now_iso()
        relation = KnowledgeRelationModel(id=relation_id, created_at=timestamp)
        self.db.add(relation)
        self._apply_relation_payload(relation, payload, timestamp)
        return self.serialize_relation(relation)

    def update_relation(self, relation_id: str, payload: dict) -> dict:
        relation = self.db.get(KnowledgeRelationModel, relation_id)
        if not relation:
            raise LookupError("图谱关系不存在")
        self._apply_relation_payload(relation, payload, _now_iso())
        return self.serialize_relation(relation)

    def delete_relation(self, relation_id: str) -> None:
        relation = self.db.get(KnowledgeRelationModel, relation_id)
        if not relation:
            raise LookupError("图谱关系不存在")
        self.db.delete(relation)
        self.db.flush()

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

    def find_candidate_graph(
        self,
        *,
        message: str,
        expert_id: str = "",
        topic: str = "",
        stage: dict | None = None,
    ) -> dict:
        if not self.db.query(KnowledgeEntityModel).first():
            self.load_seed_graph()
        message_text = (message or "").strip()
        if message_text:
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
        else:
            anchors = self.default_entities_for_expert(expert_id)
            if not anchors:
                query_text = "\n".join(
                    item
                    for item in [
                        topic,
                        str((stage or {}).get("name") or ""),
                        str((stage or {}).get("display_direction") or ""),
                    ]
                    if item
                )
                anchors = self.match_entities(query_text)
        if not anchors:
            anchors = self.db.query(KnowledgeEntityModel).order_by(KnowledgeEntityModel.name.asc()).limit(DEFAULT_CANDIDATE_ANCHOR_LIMIT).all()

        all_anchor_ids = [entity.id for entity in anchors]
        anchors = anchors[:DEFAULT_CANDIDATE_ANCHOR_LIMIT]
        anchor_ids = {entity.id for entity in anchors}
        first_hop_relations = self._relations_for_entities(anchor_ids)
        first_hop_entity_ids = {
            entity_id
            for relation in first_hop_relations
            for entity_id in (relation.subject_entity_id, relation.object_entity_id)
        }
        candidate_relations = self._dedupe_relations(
            [*first_hop_relations, *self._relations_for_entities(first_hop_entity_ids)]
        )
        candidate_entity_ids = set(anchor_ids)
        for relation in candidate_relations:
            candidate_entity_ids.add(relation.subject_entity_id)
            candidate_entity_ids.add(relation.object_entity_id)

        selected_entity_ids = set(anchor_ids)
        relations: list[KnowledgeRelationModel] = []
        for relation in candidate_relations:
            if len(relations) >= DEFAULT_CANDIDATE_RELATION_LIMIT:
                break
            next_entity_ids = selected_entity_ids | {relation.subject_entity_id, relation.object_entity_id}
            if len(next_entity_ids) > DEFAULT_CANDIDATE_NODE_LIMIT:
                continue
            relations.append(relation)
            selected_entity_ids = next_entity_ids

        entities = (
            self.db.query(KnowledgeEntityModel)
            .filter(KnowledgeEntityModel.id.in_(list(selected_entity_ids)))
            .order_by(KnowledgeEntityModel.name.asc())
            .all()
            if selected_entity_ids
            else []
        )
        paths = self._build_paths(anchors, relations)
        recommended_path_ids = [path["id"] for path in paths[:3]]
        return {
            "entities": self.serialize_entities(entities),
            "relations": [self.serialize_relation(relation) for relation in relations],
            "paths": paths,
            "recommended_path_ids": recommended_path_ids,
            "anchor_entity_ids": [entity.id for entity in anchors],
            "truncated": len(all_anchor_ids) > len(anchors) or len(candidate_entity_ids) > len(entities) or len(candidate_relations) > len(relations),
            "total_entity_count": len(candidate_entity_ids),
            "total_relation_count": len(candidate_relations),
        }

    def all_graph(self) -> dict:
        entities = self.db.query(KnowledgeEntityModel).order_by(KnowledgeEntityModel.name.asc()).all()
        relations = self.db.query(KnowledgeRelationModel).order_by(KnowledgeRelationModel.id.asc()).all()
        return {
            "entities": self.serialize_entities(entities),
            "relations": [self.serialize_relation(relation) for relation in relations],
            "paths": self._build_paths(entities, relations),
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
        if not self.db.get(KnowledgeEntityModel, entity_id):
            return {"entities": [], "relations": [], "paths": [], "recommended_path_ids": []}
        max_hops = min(max(hops, 1), 2)
        seen_entities = {entity_id}
        frontier = {entity_id}
        relation_map: dict[str, KnowledgeRelationModel] = {}
        for _ in range(max_hops):
            next_frontier: set[str] = set()
            for relation in self._relations_for_entities(frontier, predicates):
                if len(relation_map) >= relation_limit:
                    break
                relation_map[relation.id] = relation
                for next_id in (relation.subject_entity_id, relation.object_entity_id):
                    if next_id not in seen_entities and len(seen_entities) < node_limit:
                        seen_entities.add(next_id)
                        next_frontier.add(next_id)
            frontier = next_frontier
            if not frontier or len(relation_map) >= relation_limit:
                break
        entities = (
            self.db.query(KnowledgeEntityModel)
            .filter(KnowledgeEntityModel.id.in_(list(seen_entities)))
            .all()
        )
        relations = list(relation_map.values())
        return {
            "entities": self.serialize_entities(entities),
            "relations": [self.serialize_relation(relation) for relation in relations],
            "paths": self._build_paths([self.db.get(KnowledgeEntityModel, entity_id)], relations),
            "recommended_path_ids": [],
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
        matched_ids = {entity.id for entity in self.match_entities(message)}
        selected_ids = set(selected_entity_ids)
        if selected_relation_ids:
            relations = (
                self.db.query(KnowledgeRelationModel)
                .filter(KnowledgeRelationModel.id.in_(selected_relation_ids))
                .all()
            )
            for relation in relations:
                selected_ids.add(relation.subject_entity_id)
                selected_ids.add(relation.object_entity_id)
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
        relation_ids = list(dict.fromkeys(selected_relation_ids + self._relation_ids_from_paths(selected_path_ids)))
        selected_entity_set = set(selected_entity_ids)
        if not relation_ids and selected_entity_set:
            relation_ids = sorted(
                relation.id
                for relation in self.db.query(KnowledgeRelationModel).all()
                if (
                    relation.subject_entity_id in selected_entity_set
                    and relation.object_entity_id in selected_entity_set
                )
            )
        relations = (
            self.db.query(KnowledgeRelationModel)
            .filter(KnowledgeRelationModel.id.in_(relation_ids))
            .all()
            if relation_ids
            else []
        )
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
        if selected_path_ids:
            paths = [path for path in paths if path["id"] in set(selected_path_ids)] or paths
        return {
            "entities": [self.serialize_entity(entity) for entity in entities],
            "relations": [self.serialize_relation(relation) for relation in relations],
            "paths": paths,
            "selected_entity_ids": selected_entity_ids,
            "selected_relation_ids": relation_ids,
            "selected_path_ids": selected_path_ids,
        }

    def format_selected_graph_context(self, payload: dict) -> str:
        if not payload.get("relations"):
            return ""
        entity_by_id = {item["id"]: item for item in payload.get("entities", [])}
        lines = [
            "<knowledge_graph_reference>",
            "以下为教师手动选择的知识图谱链路。请只把这些链路作为主回答依据，并区分事实、推断和待验证结论。",
        ]
        for index, relation in enumerate(payload.get("relations", []), start=1):
            subject = entity_by_id.get(relation["subject_entity_id"], {})
            obj = entity_by_id.get(relation["object_entity_id"], {})
            lines.append(
                f"[{index}] {subject.get('name', relation['subject_entity_id'])} "
                f"--{relation['predicate']}--> {obj.get('name', relation['object_entity_id'])}"
            )
            if relation.get("description"):
                lines.append(f"说明：{relation['description']}")
            if relation.get("evidence_source"):
                lines.append(f"证据来源：{relation['evidence_source']}")
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
        queries = []
        for entity in entities:
            aliases = " ".join(self.aliases(entity))
            query = " ".join(item for item in [message, entity.name, aliases, entity.description] if item)
            if query.strip():
                queries.append(query.strip())
        return list(dict.fromkeys(queries))

    def match_entities(self, text: str) -> list[KnowledgeEntityModel]:
        normalized = text or ""
        matches = []
        for entity in self.db.query(KnowledgeEntityModel).order_by(KnowledgeEntityModel.name.asc()).all():
            names = [entity.name, *self.aliases(entity)]
            if any(name and name in normalized for name in names):
                matches.append(entity)
        return matches

    def default_entities_for_expert(self, expert_id: str) -> list[KnowledgeEntityModel]:
        entity_ids = DEFAULT_EXPERT_ENTITY_IDS.get(expert_id or "")
        if entity_ids:
            return (
                self.db.query(KnowledgeEntityModel)
                .filter(KnowledgeEntityModel.id.in_(entity_ids))
                .order_by(KnowledgeEntityModel.name.asc())
                .all()
            )
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
        return self._relations_for_entities({entity_id}, predicates)

    def _relations_for_entities(
        self,
        entity_ids: set[str],
        predicates: list[str] | None = None,
    ) -> list[KnowledgeRelationModel]:
        if not entity_ids:
            return []
        query = self.db.query(KnowledgeRelationModel).filter(
            or_(
                KnowledgeRelationModel.subject_entity_id.in_(entity_ids),
                KnowledgeRelationModel.object_entity_id.in_(entity_ids),
            )
        )
        if predicates:
            query = query.filter(KnowledgeRelationModel.predicate.in_(predicates))
        rows = query.all()
        return sorted(
            rows,
            key=lambda row: (
                -CONFIDENCE_WEIGHT.get(row.confidence, 0),
                row.predicate,
                row.id,
            ),
        )

    def _dedupe_relations(self, relations: list[KnowledgeRelationModel]) -> list[KnowledgeRelationModel]:
        by_id = {relation.id: relation for relation in relations}
        return sorted(
            by_id.values(),
            key=lambda row: (
                -CONFIDENCE_WEIGHT.get(row.confidence, 0),
                row.predicate,
                row.id,
            ),
        )

    def _relation_ids_from_paths(self, path_ids: list[str]) -> list[str]:
        relation_ids: list[str] = []
        for path_id in path_ids:
            if not path_id.startswith("path_"):
                continue
            relation_part = path_id[5:]
            relation_ids.extend(item for item in relation_part.split("__") if item)
        return relation_ids

    def _build_paths(self, anchors: list[KnowledgeEntityModel | None], relations: list[KnowledgeRelationModel]) -> list[dict]:
        paths: list[dict] = []
        seen: set[str] = set()
        for relation in relations:
            path_id = f"path_{relation.id}"
            if path_id not in seen:
                paths.append({"id": path_id, "relation_ids": [relation.id], "score": self._relation_score(relation)})
                seen.add(path_id)

        adjacency: dict[str, list[KnowledgeRelationModel]] = {}
        for relation in relations:
            adjacency.setdefault(relation.subject_entity_id, []).append(relation)
            adjacency.setdefault(relation.object_entity_id, []).append(relation)

        anchor_ids = {entity.id for entity in anchors if entity is not None}
        for first in relations:
            if anchor_ids and first.subject_entity_id not in anchor_ids and first.object_entity_id not in anchor_ids:
                continue
            for middle_id in (first.subject_entity_id, first.object_entity_id):
                for second in adjacency.get(middle_id, []):
                    if first.id == second.id:
                        continue
                    relation_ids = [first.id, second.id]
                    path_id = "path_" + "__".join(relation_ids)
                    if path_id in seen:
                        continue
                    score = self._relation_score(first) + self._relation_score(second)
                    paths.append({"id": path_id, "relation_ids": relation_ids, "score": score})
                    seen.add(path_id)
        paths.sort(key=lambda item: (-item["score"], len(item["relation_ids"]), item["id"]))
        return paths[:10]

    def _relation_score(self, relation: KnowledgeRelationModel) -> int:
        return CONFIDENCE_WEIGHT.get(relation.confidence, 1)

    def _apply_entity_payload(
        self,
        entity: KnowledgeEntityModel,
        payload: dict,
        timestamp: str,
    ) -> None:
        name = str(payload.get("name") or "").strip()
        entity_type = str(payload.get("entity_type") or "").strip()
        if not name or not entity_type:
            raise ValueError("图谱节点必须包含 name 和 entity_type")
        entity.name = name
        entity.entity_type = entity_type
        entity.aliases_json = json.dumps(_json_list(payload.get("aliases")), ensure_ascii=False)
        entity.description = str(payload.get("description") or "").strip()
        entity.source = str(payload.get("source") or "").strip()
        entity.updated_at = timestamp
        self.db.flush()

    def _apply_relation_payload(
        self,
        relation: KnowledgeRelationModel,
        payload: dict,
        timestamp: str,
    ) -> None:
        subject_id = str(payload.get("subject_entity_id") or "").strip()
        object_id = str(payload.get("object_entity_id") or "").strip()
        predicate = str(payload.get("predicate") or "").strip()
        confidence = str(payload.get("confidence") or "medium").strip()
        if not subject_id or not object_id or not predicate:
            raise ValueError("图谱关系必须包含 subject_entity_id、predicate 和 object_entity_id")
        if confidence not in CONFIDENCE_WEIGHT:
            raise ValueError("图谱关系置信度必须是 high、medium 或 low")
        if not self.db.get(KnowledgeEntityModel, subject_id) or not self.db.get(KnowledgeEntityModel, object_id):
            raise ValueError("图谱关系引用了不存在的实体")
        relation.subject_entity_id = subject_id
        relation.predicate = predicate
        relation.object_entity_id = object_id
        relation.description = str(payload.get("description") or "").strip()
        relation.evidence_source = str(payload.get("evidence_source") or "").strip()
        relation.confidence = confidence
        relation.updated_at = timestamp
        self.db.flush()

    def serialize_entities(self, entities: list[KnowledgeEntityModel]) -> list[dict]:
        sources_by_entity = self.rag_sources_for_entities([entity.id for entity in entities])
        return [self.serialize_entity(entity, sources_by_entity.get(entity.id, [])) for entity in entities]

    def serialize_entity(self, entity: KnowledgeEntityModel, rag_sources: list[str] | None = None) -> dict:
        return {
            "id": entity.id,
            "name": entity.name,
            "entity_type": entity.entity_type,
            "aliases": self.aliases(entity),
            "description": entity.description,
            "source": entity.source,
            "rag_sources": self.rag_sources_for_entity(entity.id) if rag_sources is None else rag_sources,
        }

    def serialize_relation(self, relation: KnowledgeRelationModel) -> dict:
        return {
            "id": relation.id,
            "subject_entity_id": relation.subject_entity_id,
            "predicate": relation.predicate,
            "predicate_label": PREDICATE_LABELS.get(relation.predicate, relation.predicate),
            "object_entity_id": relation.object_entity_id,
            "description": relation.description,
            "evidence_source": relation.evidence_source,
            "confidence": relation.confidence,
        }
