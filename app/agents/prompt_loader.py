from pathlib import Path

from app.agents.models import AgentDefinition


AGENTS_DIR = Path(__file__).resolve().parent


class AgentPromptError(RuntimeError):
    pass


def load_agent_prompt(agent: AgentDefinition) -> str:
    prompt_path = (AGENTS_DIR / agent.prompt_file).resolve()
    if AGENTS_DIR not in prompt_path.parents:
        raise AgentPromptError(f"Agent {agent.id} 的提示词路径越界")
    if not prompt_path.is_file():
        raise AgentPromptError(f"Agent {agent.id} 的提示词不存在：{prompt_path}")
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise AgentPromptError(f"Agent {agent.id} 的提示词为空")
    return prompt
