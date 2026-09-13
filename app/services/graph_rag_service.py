from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.curriculum_knowledge_service import CurriculumKnowledgeService
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.rag_service import RagService


class GraphRagService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def resolve_sources(
        self,
        *,
        selected_entity_ids: list[str],
        allowed_sources: list[str] | None,
    ) -> dict:
        normalized_allowed = list(dict.fromkeys(allowed_sources or []))
        bindings = KnowledgeGraphService(self.db).rag_sources_for_entities(
            selected_entity_ids
        )
        configured_sources = list(
            dict.fromkeys(
                source
                for entity_sources in bindings.values()
                for source in entity_sources
            )
        )
        if configured_sources:
            effective_sources = [
                source for source in configured_sources if source in normalized_allowed
            ]
            source_resolution = (
                "node_configured" if effective_sources else "configured_but_not_allowed"
            )
        elif normalized_allowed:
            effective_sources = normalized_allowed
            source_resolution = "expert_fallback"
        else:
            effective_sources = []
            source_resolution = "no_expert_permission"
        return {
            "configured_sources": configured_sources,
            "allowed_sources": normalized_allowed,
            "effective_sources": effective_sources,
            "source_resolution": source_resolution,
            "fallback_reason": ""
            if source_resolution in {"node_configured", "expert_fallback"}
            else source_resolution,
        }

    def retrieve_for_selection(
        self,
        *,
        message: str,
        selected_entity_ids: list[str],
        allowed_sources: list[str] | None = None,
    ) -> tuple[str, dict]:
        graph_service = KnowledgeGraphService(self.db)
        source_resolution = self.resolve_sources(
            selected_entity_ids=selected_entity_ids,
            allowed_sources=allowed_sources,
        )
        queries = graph_service.graph_rag_queries(message, selected_entity_ids)
        if not self.settings.curriculum_rag_enabled:
            return "", {
                **source_resolution,
                "mode": "disabled",
                "reason": "CURRICULUM_RAG_ENABLED=false",
                "rag_node_queries": queries,
                "records": [],
                "hit_sources": [],
            }
        if not queries:
            return "", {
                **source_resolution,
                "rag_node_queries": [],
                "records": [],
                "hit_sources": [],
            }

        try:
            knowledge = CurriculumKnowledgeService(self.db, self.settings)
            all_records = []
            contexts = []
            hit_sources = []
            for query in queries[:3]:
                results = knowledge.retrieve(
                    query,
                    self.settings.curriculum_top_k,
                    source_resolution["effective_sources"],
                )
                if not results:
                    continue
                all_records.extend(RagService.curriculum_result_to_dict(result) for result in results)
                contexts.append(RagService.format_graph_rag_context(query, results))
                hit_sources.extend(result.source for result in results)
        except Exception as exc:
            return "", {
                **source_resolution,
                "mode": "local_bm25_error",
                "error": str(exc),
                "rag_node_queries": queries,
                "records": [],
                "hit_sources": [],
            }

        return "\n\n".join(contexts), {
            **source_resolution,
            "rag_node_queries": queries,
            "records": all_records,
            "hit_sources": list(dict.fromkeys(hit_sources)),
            "mode": knowledge.last_retrieval.get("mode", "local_bm25"),
            "vector_error": knowledge.last_retrieval.get("vector_error", ""),
        }
