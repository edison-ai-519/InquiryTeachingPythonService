import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import SessionModel, UserModel, UserWorkspaceRoleModel
from app.api.auth import update_workspace_roles
from app.schemas import WorkspaceRolesRequest
from app.services.auth_service import serialize_user
from app.services.session_access_service import (
    get_owned_workspace_session,
    resolve_workspace_role,
)


def make_user(role: str = "teacher") -> UserModel:
    return UserModel(
        id="user_workspace_test",
        username="workspace_test",
        password_hash="hash",
        is_admin=0,
        user_role=role,
        created_at="2026-10-12T00:00:00+00:00",
    )


def test_serialized_user_exposes_default_teacher_workspace_authorization():
    assert serialize_user(make_user())["workspace_roles"] == ["teacher"]


def test_serialized_user_exposes_study_travel_workspace_authorization():
    assert serialize_user(make_user("study_travel"))["workspace_roles"] == ["study_travel"]


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_workspace_context_rejects_ungranted_role(db):
    user = make_user()
    db.add(user)
    db.add(UserWorkspaceRoleModel(user_id=user.id, role_category="teacher", created_at=user.created_at))
    db.commit()

    with pytest.raises(HTTPException) as error:
        resolve_workspace_role(db, user, "study_travel")

    assert error.value.status_code == 403


def test_workspace_session_rejects_explicit_role_mismatch(db):
    user = make_user()
    db.add(user)
    db.add(UserWorkspaceRoleModel(user_id=user.id, role_category="teacher", created_at=user.created_at))
    db.add(UserWorkspaceRoleModel(user_id=user.id, role_category="study_travel", created_at=user.created_at))
    db.add(
        SessionModel(
            id="session_teacher",
            owner_user_id=user.id,
            title="teacher session",
            topic="topic",
            flow_name="inquiry_7_stage",
            role_category="teacher",
            created_at=user.created_at,
            updated_at=user.created_at,
        )
    )
    db.commit()

    with pytest.raises(HTTPException) as error:
        get_owned_workspace_session(db, "session_teacher", user, "study_travel")

    assert error.value.status_code == 404


def test_dual_workspace_user_must_supply_role_context(db):
    user = make_user()
    db.add(user)
    db.add(UserWorkspaceRoleModel(user_id=user.id, role_category="teacher", created_at=user.created_at))
    db.add(UserWorkspaceRoleModel(user_id=user.id, role_category="study_travel", created_at=user.created_at))
    db.add(
        SessionModel(
            id="session_travel",
            owner_user_id=user.id,
            title="travel session",
            topic="topic",
            flow_name="study_travel_4_stage",
            role_category="study_travel",
            created_at=user.created_at,
            updated_at=user.created_at,
        )
    )
    db.commit()

    with pytest.raises(HTTPException) as error:
        get_owned_workspace_session(db, "session_travel", user)

    assert error.value.status_code == 400


def test_admin_role_update_grants_both_workspaces(db):
    user = make_user()
    admin = UserModel(
        id="admin_workspace_test",
        username="admin_workspace_test",
        password_hash="hash",
        is_admin=1,
        user_role="teacher",
        created_at=user.created_at,
    )
    db.add_all([user, admin])
    db.add(UserWorkspaceRoleModel(user_id=user.id, role_category="teacher", created_at=user.created_at))
    db.commit()

    response = update_workspace_roles(
        user.id,
        WorkspaceRolesRequest(workspace_roles=["teacher", "study_travel"]),
        db,
        admin,
    )

    assert response["data"]["workspace_roles"] == ["study_travel", "teacher"]
    assert resolve_workspace_role(db, user, "study_travel") == "study_travel"
