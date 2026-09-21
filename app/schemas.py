from typing import Literal

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    topic: str = Field(min_length=1)
    flow_name: str = "inquiry_7_stage"


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class SelectFlowRequest(BaseModel):
    flow_name: str
    clear_messages: bool = True


class DraftModeRequest(BaseModel):
    enabled: bool


class DraftSelection(BaseModel):
    selected_text: str = ""
    start_offset: int = 0
    end_offset: int = 0
    stage_id: str = ""
    block_id: str | None = None


class GraphSelection(BaseModel):
    entity_ids: list[str] = Field(default_factory=list)
    relation_ids: list[str] = Field(default_factory=list)
    path_ids: list[str] = Field(default_factory=list)


class KnowledgeEntityRagSourcesRequest(BaseModel):
    sources: list[str] = Field(default_factory=list)


class KnowledgeEntityUpsertRequest(BaseModel):
    id: str | None = Field(default=None, min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    entity_type: str = Field(min_length=1, max_length=64)
    aliases: list[str] = Field(default_factory=list)
    description: str = Field(default="", max_length=2000)
    source: str = Field(default="", max_length=255)
    rag_sources: list[str] = Field(default_factory=list)


class KnowledgeRelationUpsertRequest(BaseModel):
    id: str | None = Field(default=None, min_length=1, max_length=128)
    subject_entity_id: str = Field(min_length=1, max_length=128)
    predicate: str = Field(min_length=1, max_length=128)
    object_entity_id: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=2000)
    evidence_source: str = Field(default="", max_length=255)
    confidence: str = Field(default="medium", pattern=r"^(high|medium|low)$")


class ChatRequest(BaseModel):
    type: Literal["chat", "sys_action"] = "chat"
    request_id: str | None = Field(default=None, min_length=1, max_length=128)
    message: str = ""
    action: Literal["next_stage", "prev_stage", "intro", "confirm_stage"] | None = None
    final_content: str | None = None
    expert_id: str | None = Field(default=None, min_length=1, max_length=128)
    draft_request_kind: Literal["generate", "edit"] | None = None
    selection: DraftSelection | None = None
    graph_selection: GraphSelection | None = None


class RollbackRequest(BaseModel):
    steps: int = Field(default=1, ge=1, le=20)
    stage_back: bool = False


class DraftUpdateRequest(BaseModel):
    draft_content: str


class DraftProposalActionItem(BaseModel):
    hunk_id: str
    action: Literal["accept", "reject"]


class DraftProposalActionRequest(BaseModel):
    actions: list[DraftProposalActionItem]


class ConfirmStageRequest(BaseModel):
    final_content: str


class ApiMessage(BaseModel):
    code: int = 0
    message: str = "success"
    data: dict | list | None = None
