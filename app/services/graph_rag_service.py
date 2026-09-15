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
                source
                for source in configured_sources
                if source in normalized_allowed
            ]
            source_resolution = (
                "node_configured"
                if effective_sources
                else "configured_but_not_allowed"
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
        selected_relation_ids: list[str] | None = None,
        allowed_sources: list[str] | None = None,
    ) -> tuple[str, dict]:
        graph_service = KnowledgeGraphService(self.db)
        relation_ids = list(dict.fromkeys(selected_relation_ids or []))
        source_resolution = self.resolve_sources(
            selected_entity_ids=selected_entity_ids,
            allowed_sources=allowed_sources,
        )
        allowed = source_resolution["allowed_sources"]
        links = graph_service.linked_chunk_ids(
            entity_ids=selected_entity_ids,
            relation_ids=relation_ids,
            allowed_sources=allowed,
        )
        queries = graph_service.graph_rag_queries(
            message,
            selected_entity_ids,
        )
        if not self.settings.curriculum_rag_enabled:
            return "", {
                **source_resolution,
                **links,
                "mode": "disabled",
                "reason": "CURRICULUM_RAG_ENABLED=false",
                "rag_node_queries": queries,
                "records": [],
                "hit_sources": [],
                "retrieval_strategy": "disabled",
            }
        if not queries:
            return "", {
                **source_resolution,
                **links,
                "rag_node_queries": [],
                "records": [],
                "hit_sources": [],
                "retrieval_strategy": "empty_query",
            }

        query = queries[0]
        attempts: list[tuple[str, list[str], list[int] | None]] = []
        if links["linked_chunk_ids"] and allowed:
            attempts.append(
                ("linked_chunks", allowed, links["linked_chunk_ids"])
            )
        effective_sources = source_resolution["effective_sources"]
        if (
            effective_sources
            and source_resolution["source_resolution"] == "node_configured"
        ):
            attempts.append(("node_source_fallback", effective_sources, None))
        if allowed and (
            source_resolution["source_resolution"] != "node_configured"
            or allowed != effective_sources
        ):
            attempts.append(("knowledge_fallback", allowed, None))

        knowledge = CurriculumKnowledgeService(self.db, self.settings)
        vector_error = ""
        last_mode = "local_bm25_empty"
        for strategy, sources, chunk_ids in attempts:
            try:
                results = knowledge.retrieve(
                    query,
                    self.settings.curriculum_top_k,
                    sources,
                    chunk_ids,
                )
            except Exception as exc:
                vector_error = str(exc)
                continue
            last_mode = knowledge.last_retrieval.get(
                "mode",
                "local_bm25",
            )
            vector_error = knowledge.last_retrieval.get("vector_error", "")
            if not results:
                continue
            records = [
                {
                    **RagService.curriculum_result_to_dict(result),
                    "retrieval_strategy": strategy,
                }
                for result in results
            ]
            return RagService.format_graph_rag_context(query, results), {
                **source_resolution,
                **links,
                "rag_node_queries": queries,
                "records": records,
                "hit_sources": list(
                    dict.fromkeys(result.source for result in results)
                ),
                "mode": last_mode,
                "vector_error": vector_error,
                "retrieval_strategy": strategy,
            }

        return "", {
            **source_resolution,
            **links,
            "rag_node_queries": queries,
            "records": [],
            "hit_sources": [],
            "mode": "local_bm25_error" if vector_error else last_mode,
            "vector_error": vector_error,
            "error": vector_error,
            "retrieval_strategy": (
                attempts[-1][0] if attempts else "no_expert_permission"
            ),
        }
