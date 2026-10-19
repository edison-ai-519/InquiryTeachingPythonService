import pytest

from app.agents.registry import get_agent_registry
from app.schemas import HomeContext, SessionCreate, WorkspaceRolesRequest
from app.services.session_access_service import WORKSPACE_ROLES
from app.services.prompt_service import PromptService
from app.workflow.flows import get_flow, list_flows


def test_parent_role_has_isolated_experts_and_main_tutor():
    registry = get_agent_registry()
    assert registry.main_tutor("parent").id == "parent_main_tutor"
    assert len(registry.experts("parent")) == 5
    assert registry.selectable_expert("parent_nature_agent", "parent")
    assert registry.selectable_expert("nature_agent", "parent") is None


def test_stone_buddha_ancient_road_workflows_are_role_specific():
    teacher_flows = {flow["name"]: flow for flow in list_flows("teacher")}
    parent_flows = {flow["name"]: flow for flow in list_flows("parent")}

    teacher = teacher_flows["stone_buddha_ancient_road_course"]
    parent = parent_flows["stone_buddha_ancient_road_home_inquiry"]

    assert teacher["display_name"] == "石佛岭古道跨学科课程实施"
    assert teacher["stage_count"] == 6
    assert [stage["id"] for stage in teacher["stages"]] == [
        "theme_and_course_goals",
        "field_observation_tasks",
        "classroom_model_experiment",
        "course_implementation_evidence",
        "evidence_analysis",
        "learning_outcomes_and_conservation",
    ]
    assert "不敲击" in teacher["stages"][1]["direction"]
    assert "重复" in teacher["stages"][2]["direction"]
    assert "部分支持" in teacher["stages"][4]["direction"]
    assert "证据不足" in teacher["stages"][4]["direction"]

    assert parent["display_name"] == "石佛岭古道主题家庭探究"
    assert parent["stage_count"] == 5
    assert [stage["id"] for stage in parent["stages"]] == [
        "home_inquiry_question",
        "home_model_activity",
        "home_materials_and_safety",
        "parent_child_observation",
        "home_findings_and_reflection",
    ]
    assert "居家" in parent["stages"][1]["direction"]
    assert "不能" in parent["stages"][4]["direction"]
    assert teacher["stages"] != parent["stages"]

    assert "stone_buddha_ancient_road_home_inquiry" not in teacher_flows
    assert "stone_buddha_ancient_road_course" not in parent_flows


def test_parent_household_context_is_optional_and_does_not_collect_identity():
    assert SessionCreate(topic="鸟类观察", role_category="parent").home_context is None
    context = HomeContext(child_age_grade="二年级", available_time="30分钟")
    assert context.child_age_grade == "二年级"
    assert "parent" in WorkspaceRolesRequest(workspace_roles=["parent"]).workspace_roles
    with pytest.raises(Exception):
        HomeContext(child_name="小明")


def test_parent_prompts_adapt_to_home_safety_and_child_agency():
    prompt = PromptService.build_draft_generate_prompt(
        topic="阳台上的植物", flow_display_name="家庭探究",
        stage={"name": "观察", "direction": "观察变化"}, dialog_history="",
        doc_input="家庭情况：阳台；基地资料：植物观察", role_category="parent",
    )
    assert "家庭实施步骤" in prompt
    assert "安全提醒" in prompt
    assert "家庭情况缺失" in prompt
    assert "基地资料" in prompt
