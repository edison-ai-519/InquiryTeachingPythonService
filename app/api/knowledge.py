from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.agents.registry import get_agent_registry
from app.core.auth import get_admin_user, get_current_user
from app.db.database import get_db
from app.db.models import UserModel
from app.schemas import (
    KnowledgeEntityRagSourcesRequest,
    KnowledgeEntityUpsertRequest,
    KnowledgeRelationUpsertRequest,
)
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.session_access_service import get_owned_session
from app.workflow.flows import get_flow


router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class GraphCandidateRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(default="")
    expert_id: str | None = Field(default=None, max_length=128)


def _raise_graph_error(exc: Exception) -> None:
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise exc


@router.post("/graph/candidates")
def graph_candidates(
    payload: GraphCandidateRequest,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    sess = get_owned_session(db, payload.session_id, user.id)
    flow = get_flow(sess.flow_name)
    stage = (
        flow["stages"][sess.current_stage_index]
        if sess.current_stage_index < len(flow["stages"])
        else {}
    )
    if (
        payload.expert_id
        and get_agent_registry().selectable_expert(payload.expert_id) is None
    ):
        raise HTTPException(status_code=400, detail="未知或不可选择的专家 Agent")
    service = KnowledgeGraphService(db)
    data = service.find_candidate_graph(
        message=payload.message,
        expert_id=payload.expert_id or "",
        topic=sess.topic,
        stage=stage,
    )
    db.commit()
    return {"code": 0, "message": "success", "data": data}


@router.get("/graph")
def get_graph_for_admin(
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    service = KnowledgeGraphService(db)
    data = service.all_graph()
    if not data["entities"]:
        service.load_seed_graph()
        db.commit()
        data = service.all_graph()
    return {"code": 0, "message": "success", "data": data}


@router.post("/graph/entities")
def create_graph_entity(
    payload: KnowledgeEntityUpsertRequest,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    service = KnowledgeGraphService(db)
    try:
        entity = service.create_entity(**payload.model_dump())
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_graph_error(exc)
    return {"code": 0, "message": "graph entity created", "data": entity}


@router.put("/graph/entities/{entity_id}")
def update_graph_entity(
    entity_id: str,
    payload: KnowledgeEntityUpsertRequest,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    service = KnowledgeGraphService(db)
    try:
        entity = service.update_entity(entity_id, **payload.model_dump())
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_graph_error(exc)
    return {"code": 0, "message": "graph entity updated", "data": entity}


@router.delete("/graph/entities/{entity_id}")
def delete_graph_entity(
    entity_id: str,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    service = KnowledgeGraphService(db)
    try:
        service.delete_entity(entity_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_graph_error(exc)
    return {"code": 0, "message": "graph entity deleted", "data": None}


@router.put("/graph/entities/{entity_id}/rag-sources")
def replace_graph_entity_rag_sources(
    entity_id: str,
    payload: KnowledgeEntityRagSourcesRequest,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    service = KnowledgeGraphService(db)
    try:
        sources = service.replace_rag_sources(entity_id, payload.sources)
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_graph_error(exc)
    return {
        "code": 0,
        "message": "graph entity rag sources updated",
        "data": {"entity_id": entity_id, "sources": sources},
    }


@router.post("/graph/relations")
def create_graph_relation(
    payload: KnowledgeRelationUpsertRequest,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    service = KnowledgeGraphService(db)
    try:
        relation = service.create_relation(**payload.model_dump())
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_graph_error(exc)
    return {"code": 0, "message": "graph relation created", "data": relation}


@router.put("/graph/relations/{relation_id}")
def update_graph_relation(
    relation_id: str,
    payload: KnowledgeRelationUpsertRequest,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    service = KnowledgeGraphService(db)
    try:
        relation = service.update_relation(
            relation_id,
            **payload.model_dump(),
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_graph_error(exc)
    return {"code": 0, "message": "graph relation updated", "data": relation}


@router.delete("/graph/relations/{relation_id}")
def delete_graph_relation(
    relation_id: str,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    service = KnowledgeGraphService(db)
    try:
        service.delete_relation(relation_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_graph_error(exc)
    return {"code": 0, "message": "graph relation deleted", "data": None}


@router.get("/graph/evidence-chunks")
def graph_evidence_chunks(
    source: str = "",
    query: str = "",
    relation_id: str = "",
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    try:
        chunks = KnowledgeGraphService(db).evidence_chunks(
            source=source,
            query=query,
            relation_id=relation_id,
            limit=limit,
        )
    except Exception as exc:
        _raise_graph_error(exc)
    return {"code": 0, "message": "success", "data": chunks}


@router.post("/graph/rebuild-mentions")
def rebuild_graph_mentions(
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    service = KnowledgeGraphService(db)
    try:
        count = service.rebuild_all_mentions()
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_graph_error(exc)
    return {
        "code": 0,
        "message": "graph mentions rebuilt",
        "data": {"mention_count": count},
    }


@router.get("/graph/entities/{entity_id}/neighbors")
def graph_entity_neighbors(
    entity_id: str,
    hops: int = Query(1, ge=1, le=2),
    predicates: str = "",
    db: Session = Depends(get_db),
    _user: UserModel = Depends(get_current_user),
):
    predicate_list = [
        item.strip() for item in predicates.split(",") if item.strip()
    ]
    data = KnowledgeGraphService(db).expand_neighbors(
        entity_id,
        hops=hops,
        predicates=predicate_list or None,
    )
    return {"code": 0, "message": "success", "data": data}


@router.post("/graph/import")
def import_graph_json(
    payload: dict,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    try:
        data = KnowledgeGraphService(db).import_graph_json(payload)
        db.commit()
    except Exception as exc:
        db.rollback()
        _raise_graph_error(exc)
    return {
        "code": 0,
        "message": "knowledge graph imported",
        "data": data,
    }
