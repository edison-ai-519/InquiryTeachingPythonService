from functools import lru_cache
from pathlib import Path

import yaml

from app.agents.models import AgentDefinition
from app.agents.prompt_loader import AgentPromptError, load_agent_prompt
from app.core.config import get_settings


AGENT_ID_ALIASES = {
    "insect_agent": "nature_agent",
}


class AgentRegistryError(RuntimeError):
    pass


class AgentRegistry:
    def __init__(self, config_path: Path):
        self.config_path = config_path.resolve()
        self._agents = self._load()

    def _load(self) -> dict[str, AgentDefinition]:
        if not self.config_path.is_file():
            raise AgentRegistryError(f"Agent 配置不存在：{self.config_path}")
        try:
            payload = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            raise AgentRegistryError(f"Agent 配置解析失败：{exc}") from exc
        items = payload.get("agents")
        if not isinstance(items, list) or not items:
            raise AgentRegistryError("Agent 配置必须包含非空 agents 列表")

        agents: dict[str, AgentDefinition] = {}
        for item in items:
            if not isinstance(item, dict):
                raise AgentRegistryError("Agent 配置项必须是对象")
            agent_id = str(item.get("id") or "").strip()
            if not agent_id:
                raise AgentRegistryError("Agent id 不能为空")
            if agent_id in agents:
                raise AgentRegistryError(f"Agent id 重复：{agent_id}")
            kind = str(item.get("kind") or "").strip()
            if kind not in {"main", "expert"}:
                raise AgentRegistryError(f"Agent {agent_id} 的 kind 无效：{kind}")
            capabilities = item.get("capabilities") or []
            if not isinstance(capabilities, list):
                raise AgentRegistryError(f"Agent {agent_id} 的 capabilities 必须是列表")
            agent = AgentDefinition(
                id=agent_id,
                kind=kind,
                name=str(item.get("name") or "").strip(),
                role=str(item.get("role") or "").strip(),
                description=str(item.get("description") or "").strip(),
                capabilities=tuple(
                    str(value).strip()
                    for value in capabilities
                    if str(value).strip()
                ),
                prompt_file=str(item.get("prompt_file") or "").strip(),
                selectable=bool(item.get("selectable", False)),
            )
            if not agent.name or not agent.role or not agent.prompt_file:
                raise AgentRegistryError(f"Agent {agent_id} 缺少 name、role 或 prompt_file")
            if agent.kind == "main" and agent.selectable:
                raise AgentRegistryError(f"主导师 {agent_id} 不能设为可选择专家")
            if agent.kind != "expert" and agent.selectable:
                raise AgentRegistryError("只有 expert 类型可设置 selectable")
            try:
                load_agent_prompt(agent)
            except AgentPromptError as exc:
                raise AgentRegistryError(str(exc)) from exc
            agents[agent_id] = agent

        main_agents = [agent for agent in agents.values() if agent.kind == "main"]
        if len(main_agents) != 1 or main_agents[0].id != "main_tutor":
            raise AgentRegistryError("必须且只能配置一个 id=main_tutor 的主导师")
        return agents

    def get(self, agent_id: str) -> AgentDefinition | None:
        canonical_id = AGENT_ID_ALIASES.get(agent_id, agent_id)
        return self._agents.get(canonical_id)

    def require(self, agent_id: str) -> AgentDefinition:
        agent = self.get(agent_id)
        if not agent:
            raise AgentRegistryError(f"Agent 不存在：{agent_id}")
        return agent

    def main_tutor(self) -> AgentDefinition:
        return self.require("main_tutor")

    def experts(self) -> list[AgentDefinition]:
        return [
            agent
            for agent in self._agents.values()
            if agent.kind == "expert" and agent.selectable
        ]

    def selectable_expert(self, agent_id: str) -> AgentDefinition | None:
        agent = self.get(agent_id)
        if not agent or agent.kind != "expert" or not agent.selectable:
            return None
        return agent


@lru_cache(maxsize=1)
def get_agent_registry() -> AgentRegistry:
    return AgentRegistry(get_settings().agent_config_path)
