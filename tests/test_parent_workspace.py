import asyncio
from types import SimpleNamespace

import pytest

from app.agents.registry import get_agent_registry
from app.agents.service import ExpertAgentService
from app.schemas import HomeContext, SessionCreate, WorkspaceRolesRequest
from app.services.session_access_service import WORKSPACE_ROLES
from app.services.prompt_service import PromptService
from app.workflow.flows import get_flow, list_flows


def test_parent_role_has_isolated_experts_and_main_tutor():
    registry = get_agent_registry()
    assert registry.main_tutor("parent").id == "parent_main_tutor"
    assert len(registry.experts("parent")) == 6
    assert registry.selectable_expert("parent_nature_agent", "parent")
    assert registry.selectable_expert("nature_agent", "parent") is None


def test_parent_child_expert_is_an_age_appropriate_curious_roleplay_agent():
    registry = get_agent_registry()
    child = registry.selectable_expert("parent_child_agent", "parent")

    assert child is not None
    assert child.name == "好奇的小朋友"
    assert registry.selectable_expert("parent_child_agent", "teacher") is None
    prompt = get_agent_registry().get("parent_child_agent")
    assert prompt is not None
    from app.agents.prompt_loader import load_agent_prompt

    instructions = load_agent_prompt(prompt)
    assert "三年级" in instructions
    assert "大自然" in instructions
    assert "好奇" in instructions
    assert "角色扮演" in instructions


def test_parent_consulting_experts_use_role_specific_prompts():
    registry = get_agent_registry()
    actual = {
        agent.id: agent.prompt_file
        for agent in registry.experts("parent")
        if agent.id != "parent_child_agent"
    }

    assert actual == {
        "parent_insect_agent": "prompts/parent_insect.md",
        "parent_nature_agent": "prompts/parent_nature.md",
        "parent_mathematics_agent": "prompts/parent_mathematics.md",
        "parent_safety_agent": "prompts/parent_safety.md",
        "parent_physics_agent": "prompts/parent_physics.md",
    }


def test_expert_prompt_builder_accepts_chat_role_category():
    parent_expert = get_agent_registry().require("parent_nature_agent")

    prompt = ExpertAgentService.build_prompt(
        agent=parent_expert,
        topic="阳台上的植物",
        flow_display_name="激发好奇心",
        stage={"name": "观察", "direction": "帮助孩子观察叶片变化"},
        dialog_history="",
        doc_input="",
        current_draft="",
        user_message="叶子为什么有的黄了？",
        role_category="parent",
    )

    assert "【家庭探究流程】激发好奇心" in prompt
    assert "【本轮家长输入】" in prompt
    assert "【家庭场景要求】" in prompt


def test_parent_child_expert_prompt_preserves_roleplay_instead_of_professional_advice():
    child = get_agent_registry().require("parent_child_agent")
    prompt = ExpertAgentService.build_prompt(
        agent=child,
        topic="雨后的蚯蚓",
        flow_display_name="激发好奇心",
        stage={"name": "观察", "direction": "培训家长观察自然现象"},
        dialog_history="家长：地上有几条蚯蚓。",
        doc_input="",
        current_draft="",
        user_message="你觉得它们为什么出来了？",
    )

    assert "【本轮输出要求】" in prompt
    assert "直接以孩子的口吻回应" in prompt
    assert "直接以你的专业角色回答，不冒充主导师" not in prompt
    assert "优先给出具体、可操作的" not in prompt
    assert "超出你的专业边界时停止推测" not in prompt


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


def test_parent_curiosity_column_has_a_scaffolded_curiosity_training_flow():
    parent_flows = {flow["name"]: flow for flow in list_flows("parent")}
    flow = parent_flows["parent_curiosity_inquiry"]

    assert flow["category"] == "好奇心专栏"
    assert flow["display_name"] == "激发好奇心"
    assert [stage["id"] for stage in flow["stages"]] == [
        "phenomenon_observation",
        "observation_detail",
        "child_questions",
        "possible_explanations",
        "safe_experiment",
        "evidence_and_conclusion",
        "parent_reflection",
    ]
    assert "不要直接给出答案" in flow["stages"][0]["direction"]
    assert "重复" in flow["stages"][4]["direction"]
    assert "证据" in flow["stages"][5]["direction"]
    assert "培训家长" in flow["description"]
    assert "parent_curiosity_inquiry" not in {
        item["name"] for item in list_flows("teacher")
    }
    assert "parent_teacher_curiosity_inquiry" not in {
        item["name"] for item in list_flows("parent")
    }


