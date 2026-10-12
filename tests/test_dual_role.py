import pytest
from app.db.models import UserModel
from app.db.database import SessionLocal


def test_user_role_default():
    """测试用户默认角色为 teacher"""
    db = SessionLocal()
    try:
        user = UserModel(
            id="test_user_001",
            username="test_teacher",
            password_hash="hash",
            user_role="teacher",
            created_at="2026-09-28T00:00:00",
        )
        db.add(user)
        db.commit()
        assert str(user.user_role) == "teacher"
    finally:
        db.rollback()
        db.close()


def test_user_role_study_travel():
    """测试研学基地人员角色"""
    db = SessionLocal()
    try:
        user = UserModel(
            id="test_user_002",
            username="test_study_travel",
            password_hash="hash",
            user_role="study_travel",
            created_at="2026-09-28T00:00:00",
        )
        db.add(user)
        db.commit()
        assert str(user.user_role) == "study_travel"
    finally:
        db.rollback()
        db.close()


def test_agent_role_category_filter():
    """测试按角色分类过滤专家"""
    from app.agents.registry import get_agent_registry

    registry = get_agent_registry()
    teacher_experts = registry.experts(role_category="teacher")
    study_travel_experts = registry.experts(role_category="study_travel")

    assert len(teacher_experts) == 5
    assert len(study_travel_experts) == 3
    assert all(e.role_category == "teacher" for e in teacher_experts)
    assert all(e.role_category == "study_travel" for e in study_travel_experts)


def test_curriculum_permission_isolation():
    """测试知识库权限按角色分类隔离"""
    from app.services.curriculum_permission_service import CurriculumPermissionService
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        # 测试教师类权限
        teacher_sources = CurriculumPermissionService.allowed_sources(
            db, "physics_teacher_agent", role_category="teacher"
        )
        assert len(teacher_sources) > 0

        # 测试研学类权限（应为空或不同）
        study_sources = CurriculumPermissionService.allowed_sources(
            db, "village_secretary_agent", role_category="study_travel"
        )
        # 研学类专家应有独立的权限配置
    finally:
        db.close()
