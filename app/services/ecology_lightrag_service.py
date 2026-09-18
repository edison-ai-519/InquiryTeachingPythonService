from __future__ import annotations

import asyncio
import hashlib
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.services.curriculum_vector_service import get_local_embedding_model


LIGHTRAG_EXTRACTOR_VERSION = "ecology-v1"


class EcologyLightRagError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExtractedEntity:
    name: str
    entity_type: str
    description: str = ""


@dataclass(frozen=True)
class ExtractedRelation:
    subject: str
    object: str
    description: str = ""
    keywords: str = ""


@dataclass(frozen=True)
class EcologyExtractionResult:
    entities: dict[str, ExtractedEntity]
    relations: list[ExtractedRelation]
    document_id: str


def _plain_value(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    as_dict = getattr(value, "dict", None)
    if callable(as_dict):
        return as_dict()
    return value


class EcologyLightRagExtractor:
    """Small, version-pinned adapter around LightRAG's public async API."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def extract(
        self,
        *,
        source: str,
        checksum: str,
        chunks: list[str],
    ) -> EcologyExtractionResult:
        if not chunks:
            return EcologyExtractionResult({}, [], self.document_id(source, checksum))
        if not self.settings.llm_api_key:
            raise EcologyLightRagError("LightRAG 自动建图需要配置 LLM_API_KEY")
        try:
            import numpy as np
            from lightrag import LightRAG
            from lightrag.kg.shared_storage import initialize_pipeline_status
            from lightrag.llm.openai import openai_complete_if_cache
            from lightrag.utils import wrap_embedding_func_with_attrs
        except Exception as exc:
            raise EcologyLightRagError(
                "缺少 LightRAG 依赖，请执行 pip install -r requirements.txt"
            ) from exc

        doc_id = self.document_id(source, checksum)
        work_dir = self._working_dir(source, checksum)
        work_dir.mkdir(parents=True, exist_ok=True)
        embedding_model = get_local_embedding_model(self.settings)
        try:
            embedding_model.load()
        except Exception as exc:
            raise EcologyLightRagError(str(exc)) from exc
        dimension = int(embedding_model.dimension or 0)
        if not dimension:
            raise EcologyLightRagError("本地 Embedding 模型未提供向量维度")

        settings = self.settings

        async def llm_model_func(
            prompt: str,
            system_prompt: str | None = None,
            history_messages: list[dict] | None = None,
            **kwargs,
        ) -> str:
            headers = {}
            if settings.llm_http_referer:
                headers["HTTP-Referer"] = settings.llm_http_referer
            if settings.llm_app_title:
                headers["X-Title"] = settings.llm_app_title
            if headers:
                client_configs = dict(kwargs.pop("openai_client_configs", {}) or {})
                client_configs["default_headers"] = {
                    **dict(client_configs.get("default_headers") or {}),
                    **headers,
                }
                kwargs["openai_client_configs"] = client_configs
            return await openai_complete_if_cache(
                settings.ecology_graph_extract_model,
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages or [],
                api_key=settings.llm_api_key,
                base_url=settings.llm_api_base,
                **kwargs,
            )

        @wrap_embedding_func_with_attrs(
            embedding_dim=dimension,
            max_token_size=8192,
            model_name=settings.curriculum_embedding_model,
        )
        async def embedding_func(texts: list[str]):
            values = await asyncio.to_thread(embedding_model.encode, texts)
            return np.asarray(values, dtype=np.float32)

        rag = LightRAG(
            working_dir=str(work_dir),
            workspace="ecology",
            llm_model_func=llm_model_func,
            llm_model_name=settings.ecology_graph_extract_model,
            embedding_func=embedding_func,
            max_parallel_insert=1,
            addon_params={
                "language": "Simplified Chinese",
                "entity_types_guidance": (
                    "只抽取 INSECT（昆虫）、PLANT（植物）和 HABITAT（栖息地）实体。"
                    "只抽取文本明确表达的取食、访花、授粉、栖息、产卵、危害、捕食、寄生关系；"
                    "关系描述必须保留原文中的生态行为词，不得根据常识补充。"
                ),
            },
        )
        try:
            await rag.initialize_storages()
            await initialize_pipeline_status()
            await rag.ainsert(
                "\n\n".join(chunks),
                ids=[doc_id],
                file_paths=[source],
            )
            graph = await rag.get_knowledge_graph(
                node_label="*",
                max_depth=3,
                max_nodes=10000,
            )
            entities, relations = self.parse_graph(graph)
            self.prune_source_versions(source, keep_checksum=checksum)
            return EcologyExtractionResult(entities, relations, doc_id)
        except EcologyLightRagError:
            raise
        except Exception as exc:
            raise EcologyLightRagError(
                f"LightRAG 抽取失败：{type(exc).__name__}: {exc}"
            ) from exc
        finally:
            finalize = getattr(rag, "finalize_storages", None)
            if callable(finalize):
                try:
                    await finalize()
                except Exception:
                    pass

    @staticmethod
    def document_id(source: str, checksum: str) -> str:
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
        return f"ecology-{digest}-{checksum[:16]}"

    def _working_dir(self, source: str, checksum: str) -> Path:
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
        safe_checksum = re.sub(r"[^a-zA-Z0-9_-]", "", checksum)[:16] or "unknown"
        return self.settings.ecology_lightrag_dir / digest / safe_checksum

    def prune_source_versions(self, source: str, *, keep_checksum: str = "") -> None:
        source_dir = self._source_dir(source)
        if not source_dir.is_dir():
            return
        keep_dir = self._working_dir(source, keep_checksum).resolve() if keep_checksum else None
        for child in source_dir.iterdir():
            resolved = child.resolve()
            if keep_dir is not None and resolved == keep_dir:
                continue
            if child.is_dir() and source_dir.resolve() in resolved.parents:
                shutil.rmtree(resolved, ignore_errors=True)
        if keep_dir is None:
            try:
                source_dir.rmdir()
            except OSError:
                pass

    def delete_source_artifacts(self, source: str) -> None:
        self.prune_source_versions(source)

    def _source_dir(self, source: str) -> Path:
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
        return self.settings.ecology_lightrag_dir / digest

    @classmethod
    def parse_graph(
        cls,
        graph: Any,
    ) -> tuple[dict[str, ExtractedEntity], list[ExtractedRelation]]:
        payload = _plain_value(graph)
        if not isinstance(payload, dict):
            payload = {
                "nodes": getattr(graph, "nodes", []),
                "edges": getattr(graph, "edges", []),
            }
        entities: dict[str, ExtractedEntity] = {}
        for raw in payload.get("nodes") or []:
            item = _plain_value(raw)
            if not isinstance(item, dict):
                continue
            properties = _plain_value(item.get("properties") or {})
            if not isinstance(properties, dict):
                properties = {}
            name = str(
                item.get("id")
                or item.get("entity_id")
                or item.get("label")
                or item.get("name")
                or properties.get("entity_id")
                or properties.get("name")
                or ""
            ).strip()
            if not name:
                continue
            entities[name] = ExtractedEntity(
                name=name,
                entity_type=str(
                    properties.get("entity_type")
                    or item.get("entity_type")
                    or ""
                ).strip(),
                description=str(
                    properties.get("description")
                    or item.get("description")
                    or ""
                ).strip(),
            )

        relations: list[ExtractedRelation] = []
        for raw in payload.get("edges") or payload.get("links") or []:
            item = _plain_value(raw)
            if not isinstance(item, dict):
                continue
            properties = _plain_value(item.get("properties") or {})
            if not isinstance(properties, dict):
                properties = {}
            subject = str(
                item.get("source")
                or item.get("src_id")
                or item.get("source_node_id")
                or ""
            ).strip()
            object_name = str(
                item.get("target")
                or item.get("tgt_id")
                or item.get("target_node_id")
                or ""
            ).strip()
            if not subject or not object_name or subject == object_name:
                continue
            relations.append(
                ExtractedRelation(
                    subject=subject,
                    object=object_name,
                    description=str(
                        properties.get("description")
                        or item.get("description")
                        or ""
                    ).strip(),
                    keywords=str(
                        properties.get("keywords")
                        or item.get("keywords")
                        or ""
                    ).strip(),
                )
            )
        return entities, relations
