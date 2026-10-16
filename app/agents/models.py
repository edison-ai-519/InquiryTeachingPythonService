from dataclasses import dataclass
from typing import Literal


AgentKind = Literal["main", "expert"]


@dataclass(frozen=True)
class AgentDefinition:
    id: str
    kind: AgentKind
    name: str
    role: str
    description: str
    capabilities: tuple[str, ...]
    prompt_file: str
    selectable: bool = False
    role_category: str = "teacher"

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "role_category": self.role_category,
        }
