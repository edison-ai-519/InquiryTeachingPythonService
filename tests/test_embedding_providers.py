import asyncio
import json
import sys
from importlib.machinery import ModuleSpec
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.core.config import Settings
from app.services import curriculum_vector_service as vectors
from app.services.ecology_lightrag_service import EcologyLightRagExtractor


def settings(provider="remote", **overrides):
    value = Settings()
    value.curriculum_embedding_provider = provider
    value.curriculum_embedding_api_base = "https://embedding.example/v1/"
    value.curriculum_embedding_api_model = "test-embedding"
    value.curriculum_embedding_api_key = "secret-test-key"
    value.curriculum_embedding_batch_size = 2
    for key, item in overrides.items():
        setattr(value, key, item)
    return value


def transport(monkeypatch, handler):
    client = httpx.Client
    monkeypatch.setattr(vectors.httpx, "Client", lambda **kw: client(
        transport=httpx.MockTransport(handler), **kw
    ))


def test_remote_batches_order_normalization_and_probe(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        body = json.loads(request.content)
        assert str(request.url) == "https://embedding.example/v1/embeddings"
        assert request.headers["authorization"] == "Bearer secret-test-key"
        assert body["model"] == "test-embedding"
        return httpx.Response(200, json={"data": [
            {"index": i, "embedding": [3, 4] if i == 0 else [0, 2]}
            for i in reversed(range(len(body["input"])))
        ]})

    transport(monkeypatch, handler)
    model = vectors.RemoteEmbeddingModel(settings())
    assert model.encode(["a", "b", " "]) == [[0.6, 0.8], [0, 1], [0.6, 0.8]]
    assert json.loads(calls[-1].content)["input"] == [" "]
    assert model.dimension == 2
    model.load()
    assert len(calls) == 2  # known dimension does not need a probe
    other = vectors.RemoteEmbeddingModel(settings())
    other.load()
    assert other.dimension == 2
    assert len(calls) == 3


def test_remote_no_key_and_no_local_dependencies(monkeypatch, tmp_path):
    def handler(request):
        assert "authorization" not in request.headers
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1, 0]}]})

    transport(monkeypatch, handler)
    monkeypatch.setattr(vectors, "get_local_embedding_model", Mock(side_effect=AssertionError))
    s = settings(curriculum_embedding_api_key="", curriculum_embedding_model_dir=tmp_path / "missing")
    model = vectors.get_embedding_model(s)
    assert model.availability_error() == ""
    assert model.encode(["test"]) == [[1, 0]]


@pytest.mark.parametrize("override", [
    {"curriculum_embedding_provider": "invalid"},
    {"curriculum_embedding_api_base": ""},
    {"curriculum_embedding_api_base": "https://user:secret@example.com"},
    {"curriculum_embedding_api_model": ""},
    {"curriculum_embedding_api_timeout_seconds": 0},
])
def test_invalid_remote_config(override):
    model = vectors.RemoteEmbeddingModel(settings(**override))
    assert model.availability_error()
    with pytest.raises(vectors.CurriculumVectorUnavailable):
        model.encode(["test"])


@pytest.mark.parametrize("data", [
    [],
    [{"index": 1, "embedding": [1]}],
    [{"index": 0, "embedding": []}],
    [{"index": 0, "embedding": [0, 0]}],
    [{"index": 0, "embedding": ["1"]}],
    [{"index": 0, "embedding": [True]}],
    [{"index": 0, "embedding": [1e309]}],
])
def test_invalid_response(monkeypatch, data):
    # Use raw JSON so non-finite values reach the client's validator.
    transport(monkeypatch, lambda r: httpx.Response(200, content=json.dumps({"data": data})))
    with pytest.raises(vectors.CurriculumVectorUnavailable, match="响应无效"):
        vectors.RemoteEmbeddingModel(settings()).encode(["test"])


@pytest.mark.parametrize("kind", ["401", "500", "timeout", "network", "invalid-json"])
def test_remote_errors_are_sanitized(monkeypatch, kind):
    def handler(request):
        if kind == "timeout":
            raise httpx.ReadTimeout("secret-test-key", request=request)
        if kind == "network":
            raise httpx.ConnectError("secret-test-key", request=request)
        if kind == "invalid-json":
            return httpx.Response(200, text="secret-test-key")
        return httpx.Response(int(kind), text="secret-test-key")

    transport(monkeypatch, handler)
    with pytest.raises(vectors.CurriculumVectorUnavailable) as exc:
        vectors.RemoteEmbeddingModel(settings()).encode(["test"])
    assert "secret-test-key" not in str(exc.value)


def test_dimension_change_is_rejected(monkeypatch):
    transport(monkeypatch, lambda r: httpx.Response(200, json={
        "data": [{"index": 0, "embedding": [1, 0, 0]}]
    }))
    model = vectors.RemoteEmbeddingModel(settings())
    model.dimension = 2
    with pytest.raises(vectors.CurriculumVectorUnavailable):
        model.encode(["test"])


def test_invalid_batch_does_not_cache_dimension(monkeypatch):
    transport(monkeypatch, lambda r: httpx.Response(200, json={"data": [
        {"index": 0, "embedding": [1, 0]},
        {"index": 0, "embedding": [1, 0]},
    ]}))
    model = vectors.RemoteEmbeddingModel(settings())
    with pytest.raises(vectors.CurriculumVectorUnavailable):
        model.encode(["first", "second"])
    assert model.dimension is None


