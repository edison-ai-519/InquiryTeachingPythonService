from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.agents.registry import get_agent_registry
from app.core.auth import get_admin_user, get_current_user
from app.db.database import get_db
from app.db.models import UserModel
from app.schemas import KnowledgeEntityRagSourcesRequest
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.session_access_service import get_owned_session
from app.workflow.flows import get_flow


router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class GraphCandidateRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(default="")
    expert_id: str | None = Field(default=None, max_length=128)


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