def test_teacher_curiosity_column_has_the_same_scaffold_in_a_classroom_context():
    teacher_flows = {flow["name"]: flow for flow in list_flows("teacher")}
    flow = teacher_flows["teacher_curiosity_inquiry"]

    assert flow["category"] == "好奇心专栏"
    assert flow["display_name"] == "激发好奇心"
    assert [stage["id"] for stage in flow["stages"]] == [
        "phenomenon_observation",
        "observation_detail",
        "child_questions",
        "possible_explanations",
        "safe_experiment",
        "evidence_and_conclusion",
        "parent_reflection",
    ]
    assert "学生" in flow["stages"][0]["direction"]
    assert "课堂" in flow["stages"][4]["direction"]
    assert "教师" in flow["stages"][6]["direction"]
    assert all("孩子" not in stage["direction"] for stage in flow["stages"])
    assert "parent_curiosity_inquiry" not in teacher_flows


def test_nature_museum_workflow_is_role_isolated_and_keeps_a_regular_hands_on_rhythm():
    parent_flows = {flow["name"]: flow for flow in list_flows("parent")}
    teacher_flows = {flow["name"]: flow for flow in list_flows("teacher")}
    parent = parent_flows["parent_nature_museum"]
    teacher = teacher_flows["teacher_nature_museum"]
    expected_stages = [
        "nature_spot_discovery",
        "nature_collect_and_sort",
        "nature_magnifier_observation",
        "nature_observation_sentence",
        "nature_card_layout",
        "nature_specimen_mounting",
        "nature_museum_sharing",
    ]

    for flow in (parent, teacher):
        assert flow["category"] == "好奇心专栏"
        assert flow["display_name"] == "我的自然博物馆"
        assert [stage["id"] for stage in flow["stages"]] == expected_stages
        for stage in flow["stages"]:
            direction = stage["direction"]
            assert "15分钟" in direction
            assert "动手" in direction
            assert "问题" in direction
            assert "下一步" in direction
            display_direction = stage["display_direction"]
            assert "15分钟" in display_direction
            assert "动手" in display_direction
            assert "问题" in display_direction
            assert "下一步" in display_direction

    assert "家长" in parent["stages"][0]["direction"]
    assert "小组" in teacher["stages"][0]["direction"]
    assert "受保护植物" in parent["stages"][1]["direction"]
    assert "受保护植物" in teacher["stages"][1]["direction"]
    assert "teacher_nature_museum" not in parent_flows
    assert "parent_teacher_nature_museum" not in parent_flows
    assert "parent_nature_museum" not in teacher_flows


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


def test_parent_guide_prompt_uses_the_parent_main_tutor():
    prompt = PromptService.build_guide_agent_prompt(
        topic="雨后的蚯蚓",
        flow_display_name="激发好奇心",
        stage={"name": "从现象开始观察", "direction": "先观察，不揭晓答案"},
        dialog_history="",
        doc_input="",
        role_category="parent",
    )

    assert "你服务的对象是家长" in prompt
    assert "【家庭探究流程】激发好奇心" in prompt
    assert "【本轮家长输入】" in prompt


def test_parent_child_expert_fallback_stays_in_child_role(monkeypatch):
    monkeypatch.setattr(
        "app.agents.service.get_settings",
        lambda: SimpleNamespace(llm_api_key=""),
    )
    child = get_agent_registry().require("parent_child_agent")

    async def collect_reply():
        return "".join([
            chunk async for chunk in ExpertAgentService.chat_stream(
                agent=child,
                system_prompt="ignored by no-key fallback",
                message="雨后地上有好多蚯蚓",
            )
        ])

    reply = asyncio.run(collect_reply())
    assert reply.startswith("咦")
    assert "专业建议" not in reply
