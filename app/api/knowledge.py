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


def request_data(payload: BaseModel) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


@router.post("/graph/candidates")
def graph_candidates(
    payload: GraphCandidateRequest,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    sess = get_owned_session(db, payload.session_id, user.id)
    flow = get_flow(sess.flow_name)
    stage = flow["stages"][sess.current_stage_index] if sess.current_stage_index < len(flow["stages"]) else {}
    if payload.expert_id and get_agent_registry().selectable_expert(payload.expert_id) is None:
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
    return {"code": 0, "message": "success", "data": KnowledgeGraphService(db).all_graph()}


@router.delete("/graph")
def clear_graph_for_admin(
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    data = KnowledgeGraphService(db).clear_graph()
    db.commit()
    return {"code": 0, "message": "knowledge graph deleted", "data": data}


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
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "code": 0,
        "message": "graph entity rag sources updated",
        "data": {"entity_id": entity_id, "sources": sources},
    }


@router.post("/graph/entities")
def create_graph_entity(
    payload: KnowledgeEntityUpsertRequest,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    service = KnowledgeGraphService(db)
    try:
        data = service.create_entity(request_data(payload))
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"code": 0, "message": "graph entity created", "data": data}


@router.put("/graph/entities/{entity_id}")
def update_graph_entity(
    entity_id: str,
    payload: KnowledgeEntityUpsertRequest,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    service = KnowledgeGraphService(db)
    try:
        data = service.update_entity(entity_id, request_data(payload))
        db.commit()
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"code": 0, "message": "graph entity updated", "data": data}


@router.delete("/graph/entities/{entity_id}")
def delete_graph_entity(
    entity_id: str,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    try:
        data = KnowledgeGraphService(db).delete_entity(entity_id)
        db.commit()
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"code": 0, "message": "graph entity deleted", "data": data}


@router.post("/graph/relations")
def create_graph_relation(
    payload: KnowledgeRelationUpsertRequest,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    service = KnowledgeGraphService(db)
    try:
        data = service.create_relation(request_data(payload))
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"code": 0, "message": "graph relation created", "data": data}


@router.put("/graph/relations/{relation_id}")
def update_graph_relation(
    relation_id: str,
    payload: KnowledgeRelationUpsertRequest,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    service = KnowledgeGraphService(db)
    try:
        data = service.update_relation(relation_id, request_data(payload))
        db.commit()
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"code": 0, "message": "graph relation updated", "data": data}


@router.delete("/graph/relations/{relation_id}")
def delete_graph_relation(
    relation_id: str,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    try:
        KnowledgeGraphService(db).delete_relation(relation_id)
        db.commit()
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"code": 0, "message": "graph relation deleted", "data": None}


@router.get("/graph/entities/{entity_id}/neighbors")
def graph_entity_neighbors(
    entity_id: str,
    hops: int = Query(1, ge=1, le=2),
    predicates: str = "",
    db: Session = Depends(get_db),
    _user: UserModel = Depends(get_current_user),
):
    predicate_list = [item.strip() for item in predicates.split(",") if item.strip()]
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
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    return {"code": 0, "message": "knowledge graph imported", "data": data}


@router.post("/graph/import/preview")
def preview_graph_import(
    payload: dict,
    db: Session = Depends(get_db),
    _admin: UserModel = Depends(get_admin_user),
):
    return {
        "code": 0,
        "message": "knowledge graph import preview",
        "data": KnowledgeGraphService(db).preview_import_graph_json(payload),
    }
