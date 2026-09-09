from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.db.database import Base


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    owner_user_id = Column(String, nullable=True, index=True)
    title = Column(String)
    topic = Column(String, nullable=False)
    flow_name = Column(String, nullable=False, default="inquiry_7_stage")
    current_stage_index = Column(Integer, default=0)
    status = Column(String, default="active")
    draft_mode_enabled = Column(Integer, default=0)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    username = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=False)
    is_admin = Column(Integer, nullable=False, default=0)
    created_at = Column(String, nullable=False)


class AuthSessionModel(Base):
    __tablename__ = "auth_sessions"

    id = Column(String, primary_key=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    expires_at = Column(String, nullable=False, index=True)
    created_at = Column(String, nullable=False)


class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False, index=True)
    stage_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    agent_id = Column(String)
    message_type = Column(String, default="chat")
    created_at = Column(String, nullable=False)


class SessionFileModel(Base):
    __tablename__ = "session_files"

    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    extension = Column(String, nullable=False)
    mime_type = Column(String, default="")
    size_bytes = Column(Integer, default=0)
    extracted_text = Column(Text, default="")
    extracted_chars = Column(Integer, default=0)
    status = Column(String, nullable=False, default="processing")
    error_message = Column(Text, default="")
    stored_path = Column(Text, nullable=False)
    created_at = Column(String, nullable=False)


class ChatTurnModel(Base):
    __tablename__ = "chat_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    turn_id = Column(String, nullable=False, unique=True, index=True)
    session_id = Column(String, nullable=False, index=True)
    stage_id = Column(String, nullable=False, index=True)
    user_message_id = Column(String, nullable=False)
    expert_message_id = Column(String)
    assistant_message_id = Column(String, nullable=False)
    rag_record_id = Column(String)
    draft_before = Column(Text, default="")
    draft_after = Column(Text, default="")
    created_at = Column(String, nullable=False)


class StageOutputModel(Base):
    __tablename__ = "stage_outputs"

    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False, index=True)
    flow_name = Column(String, nullable=False)
    stage_id = Column(String, nullable=False, index=True)
    stage_name = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False)
    draft_content = Column(Text, default="")
    final_content = Column(Text, default="")
    confirmed = Column(Integer, default=0)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("session_id", "stage_id", name="uq_session_stage"),
    )


class DraftProposalModel(Base):
    __tablename__ = "draft_proposals"

    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False, index=True)
    stage_id = Column(String, nullable=False, index=True)
    base_content = Column(Text, default="")
    candidate_content = Column(Text, default="")
    diff_json = Column(Text, nullable=False, default="[]")
    status = Column(String, nullable=False, default="pending")
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)


class RagRecordModel(Base):
    __tablename__ = "rag_records"

    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False, index=True)
    stage_id = Column(String, nullable=False)
    query = Column(Text)
    context = Column(Text)
    source_json = Column(Text)
    created_at = Column(String, nullable=False)


class CurriculumChunkModel(Base):
    __tablename__ = "curriculum_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, nullable=False, index=True)
    source_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("source", "source_index", name="uq_curriculum_source_index"),
    )


class CurriculumSourceModel(Base):
    __tablename__ = "curriculum_sources"

    source = Column(String, primary_key=True)
    checksum = Column(String, nullable=False, default="")
    chunk_count = Column(Integer, nullable=False, default=0)
    vector_chunk_count = Column(Integer, nullable=False, default=0)
    vector_status = Column(String, nullable=False, default="pending")
    embedding_model = Column(String, nullable=False, default="")
    last_error = Column(Text, nullable=False, default="")
    updated_at = Column(String, nullable=False)


class CurriculumSourceAgentPermissionModel(Base):
    __tablename__ = "curriculum_source_agent_permissions"

    source = Column(
        String,
        ForeignKey("curriculum_sources.source", ondelete="CASCADE"),
        primary_key=True,
    )
    agent_id = Column(String, primary_key=True)
    created_at = Column(String, nullable=False)

    __table_args__ = (Index("ix_curriculum_permissions_agent_id", "agent_id"),)


class KnowledgeEntitySourceModel(Base):
    __tablename__ = "knowledge_entity_sources"

    entity_id = Column(
        String,
        ForeignKey("knowledge_entities.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source = Column(
        String,
        ForeignKey("curriculum_sources.source", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(String, nullable=False)

    __table_args__ = (Index("ix_knowledge_entity_sources_source", "source"),)


class KnowledgeEntityModel(Base):
    __tablename__ = "knowledge_entities"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)
    aliases_json = Column(Text, nullable=False, default="[]")
    description = Column(Text, nullable=False, default="")
    source = Column(String, nullable=False, default="")
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)


class KnowledgeRelationModel(Base):
    __tablename__ = "knowledge_relations"

    id = Column(String, primary_key=True)
    subject_entity_id = Column(
        String,
        ForeignKey("knowledge_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    predicate = Column(String, nullable=False, index=True)
    object_entity_id = Column(
        String,
        ForeignKey("knowledge_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description = Column(Text, nullable=False, default="")
    evidence_source = Column(Text, nullable=False, default="")
    confidence = Column(String, nullable=False, default="medium")
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)


class KnowledgeEntityMentionModel(Base):
    __tablename__ = "knowledge_entity_mentions"

    entity_id = Column(
        String,
        ForeignKey("knowledge_entities.id", ondelete="CASCADE"),
        primary_key=True,
    )
    chunk_id = Column(
        Integer,
        ForeignKey("curriculum_chunks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source = Column(String, nullable=False, default="", index=True)

    __table_args__ = (Index("ix_knowledge_mentions_source", "source"),)
