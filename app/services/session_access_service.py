from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import SessionModel, UserWorkspaceRoleModel
from app.db.models import UserModel
from app.services.auth_service import workspace_roles_for_user


WORKSPACE_ROLES = {"teacher", "study_travel", "parent"}


def resolve_workspace_role(db: Session, user: UserModel, requested_role: str | None) -> str:
    granted_roles = workspace_roles_for_user(db, user)
    if requested_role is None:
        if len(granted_roles) != 1:
            raise HTTPException(status_code=400, detail="Workspace role is required")
        role = granted_roles[0]
    else:
        role = requested_role
    if role not in WORKSPACE_ROLES:
        raise HTTPException(status_code=400, detail="Invalid workspace role")
    if role not in granted_roles:
        raise HTTPException(status_code=403, detail="Workspace access denied")
    return role


def get_owned_workspace_session(
    db: Session,
    session_id: str,
    user: UserModel,
    requested_role: str | None = None,
) -> SessionModel:
    session = get_owned_session(db, session_id, user.id)
    role = resolve_workspace_role(db, user, requested_role)
    if session.role_category != role:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.role_category not in workspace_roles_for_user(db, user):
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def get_owned_session(db: Session, session_id: str, user_id: str) -> SessionModel:
    session = (
        db.query(SessionModel)
        .filter(
            SessionModel.id == session_id,
            SessionModel.owner_user_id == user_id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    has_workspace_access = (
        db.query(UserWorkspaceRoleModel)
        .filter(
            UserWorkspaceRoleModel.user_id == user_id,
            UserWorkspaceRoleModel.role_category == session.role_category,
        )
        .first()
    )
    if not has_workspace_access:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
