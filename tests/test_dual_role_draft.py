import pytest
from app.services.prompt_service import PromptService


def test_draft_prompt_teacher():
    """测试教师类草案提示词"""
    prompt = PromptService.build_draft_generate_prompt(
        topic="光的反射",
        flow_display_name="七阶段科学探究流",
        stage={"name": "观察起点", "direction": "从真实现象切入"},
        dialog_history="",
        doc_input="",
        current_draft="",
        user_message="我想从镜子反光开始",
        role_category="teacher",
    )
    assert "教师输入" in prompt
    assert "教学流" in prompt
    assert "研学" not in prompt


def test_draft_prompt_study_travel():
    """测试研学类草案提示词"""
    prompt = PromptService.build_draft_generate_prompt(
        topic="昆虫旅馆",
        flow_display_name="研学探究流",
        stage={"name": "行前准备", "direction": "明确研学目标"},
        dialog_history="",
        doc_input="",
        current_draft="",
        user_message="想让学生观察昆虫栖息",
        role_category="study_travel",
    )
    assert "基地人员输入" in prompt
    assert "研学流程" in prompt
    assert "研学目标" in prompt
    assert "安全预案" in prompt


def test_draft_agent_prompt_teacher():
    """测试教师类草案 Agent 提示词"""
    prompt = PromptService.build_draft_agent_prompt(
        topic="光的反射",
        flow_display_name="七阶段科学探究流",
        stage={"name": "观察起点", "direction": "从真实现象切入"},
        guide_output="引导回复",
        dialog_history="",
        doc_input="",
        current_draft="",
        user_message="我想从镜子反光开始",
        role_category="teacher",
    )
    assert "教师输入" in prompt
    assert "教学设计" in prompt


def test_draft_agent_prompt_study_travel():
    """测试研学类草案 Agent 提示词"""
    prompt = PromptService.build_draft_agent_prompt(
        topic="昆虫旅馆",
        flow_display_name="研学探究流",
        stage={"name": "行前准备", "direction": "明确研学目标"},
        guide_output="引导回复",
        dialog_history="",
        doc_input="",
        current_draft="",
        user_message="想让学生观察昆虫栖息",
        role_category="study_travel",
    )
    assert "基地人员输入" in prompt
    assert "研学方案设计" in prompt


def test_guide_prompt_teacher():
    """测试教师类引导提示词"""
    prompt = PromptService.build_guide_agent_prompt(
        topic="光的反射",
        flow_display_name="七阶段科学探究流",
        stage={"name": "观察起点", "direction": "从真实现象切入"},
        dialog_history="",
        doc_input="",
        current_draft="",
        user_message="我想从镜子反光开始",
        role_category="teacher",
    )
    assert "教师" in prompt
    assert "教学流" in prompt


def test_guide_prompt_study_travel():
    """测试研学类引导提示词"""
    prompt = PromptService.build_guide_agent_prompt(
        topic="昆虫旅馆",
        flow_display_name="研学探究流",
        stage={"name": "行前准备", "direction": "明确研学目标"},
        dialog_history="",
        doc_input="",
        current_draft="",
        user_message="想让学生观察昆虫栖息",
        role_category="study_travel",
    )
    assert "基地人员" in prompt
    assert "研学流程" in prompt
