from __future__ import annotations

import hashlib
import math
import importlib.util
import shutil
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Protocol
from urllib.parse import urlsplit

import httpx

from app.core.config import Settings
from app.db.models import CurriculumChunkModel


class CurriculumVectorUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class CurriculumVectorHit:
    chunk_id: int
    score: float


_MODEL_CACHE: dict[tuple[str, str, int], "LocalEmbeddingModel"] = {}
_MODEL_CACHE_LOCK = threading.Lock()
_VECTOR_LOCKS: dict[str, threading.RLock] = {}
_VECTOR_LOCKS_GUARD = threading.Lock()


def get_local_embedding_model(settings: Settings) -> "LocalEmbeddingModel":
    key = (
        str(settings.curriculum_embedding_model_dir),
        settings.curriculum_embedding_device,
        settings.curriculum_embedding_batch_size,
    )
    with _MODEL_CACHE_LOCK:
        model = _MODEL_CACHE.get(key)
        if model is None:
            model = LocalEmbeddingModel(settings)
            _MODEL_CACHE[key] = model
        return model


class EmbeddingModel(Protocol):
    model_name: str
    dimension: int | None

    def availability_error(self) -> str: ...
    def load(self): ...
    def encode(self, texts: Iterable[str]) -> list[list[float]]: ...


def embedding_identity(settings: Settings) -> dict[str, str]:
    provider = settings.curriculum_embedding_provider
    endpoint = settings.curriculum_embedding_api_base.rstrip("/") if provider == "remote" else ""
    return {
        "embedding_provider": provider,
        "embedding_model": settings.curriculum_effective_embedding_model,
        "embedding_endpoint": hashlib.sha256(endpoint.encode()).hexdigest() if endpoint else "",
    }


_REMOTE_MODEL_CACHE: dict[tuple, "RemoteEmbeddingModel"] = {}


def get_embedding_model(settings: Settings) -> EmbeddingModel:
    if settings.curriculum_embedding_provider == "local":
        return get_local_embedding_model(settings)
    key = (
        settings.curriculum_embedding_provider,
        settings.curriculum_embedding_api_base,
        settings.curriculum_embedding_api_model,
        settings.curriculum_embedding_api_key,
        settings.curriculum_embedding_api_timeout_seconds,
        settings.curriculum_embedding_batch_size,
    )
    with _MODEL_CACHE_LOCK:
        if key not in _REMOTE_MODEL_CACHE:
            _REMOTE_MODEL_CACHE[key] = RemoteEmbeddingModel(settings)
        return _REMOTE_MODEL_CACHE[key]


