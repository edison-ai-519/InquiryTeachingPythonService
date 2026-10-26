import asyncio
from collections.abc import AsyncIterator

from app.agents.models import AgentDefinition
from app.agents.prompt_loader import load_agent_prompt
from app.core.config import get_settings
from app.services.llm_service import LLMService


class ExpertAgentService:
    @staticmethod
    def build_prompt(
        *,
        agent: AgentDefinition,
        topic: str,
        flow_display_name: str,
        stage: dict,
        dialog_history: str,
        doc_input: str,
        current_draft: str,
        user_message: str,
        selection_text: str = "",
        role_category: str | None = None,
    ) -> str:
        role_prompt = load_agent_prompt(agent)
        if agent.id == "parent_child_agent":
            return f"""{role_prompt}

【你的身份】{agent.name} / {agent.role}
【家长探究主题】{topic}
【当前对话阶段】{stage["name"]}

【对话历史】
{dialog_history or "暂无对话历史。"}

【家庭场景参考】
{doc_input or "暂无补充场景资料。仅根据家长实际提供的信息回应，不自行补造观察。"}

【家长本轮输入】
{user_message}

【本轮输出要求】
1. 以上主题、阶段和场景只用于理解对话，不改变你的虚构小朋友身份；不执行阶段目标中的“培训家长”等成人导师任务。
2. 直接以孩子的口吻回应，默认一至三句；分享一个真实感的观察、情绪或猜想即可，不必每次都提问。
3. 不讲专业课、不提供完整活动方案、不主动点评家长。只有家长明确要求暂停或评价时才退出角色。
4. 不把虚构情境说成真实经历；涉及风险时用孩子能理解的话请成人帮助。
"""
        workspace_role = role_category or agent.role_category
        is_parent = workspace_role == "parent"
        user_label = "家长" if is_parent else "基地人员" if workspace_role == "study_travel" else "教师"
        flow_label = "家庭探究流程" if is_parent else "研学流程" if workspace_role == "study_travel" else "教学流"
        scenario_section = (
            "【家庭场景要求】\n建议必须适合家庭实施，考虑孩子年龄、家庭空间、常见材料、可用时长和成人陪伴；鼓励孩子自主观察，明确安全边界和成人协助环节。\n"
            if is_parent else ""
        )
        advice_context = "适合家庭场景和阶段" if is_parent else "适合当前研学阶段" if workspace_role == "study_travel" else "适合当前教学阶段"
        return f"""{role_prompt}

【你的身份】{agent.name} / {agent.role}
【课题】{topic}
【{flow_label}】{flow_display_name}
【当前阶段】{stage["name"]}
【当前阶段目标】{stage["direction"]}

【跨阶段对话历史】
{dialog_history or "暂无历史对话。"}

【阶段与参考资料上下文】
{doc_input or "暂无阶段文档或可用参考资料。"}

【右侧现有草案】
{current_draft or "暂无草案。"}

【{user_label}当前选中的草案内容】
{selection_text.strip() or "本轮无选区。"}

【本轮{user_label}输入】
{user_message}

{scenario_section}

【本轮输出要求】
1. 直接以你的专业角色回答，不冒充主导师，也不接管完整教学流程。
2. 优先给出具体、可操作、{advice_context}的专业建议。
3. 区分观察事实、合理推断和待验证结论；证据不足时明确说明。
4. 超出你的专业边界时停止推测，并建议用户改选更合适的专家。
5. 不输出草案标记块，不编造物种、数据、课标条文或安全结论。
"""

    @staticmethod
    async def chat_stream(*, agent: AgentDefinition, system_prompt: str, message: str) -> AsyncIterator[str]:
        if get_settings().llm_api_key:
            async for text in LLMService.chat_stream(
                system_prompt,
                [],
                message,
                response_kind="expert",
            ):
                yield text
            return

        if agent.id == "parent_child_agent":
            reply = "咦，我还不太确定呢！我想先仔细看看你说的这个现象，再猜猜可能是怎么回事。你能告诉我它是什么样的吗？"
        else:
            reply = (
                f"【{agent.role}】我会从{agent.description}的角度分析这个问题。"
                f"针对“{message}”，建议先明确现有观察或数据，再区分已知事实、可能解释和需要继续验证的部分。"
            )
        for index in range(0, len(reply), 12):
            await asyncio.sleep(0.01)
            yield reply[index : index + 12]
