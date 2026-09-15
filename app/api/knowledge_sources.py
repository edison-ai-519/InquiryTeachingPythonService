from __future__ import annotations

import asyncio
import io
import json
import shutil
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.auth import get_admin_user, get_current_user
from app.core.config import get_settings
from app.db.database import get_db
from app.db.models import (
    CurriculumChunkModel,
    CurriculumSourceModel,
    KnowledgeSourceReviewEventModel,
    UserModel,
)
from app.services.curriculum_knowledge_service import (
    CurriculumFileError,
    CurriculumKnowledgeService,
    StructuredKnowledgeChunk,
    checksum_chunks,
    chunk_policy_text,
    chunk_text,
    normalize_knowledge_category,
    normalize_source,
    normalize_text,
    now_iso,
)
from app.services.curriculum_permission_service import CurriculumPermissionService
from app.services.knowledge_source_service import (
    AUTHORITY_SCOPES,
    DOCUMENT_TYPES,
    POLICY_LAYERS,
    REVIEW_STATUSES,
    TOPIC_CODES,
    VALIDITY_STATUSES,
    KnowledgeSourceService,
)


router = APIRouter(prefix="/api/knowledge/sources", tags=["knowledge-sources"])
KNOWLEDGE_ENTRY = "knowledge.json"
REVIEW_ENTRY = "review-manifest.json"
EXPORT_VERSION = 4


class ReviewRequest(BaseModel):
    action: str = Field(min_length=1, max_length=32)
    note: str = Field(default="", max_length=2000)


class MetadataRequest(BaseModel):
    metadata: dict = Field(default_factory=dict)


def _http_error(exc: Exception, status_code: int = 400) -> HTTPException:
    return HTTPException(status_code=status_code, detail=str(exc))