class RemoteEmbeddingModel:
    def __init__(self, settings: Settings):
        self.provider = settings.curriculum_embedding_provider
        self.model_name = settings.curriculum_embedding_api_model
        self.api_base = settings.curriculum_embedding_api_base.rstrip("/")
        self.api_key = settings.curriculum_embedding_api_key
        self.timeout = settings.curriculum_embedding_api_timeout_seconds
        self.batch_size = settings.curriculum_embedding_batch_size
        self.dimension: int | None = None
        self._encode_lock = threading.Lock()

    def availability_error(self) -> str:
        if self.provider != "remote":
            return "CURRICULUM_EMBEDDING_PROVIDER 必须为 local 或 remote"
        try:
            url = urlsplit(self.api_base)
            _ = url.port  # Validate malformed or out-of-range ports as configuration errors.
            valid = url.scheme in {"http", "https"} and url.hostname and not (
                url.username or url.password or url.query or url.fragment
            )
        except ValueError:
            valid = False
        if not valid:
            return "请配置有效的 CURRICULUM_EMBEDDING_API_BASE（HTTP(S) 服务根路径）"
        if not self.model_name:
            return "请配置 CURRICULUM_EMBEDDING_API_MODEL"
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            return "CURRICULUM_EMBEDDING_API_TIMEOUT_SECONDS 必须为正数"
        if self.batch_size < 1:
            return "CURRICULUM_EMBEDDING_BATCH_SIZE 必须为正整数"
        return ""

    def load(self):
        if self.dimension is None:
            self.encode(["embedding dimension probe"])
        return self

    def encode(self, texts: Iterable[str]) -> list[list[float]]:
        error = self.availability_error()
        if error:
            raise CurriculumVectorUnavailable(error)
        values = [text if text.strip() else " " for text in texts]
        if not values:
            return []
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        vectors: list[list[float]] = []
        with self._encode_lock:
            dimension = self.dimension
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    for start in range(0, len(values), self.batch_size):
                        batch = values[start:start + self.batch_size]
                        response = client.post(
                            f"{self.api_base}/embeddings",
                            headers=headers,
                            json={"model": self.model_name, "input": batch, "encoding_format": "float"},
                        )
                        response.raise_for_status()
                        data = response.json()["data"]
                        if not isinstance(data, list) or len(data) != len(batch):
                            raise ValueError("invalid count")
                        ordered: dict[int, list[float]] = {}
                        for item in data:
                            index = item["index"]
                            if type(index) is not int or not 0 <= index < len(batch) or index in ordered:
                                raise ValueError("invalid index")
                            raw = item["embedding"]
                            if not isinstance(raw, list) or not raw or any(
                                type(v) not in (float, int) or not math.isfinite(v) for v in raw
                            ):
                                raise ValueError("invalid vector")
                            vector = [float(v) for v in raw]
                            dimension = dimension or len(vector)
                            if len(vector) != dimension:
                                raise ValueError("inconsistent dimension")
                            norm = math.hypot(*vector)
                            if not norm or not math.isfinite(norm):
                                raise ValueError("invalid norm")
                            ordered[index] = [v / norm for v in vector]
                        vectors.extend(ordered[i] for i in range(len(batch)))
            except httpx.HTTPStatusError as exc:
                raise CurriculumVectorUnavailable(
                    f"远程 Embedding 请求失败：HTTP {exc.response.status_code}"
                ) from None
            except httpx.TimeoutException:
                raise CurriculumVectorUnavailable("远程 Embedding 请求超时") from None
            except httpx.RequestError:
                raise CurriculumVectorUnavailable("远程 Embedding 网络请求失败") from None
            except (ValueError, KeyError, TypeError, OverflowError):
                raise CurriculumVectorUnavailable("远程 Embedding 响应无效（数量、顺序、数值或维度错误）") from None
            self.dimension = dimension
        return vectors


def vector_directory_lock(path: Path) -> threading.RLock:
    key = str(path.resolve())
    with _VECTOR_LOCKS_GUARD:
        lock = _VECTOR_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _VECTOR_LOCKS[key] = lock
        return lock


class LocalEmbeddingModel:
    def __init__(self, settings: Settings):
        self.model_name = settings.curriculum_embedding_model
        self.model_dir = settings.curriculum_embedding_model_dir
        self.device = settings.curriculum_embedding_device or "cpu"
        self.batch_size = settings.curriculum_embedding_batch_size
        self._model = None
        self._dimension: int | None = None
        self._load_lock = threading.Lock()
        self._encode_lock = threading.Lock()

    @property
    def dimension(self) -> int | None:
        return self._dimension

    def availability_error(self) -> str:
        if not self.model_dir.is_dir():
            return f"本地 Embedding 模型不存在：{self.model_dir}"
        if importlib.util.find_spec("sentence_transformers") is None:
            return "缺少 sentence-transformers 依赖"
        if importlib.util.find_spec("torch") is None:
            return "缺少 torch 依赖"
        return ""

    def load(self):
        if self._model is not None:
            return self._model
        with self._load_lock:
            if self._model is not None:
                return self._model
            error = self.availability_error()
            if error:
                raise CurriculumVectorUnavailable(error)
            try:
                from sentence_transformers import SentenceTransformer

                model = SentenceTransformer(str(self.model_dir), device=self.device)
                get_dimension = getattr(model, "get_embedding_dimension", None)
                if get_dimension is None:
                    get_dimension = model.get_sentence_embedding_dimension
                dimension = get_dimension()
            except Exception as exc:
                raise CurriculumVectorUnavailable(
                    f"本地 Embedding 模型加载失败：{type(exc).__name__}: {exc}"
                ) from exc
            if not dimension:
                raise CurriculumVectorUnavailable("Embedding 模型未提供有效向量维度")
            self._model = model
            self._dimension = int(dimension)
            return model

    def encode(self, texts: Iterable[str]) -> list[list[float]]:
        values = [text if text.strip() else " " for text in texts]
        if not values:
            return []
        model = self.load()
        try:
            with self._encode_lock:
                vectors = model.encode(
                    values,
                    batch_size=self.batch_size,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                )
        except Exception as exc:
            raise CurriculumVectorUnavailable(
                f"Embedding 计算失败：{type(exc).__name__}: {exc}"
            ) from exc
        return [[float(value) for value in row] for row in vectors]


