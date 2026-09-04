from fastapi import APIRouter, Depends

from app.agents.registry import get_agent_registry
from app.core.auth import get_current_user
from app.db.models import UserModel


router = APIRouter(prefix="/api/experts", tags=["experts"])


@router.get("")
def list_experts(_user: UserModel = Depends(get_current_user)):
    return {
        "code": 0,
        "message": "success",
        "data": [agent.public_dict() for agent in get_agent_registry().experts()],
    }
