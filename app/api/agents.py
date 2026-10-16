from fastapi import APIRouter, Depends

from app.agents.registry import get_agent_registry
from app.core.auth import get_current_user
from app.db.models import UserModel
from app.db.database import get_db
from app.services.session_access_service import resolve_workspace_role


router = APIRouter(prefix="/api/experts", tags=["experts"])


@router.get("")
def list_experts(
    role_category: str | None = None,
    user: UserModel = Depends(get_current_user),
    db = Depends(get_db),
):
    role_category = resolve_workspace_role(db, user, role_category)
    return {
        "code": 0,
        "message": "success",
        "data": [
            agent.public_dict()
            for agent in get_agent_registry().experts(role_category=role_category)
        ],
    }