def test_local_never_calls_http(monkeypatch):
    monkeypatch.setattr(vectors.httpx, "Client", Mock(side_effect=AssertionError))
    s = settings("local", curriculum_embedding_api_base="", curriculum_embedding_api_model="")
    model = vectors.get_embedding_model(s)
    assert isinstance(model, vectors.LocalEmbeddingModel)
    fake = Mock()
    fake.encode.return_value = [[1.0, 0.0]]
    monkeypatch.setattr(model, "_model", fake)
    assert model.encode(["test"]) == [[1, 0]]
    assert fake.encode.call_args.kwargs["normalize_embeddings"] is True


def store_with_metadata(monkeypatch, tmp_path, s, metadata):
    collection = Mock(metadata=metadata)
    collection.count.return_value = 1
    client = Mock()
    client.get_or_create_collection.return_value = collection
    fake_chroma = SimpleNamespace(
        __spec__=ModuleSpec("chromadb", loader=None),
        config=SimpleNamespace(Settings=Mock()),
        PersistentClient=Mock(return_value=client),
    )
    monkeypatch.setitem(sys.modules, "chromadb", fake_chroma)
    model = Mock()
    model.availability_error.return_value = ""
    s.curriculum_vector_dir = tmp_path
    s.curriculum_vector_enabled = True
    return vectors.CurriculumVectorStore(s, model), collection


def test_old_local_index_is_compatible(monkeypatch, tmp_path):
    s = settings("local")
    store, collection = store_with_metadata(monkeypatch, tmp_path, s, {
        "embedding_model": s.curriculum_embedding_model, "hnsw:space": "cosine"
    })
    assert store.available
    assert not store.rebuild_required
    store._validate_dimension(512)
    assert collection.modify.call_args.kwargs["metadata"]["hnsw:space"] == "cosine"


@pytest.mark.parametrize("change", ["provider", "model", "endpoint", "dimension"])
def test_index_changes_require_rebuild(monkeypatch, tmp_path, change):
    s = settings()
    metadata = {**vectors.embedding_identity(s), "embedding_dimension": 2}
    if change == "provider":
        metadata["embedding_provider"] = "local"
    elif change == "model":
        metadata["embedding_model"] = "old-model"
    elif change == "endpoint":
        metadata["embedding_endpoint"] = "old-endpoint"
    store, _ = store_with_metadata(monkeypatch, tmp_path, s, metadata)
    if change == "dimension":
        with pytest.raises(vectors.CurriculumVectorUnavailable):
            store._validate_dimension(3)
    assert store.rebuild_required
    assert not store.available
    with pytest.raises(vectors.CurriculumVectorUnavailable):
        store.embed_texts(["test"])


def test_lightrag_directory_identity_and_local_compatibility(tmp_path):
    s = settings("local", ecology_lightrag_dir=tmp_path)
    extractor = EcologyLightRagExtractor(s)
    local_path = extractor._working_dir("source", "checksum")
    assert local_path.parent.parent == tmp_path
    s.curriculum_embedding_provider = "remote"
    remote_path = extractor._working_dir("source", "checksum")
    assert remote_path != local_path
    assert remote_path.parent.parent.name.startswith("remote-")
    s.curriculum_embedding_api_model = "other"
    assert extractor._working_dir("source", "checksum") != remote_path
    s.curriculum_embedding_api_model = "test-embedding"
    s.curriculum_embedding_api_key = "rotated-key"
    assert extractor._working_dir("source", "checksum") == remote_path


def test_lightrag_uses_shared_remote_adapter(monkeypatch, tmp_path):
    from app.services import ecology_lightrag_service as ecology

    s = settings(ecology_lightrag_dir=tmp_path, llm_api_key="unused-chat-key")
    model = vectors.RemoteEmbeddingModel(s)
    factory = Mock(return_value=model)
    monkeypatch.setattr(ecology, "get_embedding_model", factory)
    transport(monkeypatch, lambda r: httpx.Response(200, json={
        "data": [{"index": 0, "embedding": [3, 4]}]
    }))
    attrs = {}

    def wrap(**kwargs):
        attrs.update(kwargs)
        return lambda fn: fn

    rag = SimpleNamespace(
        initialize_storages=AsyncMock(),
        ainsert=AsyncMock(),
        get_knowledge_graph=AsyncMock(return_value={"nodes": [], "edges": []}),
        finalize_storages=AsyncMock(),
    )

    def create_rag(**kwargs):
        async def insert(*args, **kw):
            result = await kwargs["embedding_func"](["ecology text"])
            assert result.shape == (1, 2)
            assert str(result.dtype) == "float32"
        rag.ainsert.side_effect = insert
        assert kwargs["working_dir"].startswith(str(tmp_path / "remote-"))
        return rag

    for name, module in {
        "lightrag": SimpleNamespace(LightRAG=create_rag),
        "lightrag.kg": SimpleNamespace(),
        "lightrag.kg.shared_storage": SimpleNamespace(initialize_pipeline_status=AsyncMock()),
        "lightrag.llm": SimpleNamespace(),
        "lightrag.llm.openai": SimpleNamespace(openai_complete_if_cache=AsyncMock()),
        "lightrag.utils": SimpleNamespace(wrap_embedding_func_with_attrs=wrap),
    }.items():
        monkeypatch.setitem(sys.modules, name, module)
    result = asyncio.run(EcologyLightRagExtractor(s).extract(
        source="source", checksum="checksum", chunks=["ecology text"]
    ))
    factory.assert_called_once_with(s)
    assert attrs["embedding_dim"] == 2
    assert attrs["model_name"] == "test-embedding"
    assert result.entities == {}
    rag.finalize_storages.assert_awaited_once()