def _parse_metadata(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CurriculumFileError("metadata_json 不是有效 JSON") from exc
    if not isinstance(payload, dict):
        raise CurriculumFileError("metadata_json 必须是 JSON 对象")
    return payload


def _serialize(db: Session, row: CurriculumSourceModel, *, detail: bool = False) -> dict:
    result = KnowledgeSourceService(db).serialize(row, include_review_events=detail)
    result["allowed_expert_ids"] = CurriculumPermissionService.allowed_expert_ids(
        db, row.source
    )
    if detail and row.replaces_source_id:
        replaced = (
            db.query(CurriculumSourceModel)
            .filter(CurriculumSourceModel.id == row.replaces_source_id)
            .first()
        )
        result["replaces_source"] = (
            {"id": replaced.id, "title": replaced.title, "source": replaced.source}
            if replaced
            else None
        )
    result["replaced_by"] = [
        {"id": item.id, "title": item.title, "source": item.source}
        for item in db.query(CurriculumSourceModel)
        .filter(CurriculumSourceModel.replaces_source_id == row.id)
        .order_by(CurriculumSourceModel.publish_date.desc())
        .all()
    ] if detail else []
    return result


def _validate_filter(value: str | None, allowed: set[str], label: str) -> str | None:
    if value is None or not value.strip():
        return None
    normalized = value.strip().lower()
    if normalized not in allowed:
        raise HTTPException(status_code=400, detail=f"{label}无效")
    return normalized


def _original_path(source_id: str, source: str) -> Path:
    settings = get_settings()
    safe_source = CurriculumKnowledgeService.safe_source_name(source)
    return (settings.knowledge_source_dir / source_id / safe_source).resolve()


def _store_original(source_id: str, source: str, data: bytes) -> None:
    path = _original_path(source_id, source)
    root = get_settings().knowledge_source_dir.resolve()
    if root not in path.parents:
        raise CurriculumFileError("知识来源存储路径无效")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


@router.get("")
def list_sources(
    category: str | None = Query(default=None),
    policy_layer: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    authority_scope: str | None = Query(default=None),
    region_code: str | None = Query(default=None),
    validity_status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    document_type: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    try:
        normalized_category = normalize_knowledge_category(category)
    except CurriculumFileError as exc:
        raise _http_error(exc) from exc
    layer = _validate_filter(policy_layer, POLICY_LAYERS, "政策层次")
    scope = _validate_filter(authority_scope, AUTHORITY_SCOPES - {""}, "地域层级")
    validity = _validate_filter(validity_status, VALIDITY_STATUSES, "效力状态")
    review = _validate_filter(review_status, REVIEW_STATUSES, "审核状态")
    kind = _validate_filter(document_type, DOCUMENT_TYPES, "资料性质")
    normalized_topic = _validate_filter(topic, TOPIC_CODES, "主题标签")

    query = db.query(CurriculumSourceModel)
    if not bool(user.is_admin):
        query = query.filter(CurriculumSourceModel.review_status == "published")
    elif review:
        query = query.filter(CurriculumSourceModel.review_status == review)
    if normalized_category:
        query = query.filter(CurriculumSourceModel.category == normalized_category)
    if layer:
        query = query.filter(CurriculumSourceModel.policy_layer == layer)
    if scope:
        query = query.filter(CurriculumSourceModel.authority_scope == scope)
    if region_code:
        query = query.filter(CurriculumSourceModel.region_code == region_code.strip())
    if validity:
        query = query.filter(CurriculumSourceModel.validity_status == validity)
    if kind:
        query = query.filter(CurriculumSourceModel.document_type == kind)
    if normalized_topic:
        from app.db.models import KnowledgeSourceTopicModel

        query = query.join(
            KnowledgeSourceTopicModel,
            KnowledgeSourceTopicModel.source_id == CurriculumSourceModel.id,
        ).filter(KnowledgeSourceTopicModel.topic_code == normalized_topic)
    if q and q.strip():
        keyword = f"%{q.strip()}%"
        query = query.filter(
            or_(
                CurriculumSourceModel.title.like(keyword),
                CurriculumSourceModel.source.like(keyword),
                CurriculumSourceModel.document_number.like(keyword),
                CurriculumSourceModel.issuing_authority.like(keyword),
            )
        )
    rows = query.order_by(
        CurriculumSourceModel.publish_date.desc(),
        CurriculumSourceModel.updated_at.desc(),
    ).all()
    return {"code": 0, "message": "success", "data": [_serialize(db, row) for row in rows]}


@router.get("/export")
def export_sources(
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    try:
        normalized_category = normalize_knowledge_category(category)
    except CurriculumFileError as exc:
        raise _http_error(exc) from exc
    query = db.query(CurriculumSourceModel)
    if normalized_category:
        query = query.filter(CurriculumSourceModel.category == normalized_category)
    service = KnowledgeSourceService(db)
    source_items: list[dict] = []
    review_items: list[dict] = []
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for row in query.order_by(CurriculumSourceModel.source.asc()).all():
            chunks = (
                db.query(CurriculumChunkModel)
                .filter(CurriculumChunkModel.source == row.source)
                .order_by(CurriculumChunkModel.source_index.asc())
                .all()
            )
            metadata = service.serialize(row)
            metadata["allowed_expert_ids"] = CurriculumPermissionService.allowed_expert_ids(
                db, row.source
            )
            metadata["chunks"] = [
                {
                    "source_index": chunk.source_index,
                    "content": chunk.content,
                    "heading_path": chunk.heading_path or "",
                    "article_number": chunk.article_number or "",
                    "chunk_type": chunk.chunk_type or "content",
                }
                for chunk in chunks
            ]
            metadata["checksum"] = row.checksum
            metadata["review_events"] = service.review_events(row.id)
            source_items.append(metadata)
            review_items.append(
                {
                    "id": row.id,
                    "source_url": row.source_url or "",
                    "last_verified_at": row.last_verified_at or "",
                    "review_status": row.review_status or "draft",
                    "reviewed_by_user_id": row.reviewed_by_user_id or "",
                    "reviewed_at": row.reviewed_at or "",
                    "review_note": row.review_note or "",
                }
            )
            original = _original_path(row.id, row.source)
            if original.is_file():
                archive.write(original, f"files/{row.id}/{original.name}")
        payload = {
            "version": EXPORT_VERSION,
            "exported_at": now_iso(),
            "category_filter": normalized_category or "all",
            "sources": source_items,
        }
        archive.writestr(KNOWLEDGE_ENTRY, json.dumps(payload, ensure_ascii=False, indent=2))
        archive.writestr(REVIEW_ENTRY, json.dumps({"version": 1, "sources": review_items}, ensure_ascii=False, indent=2))
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{normalized_category or "all"}-knowledge-v4.zip"'},
    )


@router.post("/import")
async def import_sources(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    settings = get_settings()
    data = await file.read(settings.upload_max_file_bytes + 1)
    await file.close()
    if not data:
        raise HTTPException(status_code=400, detail="知识库导入包不能为空")
    if len(data) > settings.upload_max_file_bytes:
        raise HTTPException(status_code=413, detail="知识库导入包超过大小限制")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
            entry = KNOWLEDGE_ENTRY if KNOWLEDGE_ENTRY in names else "curriculum.json"
            if entry not in names:
                raise CurriculumFileError("导入包缺少 knowledge.json 或 curriculum.json")
            payload = json.loads(archive.read(entry).decode("utf-8"))
            version = int(payload.get("version", 0))
            if version not in {1, 2, 3, 4}:
                raise CurriculumFileError("不支持的知识库导入包版本")
            raw_sources = payload.get("sources")
            if not isinstance(raw_sources, list):
                raise CurriculumFileError("知识库导入包格式无效")
            prepared: list[
                tuple[
                    str,
                    str,
                    list[StructuredKnowledgeChunk],
                    str,
                    dict,
                    list[str],
                    list[str],
                    str,
                    list[dict],
                    bytes | None,
                ]
            ] = []
            seen: set[str] = set()
            for item in raw_sources:
                if not isinstance(item, dict):
                    raise CurriculumFileError("知识库导入包包含无效来源")
                source = normalize_source(str(item.get("source") or ""))
                if source in seen:
                    raise CurriculumFileError(f"知识库导入包包含重复来源：{source}")
                seen.add(source)
                category = normalize_knowledge_category(str(item.get("category") or "curriculum")) or "curriculum"
                chunk_items = item.get("chunks") or []
                if not isinstance(chunk_items, list) or not chunk_items:
                    raise CurriculumFileError(f"来源 {source} 缺少片段")
                chunks = [
                    StructuredKnowledgeChunk(
                        content=str(chunk.get("content") or ""),
                        heading_path=str(chunk.get("heading_path") or ""),
                        article_number=str(chunk.get("article_number") or ""),
                        chunk_type=str(chunk.get("chunk_type") or "content"),
                    )
                    for chunk in sorted(chunk_items, key=lambda value: int(value.get("source_index", 0)))
                    if isinstance(chunk, dict)
                ]
                if len(chunks) != len(chunk_items):
                    raise CurriculumFileError(f"来源 {source} 包含无效片段")
                actual_checksum = checksum_chunks([chunk.content for chunk in chunks])
                expected_checksum = str(item.get("checksum") or "")
                if expected_checksum and expected_checksum != actual_checksum:
                    raise CurriculumFileError(f"来源 {source} 的内容校验失败")
                metadata = dict(item) if version == 4 else {}
                metadata.pop("chunks", None)
                bundle_id = str(metadata.pop("id", "") or "")
                review_events = metadata.pop("review_events", [])
                if not isinstance(review_events, list) or any(
                    not isinstance(event, dict) for event in review_events
                ):
                    raise CurriculumFileError(f"来源 {source} 的审核记录格式无效")
                if category == "rural_revitalization" and version < 4:
                    metadata["review_status"] = "draft"
                topics = (item.get("topics") or []) if version == 4 else []
                if not isinstance(topics, list) or any(not isinstance(value, str) for value in topics):
                    raise CurriculumFileError(f"来源 {source} 的主题标签格式无效")
                expert_ids = CurriculumPermissionService.validate_expert_ids(item.get("allowed_expert_ids") or [])
                original_data = None
                if version == 4:
                    candidates = [name for name in names if name.startswith(f"files/{item.get('id')}/") and not name.endswith("/")]
                    if candidates:
                        original_data = archive.read(candidates[0])
                prepared.append(
                    (
                        source,
                        category,
                        chunks,
                        expected_checksum or actual_checksum,
                        metadata,
                        list(topics),
                        expert_ids,
                        bundle_id,
                        review_events,
                        original_data,
                    )
                )

        knowledge = CurriculumKnowledgeService(db, settings)
        metadata_service = KnowledgeSourceService(db)
        imported_chunks = 0
        for (
            source,
            category,
            chunks,
            checksum,
            metadata,
            topics,
            expert_ids,
            bundle_id,
            review_events,
            original_data,
        ) in prepared:
            imported_chunks += knowledge.ingest_chunks(source, chunks, checksum=checksum, category=category)
            row = db.get(CurriculumSourceModel, source)
            if version == 4:
                if bundle_id and bundle_id != row.id:
                    conflict = (
                        db.query(CurriculumSourceModel)
                        .filter(CurriculumSourceModel.id == bundle_id)
                        .first()
                    )
                    if conflict and conflict.source != source:
                        raise CurriculumFileError(f"来源 {source} 的稳定ID已被占用")
                    row.id = bundle_id
                metadata_service.update_metadata(row, metadata)
                metadata_service.replace_topics(row.id, topics)
                requested_status = str(metadata.get("review_status") or "draft")
                row.review_status = requested_status if requested_status in REVIEW_STATUSES else "draft"
                row.reviewed_by_user_id = str(metadata.get("reviewed_by_user_id") or "")
                row.reviewed_at = str(metadata.get("reviewed_at") or "")
                db.query(KnowledgeSourceReviewEventModel).filter(
                    KnowledgeSourceReviewEventModel.source_id == row.id
                ).delete(synchronize_session=False)
                for event in review_events:
                    db.add(
                        KnowledgeSourceReviewEventModel(
                            id=str(event.get("id") or uuid.uuid4().hex),
                            source_id=row.id,
                            action=str(event.get("action") or ""),
                            from_status=str(event.get("from_status") or ""),
                            to_status=str(event.get("to_status") or ""),
                            note=str(event.get("note") or ""),
                            actor_user_id=str(event.get("actor_user_id") or ""),
                            created_at=str(event.get("created_at") or now_iso()),
                        )
                    )
                if row.review_status == "published":
                    errors = metadata_service.publish_errors(row)
                    if errors:
                        raise CurriculumFileError(
                            f"来源 {source} 不满足发布条件：{'、'.join(errors)}"
                        )
            elif category == "rural_revitalization":
                row.review_status = "draft"
            CurriculumPermissionService.replace_permissions(db, source, expert_ids)
            if original_data is not None:
                _store_original(row.id, source, original_data)
        db.commit()
    except (CurriculumFileError, json.JSONDecodeError, zipfile.BadZipFile, ValueError, TypeError) as exc:
        db.rollback()
        raise _http_error(exc) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="知识库导入失败") from exc
    return {"code": 0, "message": "knowledge bundle imported", "data": {"source_count": len(prepared), "chunk_count": imported_chunks}}


@router.get("/{source_id}")
def get_source(
    source_id: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    try:
        row = KnowledgeSourceService(db).by_id(source_id)
    except LookupError as exc:
        raise _http_error(exc, 404) from exc
    if not bool(user.is_admin) and row.review_status != "published":
        raise HTTPException(status_code=404, detail="知识来源不存在")
    return {"code": 0, "message": "success", "data": _serialize(db, row, detail=True)}


@router.get("/{source_id}/chunks")
def get_source_chunks(
    source_id: str,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    try:
        row = KnowledgeSourceService(db).by_id(source_id)
    except LookupError as exc:
        raise _http_error(exc, 404) from exc
    if not bool(user.is_admin) and row.review_status != "published":
        raise HTTPException(status_code=404, detail="知识来源不存在")
    chunks = (
        db.query(CurriculumChunkModel)
        .filter(CurriculumChunkModel.source == row.source)
        .order_by(CurriculumChunkModel.source_index.asc())
        .all()
    )
    return {
        "code": 0,
        "message": "success",
        "data": [
            {
                "id": chunk.id,
                "source_index": chunk.source_index,
                "content": chunk.content,
                "heading_path": chunk.heading_path or "",
                "article_number": chunk.article_number or "",
                "chunk_type": chunk.chunk_type or "content",
            }
            for chunk in chunks
        ],
    }


@router.post("")
async def create_source(
    file: UploadFile = File(...),
    category: str = Form(default="curriculum"),
    metadata_json: str = Form(default="{}"),
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    settings = get_settings()
    try:
        source = CurriculumKnowledgeService.safe_source_name(file.filename or "")
        normalized_category = normalize_knowledge_category(category) or "curriculum"
        metadata = _parse_metadata(metadata_json)
        if db.get(CurriculumSourceModel, source):
            raise CurriculumFileError("同名知识来源已存在，请使用更新接口")
        data = await file.read(settings.upload_max_file_bytes + 1)
        if not data:
            raise CurriculumFileError("不能上传空文件")
        if len(data) > settings.upload_max_file_bytes:
            raise HTTPException(status_code=413, detail="单个文件超过大小限制")
        content = await asyncio.to_thread(CurriculumKnowledgeService.extract_bytes, source, data)
        CurriculumKnowledgeService(db, settings).ingest(source, content, category=normalized_category)
        row = db.get(CurriculumSourceModel, source)
        metadata_service = KnowledgeSourceService(db)
        metadata_service.update_metadata(row, metadata)
        metadata_service.replace_topics(row.id, metadata.get("topics") or [])
        row.review_status = "draft" if normalized_category == "rural_revitalization" else row.review_status
        _store_original(row.id, row.source, data)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except CurriculumFileError as exc:
        db.rollback()
        raise _http_error(exc) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="知识来源上传失败") from exc
    finally:
        await file.close()
    return {"code": 0, "message": "knowledge source created", "data": _serialize(db, row, detail=True)}


@router.patch("/{source_id}")
async def update_source(
    source_id: str,
    metadata_json: str = Form(default="{}"),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_admin_user),
):
    settings = get_settings()
    try:
        service = KnowledgeSourceService(db)
        row = service.by_id(source_id)
        metadata = _parse_metadata(metadata_json)
        original_data = None
        body_changed = False
        if file is not None:
            source = CurriculumKnowledgeService.safe_source_name(file.filename or "")
            if source != row.source:
                raise CurriculumFileError("更新正文时文件名必须与原来源一致")
            original_data = await file.read(settings.upload_max_file_bytes + 1)
            if not original_data:
                raise CurriculumFileError("不能上传空文件")
            if len(original_data) > settings.upload_max_file_bytes:
                raise HTTPException(status_code=413, detail="单个文件超过大小限制")
            content = await asyncio.to_thread(CurriculumKnowledgeService.extract_bytes, source, original_data)
            normalized_content = normalize_text(content)
            overlap = min(settings.curriculum_chunk_overlap, settings.curriculum_chunk_size - 1)
            prepared_chunks: list[str | StructuredKnowledgeChunk]
            if row.category == "rural_revitalization":
                prepared_chunks = chunk_policy_text(
                    normalized_content,
                    size=settings.curriculum_chunk_size,
                    overlap=overlap,
                )
            else:
                prepared_chunks = chunk_text(
                    normalized_content,
                    size=settings.curriculum_chunk_size,
                    overlap=overlap,
                )
            new_checksum = checksum_chunks(
                [
                    chunk.content if isinstance(chunk, StructuredKnowledgeChunk) else chunk
                    for chunk in prepared_chunks
                ]
            )
            body_changed = new_checksum != row.checksum
            if body_changed:
                CurriculumKnowledgeService(db, settings).ingest_chunks(
                    source,
                    prepared_chunks,
                    checksum=new_checksum,
                    category=row.category,
                )
                row = service.by_id(source_id)
                service.invalidate_publication(
                    row,
                    "content_update",
                    admin.id,
                    "正文更新后需重新审核",
                )
        service.update_metadata(row, metadata)
        if "topics" in metadata:
            service.replace_topics(row.id, metadata.get("topics") or [])
        if not body_changed and metadata:
            service.invalidate_publication(
                row,
                "metadata_update",
                admin.id,
                "元数据更新后需重新审核",
            )
        if original_data is not None:
            _store_original(row.id, row.source, original_data)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except CurriculumFileError as exc:
        db.rollback()
        raise _http_error(exc) from exc
    except LookupError as exc:
        db.rollback()
        raise _http_error(exc, 404) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="知识来源更新失败") from exc
    finally:
        if file is not None:
            await file.close()
    return {"code": 0, "message": "knowledge source updated", "data": _serialize(db, row, detail=True)}


@router.post("/{source_id}/review")
def review_source(
    source_id: str,
    payload: ReviewRequest,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_admin_user),
):
    try:
        service = KnowledgeSourceService(db)
        row = service.by_id(source_id)
        service.review(row, payload.action, admin.id, payload.note)
        db.commit()
    except CurriculumFileError as exc:
        db.rollback()
        raise _http_error(exc) from exc
    except LookupError as exc:
        db.rollback()
        raise _http_error(exc, 404) from exc
    return {"code": 0, "message": "knowledge source reviewed", "data": _serialize(db, row, detail=True)}


@router.delete("/{source_id}")
def delete_source(
    source_id: str,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    try:
        row = KnowledgeSourceService(db).by_id(source_id)
        source = row.source
        deleted = CurriculumKnowledgeService(db).delete_source(source)
        db.commit()
        directory = _original_path(source_id, source).parent
        root = get_settings().knowledge_source_dir.resolve()
        if directory.parent == root and directory.is_dir():
            shutil.rmtree(directory)
    except LookupError as exc:
        db.rollback()
        raise _http_error(exc, 404) from exc
    return {"code": 0, "message": "knowledge source deleted", "data": {"deleted_chunks": deleted}}
