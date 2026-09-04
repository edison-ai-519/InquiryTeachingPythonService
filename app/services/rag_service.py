import json

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.curriculum_knowledge_service import (
    CurriculumKnowledgeService,
    CurriculumSearchResult,
)


class RagService:
    @staticmethod
    def retrieve_curriculum_context(
        db: Session,
        *,
        topic: str,
        stage: dict,
        user_message: str,
        expert_id: str,
        allowed_sources: list[str],
    ) -> tuple[str, dict]:
        settings = get_settings()
        query = RagService.build_curriculum_query(
            topic=topic,
            stage=stage,
            user_message=user_message,
        )
        if not settings.curriculum_rag_enabled:
            return "", {
                "mode": "disabled",
                "query": query,
                "reason": "CURRICULUM_RAG_ENABLED=false",
                "expert_id": expert_id,
                "allowed_sources": allowed_sources,
                "hit_sources": [],
                "records": [],
            }

        try:
            service = CurriculumKnowledgeService(db, settings)
            results = service.retrieve(query, settings.curriculum_top_k, allowed_sources)
        except Exception as exc:
            return "", {
                "mode": "local_bm25_error",
                "query": query,
                "error": str(exc),
                "expert_id": expert_id,
                "allowed_sources": allowed_sources,
                "hit_sources": [],
                "records": [],
            }

        records = [RagService.curriculum_result_to_dict(result) for result in results]
        if not results:
            return "", {
                "mode": service.last_retrieval.get("mode", "local_bm25_empty"),
                "query": query,
                "vector_error": service.last_retrieval.get("vector_error", ""),
                "expert_id": expert_id,
                "allowed_sources": allowed_sources,
                "hit_sources": [],
                "records": [],
            }
        return RagService.format_curriculum_context(results), {
            "mode": service.last_retrieval.get("mode", "local_bm25"),
            "query": query,
            "vector_error": service.last_retrieval.get("vector_error", ""),
            "expert_id": expert_id,
            "allowed_sources": allowed_sources,
            "hit_sources": list(dict.fromkeys(result.source for result in results)),
            "records": records,
        }

    @staticmethod
    def build_curriculum_query(*, topic: str, stage: dict, user_message: str) -> str:
        parts = [
            topic.strip(),
            str(stage.get("name") or "").strip(),
            str(stage.get("display_direction") or "").strip(),
            user_message.strip(),
        ]
        return "\n".join(part for part in parts if part)

    @staticmethod
    def format_curriculum_context(results: list[CurriculumSearchResult]) -> str:
        sections = [
            "<curriculum_reference>",
            "以下内容仅作为课程标准参考，请结合学生年龄、技术基础和当前教学目标使用。",
        ]
        for index, result in enumerate(results, start=1):
            sections.extend(
                [
                    "",
                    f"[{index}] 来源：{result.source}",
                    f"相关内容：{result.content}",
                ]
            )
        sections.extend(
            [
                "",
                "请据此调整任务难度、活动形式、技术要求和评价方式，不要机械复述课标。",
                "</curriculum_reference>",
            ]
        )
        return "\n".join(sections)

    @staticmethod
    def merge_context(doc_input: str, curriculum_context: str) -> str:
        return "\n\n".join(
            item.strip()
            for item in (doc_input, curriculum_context)
            if item and item.strip()
        )

    @staticmethod
    def curriculum_sources(source: dict) -> list[str]:
        return list(
            dict.fromkeys(
                str(record.get("source") or "").strip()
                for record in source.get("records", [])
                if str(record.get("source") or "").strip()
            )
        )

    @staticmethod
    def source_note(sources: list[str]) -> str:
        if not sources:
            return ""
        return "\n\n参考课标：" + "、".join(sources)

    @staticmethod
    def curriculum_result_to_dict(result: CurriculumSearchResult) -> dict:
        return {
            "chunk_id": result.chunk_id,
            "chunk_ids": list(result.chunk_ids),
            "source": result.source,
            "source_index": result.source_index,
            "content": result.content,
            "score": result.score,
            "bm25_score": result.bm25_score,
            "vector_score": result.vector_score,
            "fusion_score": result.fusion_score,
            "retrieval_mode": result.retrieval_mode,
        }

    @staticmethod
    def source_json(source: dict) -> str:
        return json.dumps(source, ensure_ascii=False)
