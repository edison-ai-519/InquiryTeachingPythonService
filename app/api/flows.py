from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.db.database import get_db
from app.db.models import UserModel
from app.services.session_access_service import resolve_workspace_role
from app.workflow.flows import list_flows


router = APIRouter(prefix="/api/flows", tags=["flows"])


@router.get("")
def get_flows(
    role_category: str | None = None,
    user: UserModel = Depends(get_current_user),
    db = Depends(get_db),
):
    role_category = resolve_workspace_role(db, user, role_category)
    return {"code": 0, "message": "success", "data": list_flows(role_category)}