class CurriculumVectorStore:
    def __init__(
        self,
        settings: Settings,
        embedding_model: EmbeddingModel | None = None,
    ):
        self.settings = settings
        self.embedding_model = embedding_model or get_embedding_model(settings)
        self.persist_dir = settings.curriculum_vector_dir
        self.collection_name = settings.curriculum_vector_collection
        self.error = ""
        self.rebuild_required = False
        self.client = None
        self.collection = None
        self._lock = vector_directory_lock(self.persist_dir)
        self._initialize()

    @property
    def available(self) -> bool:
        return self.collection is not None and not self.error and not self.rebuild_required

    def _initialize(self) -> None:
        if not self.settings.curriculum_vector_enabled:
            self.error = "向量检索未启用"
            return
        model_error = self.embedding_model.availability_error()
        if model_error:
            self.error = model_error
            return
        if importlib.util.find_spec("chromadb") is None:
            self.error = "缺少 chromadb 依赖"
            return
        try:
            import chromadb

            self.persist_dir.mkdir(parents=True, exist_ok=True)
            chroma_settings = chromadb.config.Settings(anonymized_telemetry=False)
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=chroma_settings,
            )
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=None,
                metadata={
                    "hnsw:space": "cosine",
                    **embedding_identity(self.settings),
                },
            )
            metadata = self.collection.metadata or {}
            expected = embedding_identity(self.settings)
            actual = {
                "embedding_provider": str(metadata.get("embedding_provider") or "local"),
                "embedding_model": str(metadata.get("embedding_model") or ""),
                "embedding_endpoint": str(metadata.get("embedding_endpoint") or ""),
            }
            if self.collection.count() and actual != expected:
                self.rebuild_required = True
                self.error = "向量索引的 Embedding 服务或模型已变化，需要重建索引"
        except Exception as exc:
            self.client = None
            self.collection = None
            self.error = f"Chroma 初始化失败：{type(exc).__name__}: {exc}"

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        if self.collection is None:
            raise CurriculumVectorUnavailable(self.error or "Chroma 不可用")
        if self.rebuild_required:
            raise CurriculumVectorUnavailable(self.error)
        vectors = self.embedding_model.encode(texts)
        if vectors:
            self._validate_dimension(len(vectors[0]))
        return vectors

    def _validate_dimension(self, dimension: int) -> None:
        if self.rebuild_required:
            raise CurriculumVectorUnavailable(self.error)
        if self.collection is None:
            raise CurriculumVectorUnavailable(self.error or "Chroma 不可用")
        metadata = dict(self.collection.metadata or {})
        indexed_dimension = int(metadata.get("embedding_dimension") or 0)
        if self.collection.count() and indexed_dimension and indexed_dimension != dimension:
            self.rebuild_required = True
            self.error = (
                f"向量索引维度为 {indexed_dimension}，当前模型维度为 {dimension}，需要重建索引"
            )
            raise CurriculumVectorUnavailable(self.error)
        if indexed_dimension != dimension:
            self.collection.modify(
                metadata={
                    **metadata,
                    **embedding_identity(self.settings),
                    "embedding_dimension": dimension,
                }
            )

    def upsert_chunks(
        self,
        chunks: list[CurriculumChunkModel],
        embeddings: list[list[float]],
    ) -> int:
        rows = [row for row in chunks if row.id is not None and row.content.strip()]
        if len(rows) != len(embeddings):
            raise CurriculumVectorUnavailable("课标片段与向量数量不一致")
        if not rows:
            return 0
        if self.collection is None:
            raise CurriculumVectorUnavailable(self.error or "Chroma 不可用")
        self._validate_dimension(len(embeddings[0]))
        with self._lock:
            for start in range(0, len(rows), 256):
                batch_rows = rows[start : start + 256]
                batch_vectors = embeddings[start : start + 256]
                self.collection.upsert(
                    ids=[self._id(int(row.id)) for row in batch_rows],
                    embeddings=batch_vectors,
                    metadatas=[
                        {
                            "db_id": int(row.id),
                            "source": row.source,
                            "source_index": int(row.source_index),
                        }
                        for row in batch_rows
                    ],
                )
        return len(rows)

    def index_chunks(self, chunks: list[CurriculumChunkModel]) -> int:
        embeddings = self.embed_texts([row.content for row in chunks])
        return self.upsert_chunks(chunks, embeddings)

    def delete_source(self, source: str) -> None:
        if self.collection is None:
            return
        with self._lock:
            self.collection.delete(where={"source": source})

    def query(
        self,
        query: str,
        top_k: int,
        allowed_sources: list[str] | None = None,
        allowed_chunk_ids: list[int] | None = None,
    ) -> list[CurriculumVectorHit]:
        if not self.available:
            raise CurriculumVectorUnavailable(self.error or "向量检索不可用")
        query_vectors = self.embed_texts([query])
        if not query_vectors:
            return []
        filters: list[dict] = []
        if allowed_sources is not None:
            normalized_sources = list(dict.fromkeys(allowed_sources))
            if not normalized_sources:
                return []
            filters.append(
                {"source": normalized_sources[0]}
                if len(normalized_sources) == 1
                else {"source": {"$in": normalized_sources}}
            )
        if allowed_chunk_ids is not None:
            normalized_chunk_ids = list(
                dict.fromkeys(int(value) for value in allowed_chunk_ids)
            )
            if not normalized_chunk_ids:
                return []
            filters.append(
                {"db_id": normalized_chunk_ids[0]}
                if len(normalized_chunk_ids) == 1
                else {"db_id": {"$in": normalized_chunk_ids}}
            )
        where = None
        if len(filters) == 1:
            where = filters[0]
        elif filters:
            where = {"$and": filters}
        query_args = {
            "query_embeddings": query_vectors,
            "n_results": max(1, top_k),
            "include": ["metadatas", "distances"],
        }
        if where is not None:
            query_args["where"] = where
        result = self.collection.query(
            **query_args,
        )
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        hits: list[CurriculumVectorHit] = []
        for index, metadata in enumerate(metadatas):
            chunk_id = metadata.get("db_id") if metadata else None
            if chunk_id is None:
                continue
            distance = float(distances[index]) if index < len(distances) else 1.0
            hits.append(
                CurriculumVectorHit(
                    chunk_id=int(chunk_id),
                    score=max(0.0, 1.0 - distance),
                )
            )
        return hits

    def rebuild(self, chunks: list[CurriculumChunkModel]) -> int:
        if self.client is None:
            raise CurriculumVectorUnavailable(self.error or "Chroma 不可用")
        with self._lock:
            try:
                self.client.delete_collection(self.collection_name)
            except Exception:
                pass
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=None,
                metadata={
                    "hnsw:space": "cosine",
                    **embedding_identity(self.settings),
                },
            )
            self.error = ""
            self.rebuild_required = False
            if not chunks:
                return 0
            return self.index_chunks(chunks)

    def count(self) -> int:
        return int(self.collection.count()) if self.collection is not None else 0

    def snapshot(self) -> str | None:
        if not self.persist_dir.is_dir():
            return None
        root = self.settings.curriculum_snapshot_dir
        root.mkdir(parents=True, exist_ok=True)
        destination = root / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        with self._lock:
            shutil.copytree(self.persist_dir, destination)
        snapshots = sorted(
            [path for path in root.iterdir() if path.is_dir()],
            reverse=True,
        )
        for stale in snapshots[self.settings.curriculum_snapshot_keep :]:
            shutil.rmtree(stale, ignore_errors=True)
        return str(destination)

    def status(self) -> dict:
        dependency_ready = (
            importlib.util.find_spec("chromadb") is not None
            and not self.embedding_model.availability_error()
        )
        return {
            "enabled": self.settings.curriculum_vector_enabled,
            "required": self.settings.curriculum_vector_required,
            "available": self.available,
            "dependency_ready": dependency_ready,
            "provider": self.settings.curriculum_embedding_provider,
            "model": self.settings.curriculum_effective_embedding_model,
            "model_dir": str(self.settings.curriculum_embedding_model_dir),
            "device": self.settings.curriculum_embedding_device,
            "vector_dir": str(self.persist_dir),
            "collection": self.collection_name,
            "vector_count": self.count(),
            "rebuild_required": self.rebuild_required,
            "error": self.error,
        }

    @staticmethod
    def _id(chunk_id: int) -> str:
        return f"curriculum-chunk-{chunk_id}"
