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
    ) -> str:
        role_prompt = load_agent_prompt(agent)
        return f"""{role_prompt}

【你的身份】{agent.name} / {agent.role}
【课题】{topic}
【教学流】{flow_display_name}
【当前阶段】{stage["name"]}
【当前阶段目标】{stage["direction"]}

【跨阶段对话历史】
{dialog_history or "暂无历史对话。"}

【阶段与参考资料上下文】
{doc_input or "暂无阶段文档或可用参考资料。"}

【右侧现有草案】
{current_draft or "暂无草案。"}

【教师当前选中的草案内容】
{selection_text.strip() or "本轮无选区。"}

【本轮教师输入】
{user_message}

【本轮输出要求】
1. 直接以你的专业角色回答，不冒充主导师，也不接管完整教学流程。
2. 优先给出具体、可操作、适合当前教学阶段的专业建议。
3. 区分观察事实、合理推断和待验证结论；证据不足时明确说明。
4. 超出你的专业边界时停止推测，并建议教师改选更合适的专家。
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

        reply = (
            f"【{agent.role}】我会从{agent.description}的角度分析这个问题。"
            f"针对“{message}”，建议先明确现有观察或数据，再区分已知事实、可能解释和需要继续验证的部分。"
        )
        for index in range(0, len(reply), 12):
            await asyncio.sleep(0.01)
            yield reply[index : index + 12]
