from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path

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
PREDICATE_LABELS = {
    "feeds_on": "取食",
    "predator_of": "捕食",
    "produces": "产生",
    "attracted_by": "被吸引",
    "performs": "进行",
}


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
            anchors = self.db.query(KnowledgeEntityModel).order_by(KnowledgeEntityModel.name.asc()).limit(3).all()

        relation_map: dict[str, KnowledgeRelationModel] = {}
        for entity in anchors:
            for relation in self._relations_for_entity(entity.id):
                relation_map[relation.id] = relation
                for next_id in (relation.subject_entity_id, relation.object_entity_id):
                    if next_id == entity.id:
                        continue
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
        recommended_path_ids = [path["id"] for path in paths[:3]]
        return {
            "entities": [self.serialize_entity(entity) for entity in entities],
            "relations": [self.serialize_relation(relation) for relation in relations],
            "paths": paths,
            "recommended_path_ids": recommended_path_ids,
        }

    def all_graph(self) -> dict:
        entities = self.db.query(KnowledgeEntityModel).order_by(KnowledgeEntityModel.name.asc()).all()
        relations = self.db.query(KnowledgeRelationModel).order_by(KnowledgeRelationModel.id.asc()).all()
        return {
            "entities": [self.serialize_entity(entity) for entity in entities],
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
            for current_id in sorted(frontier):
                for relation in self._relations_for_entity(current_id, predicates):
                    if len(relation_map) >= relation_limit:
                        break
                    relation_map[relation.id] = relation
                    for next_id in (relation.subject_entity_id, relation.object_entity_id):
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
        return {
            "entities": [self.serialize_entity(entity) for entity in entities],
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
            or_(
                KnowledgeRelationModel.subject_entity_id == entity_id,
                KnowledgeRelationModel.object_entity_id == entity_id,
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

    def _relation_ids_from_paths(self, path_ids: list[str]) -> list[str]:
        relation_ids: list[str] = []
        for path_id in path_ids:
            if not path_id.startswith("path_"):
                continue
            relation_part = path_id[5:]
            relation_ids.extend(item for item in relation_part.split("__") if item)
        return relation_ids

    def _build_paths(self, anchors: list[KnowledgeEntityModel | None], relations: list[KnowledgeRelationModel]) -> list[dict]:
        relation_by_id = {relation.id: relation for relation in relations}
        paths: list[dict] = []
        seen: set[str] = set()
        for relation in relations:
            path_id = f"path_{relation.id}"
            if path_id not in seen:
                paths.append({"id": path_id, "relation_ids": [relation.id], "score": self._relation_score(relation)})
                seen.add(path_id)

        anchor_ids = {entity.id for entity in anchors if entity is not None}
        for first in relations:
            if anchor_ids and first.subject_entity_id not in anchor_ids and first.object_entity_id not in anchor_ids:
                continue
            middle_ids = {first.subject_entity_id, first.object_entity_id}
            for second in relations:
                if first.id == second.id:
                    continue
                if not middle_ids.intersection({second.subject_entity_id, second.object_entity_id}):
                    continue
                relation_ids = [first.id, second.id]
                path_id = "path_" + "__".join(relation_ids)
                if path_id in seen:
                    continue
                score = self._relation_score(first) + self._relation_score(relation_by_id[second.id])
                paths.append({"id": path_id, "relation_ids": relation_ids, "score": score})
                seen.add(path_id)
        paths.sort(key=lambda item: (-item["score"], len(item["relation_ids"]), item["id"]))
        return paths[:10]

    def _relation_score(self, relation: KnowledgeRelationModel) -> int:
        return CONFIDENCE_WEIGHT.get(relation.confidence, 1)

    def serialize_entity(self, entity: KnowledgeEntityModel) -> dict:
        return {
            "id": entity.id,
            "name": entity.name,
            "entity_type": entity.entity_type,
            "aliases": self.aliases(entity),
            "description": entity.description,
            "source": entity.source,
            "rag_sources": self.rag_sources_for_entity(entity.id),
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
