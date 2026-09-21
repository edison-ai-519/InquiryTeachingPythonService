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
    heading_path = Column(Text, nullable=False, default="")
    article_number = Column(String, nullable=False, default="")
    chunk_type = Column(String, nullable=False, default="content")
    created_at = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("source", "source_index", name="uq_curriculum_source_index"),
    )


class CurriculumSourceModel(Base):
    __tablename__ = "curriculum_sources"

    source = Column(String, primary_key=True)
    id = Column(String, nullable=True, unique=True, index=True)
    category = Column(String, nullable=False, default="curriculum", index=True)
    title = Column(String, nullable=False, default="")
    policy_layer = Column(String, nullable=True, index=True)
    document_type = Column(String, nullable=False, default="reference", index=True)
    authority_scope = Column(String, nullable=False, default="", index=True)
    region_code = Column(String, nullable=False, default="", index=True)
    issuing_authority = Column(String, nullable=False, default="")
    document_number = Column(String, nullable=False, default="")
    source_url = Column(Text, nullable=False, default="")
    publish_date = Column(String, nullable=False, default="")
    effective_date = Column(String, nullable=False, default="")
    expiry_date = Column(String, nullable=False, default="")
    validity_status = Column(String, nullable=False, default="unknown", index=True)
    review_status = Column(String, nullable=False, default="draft", index=True)
    review_note = Column(Text, nullable=False, default="")
    reviewed_by_user_id = Column(String, nullable=False, default="")
    reviewed_at = Column(String, nullable=False, default="")
    last_verified_at = Column(String, nullable=False, default="")
    replaces_source_id = Column(String, nullable=False, default="", index=True)
    checksum = Column(String, nullable=False, default="")
    chunk_count = Column(Integer, nullable=False, default=0)
    vector_chunk_count = Column(Integer, nullable=False, default=0)
    vector_status = Column(String, nullable=False, default="pending")
    embedding_model = Column(String, nullable=False, default="")
    last_error = Column(Text, nullable=False, default="")
    updated_at = Column(String, nullable=False)

    __table_args__ = (
        Index(
            "ix_curriculum_sources_policy_filters",
            "category",
            "policy_layer",
            "region_code",
            "validity_status",
            "review_status",
        ),
    )


class KnowledgeSourceTopicModel(Base):
    __tablename__ = "knowledge_source_topics"

    source_id = Column(String, primary_key=True)
    topic_code = Column(String, primary_key=True)

    __table_args__ = (Index("ix_knowledge_source_topics_topic", "topic_code"),)


class KnowledgeSourceReviewEventModel(Base):
    __tablename__ = "knowledge_source_review_events"

    id = Column(String, primary_key=True)
    source_id = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)
    from_status = Column(String, nullable=False, default="")
    to_status = Column(String, nullable=False)
    note = Column(Text, nullable=False, default="")
    actor_user_id = Column(String, nullable=False)
    created_at = Column(String, nullable=False)


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
    origin = Column(String, nullable=False, default="manual", index=True)
    management_mode = Column(String, nullable=False, default="manual")
    extractor_model = Column(String, nullable=False, default="")
    extractor_version = Column(String, nullable=False, default="")
    last_auto_sync_at = Column(String, nullable=False, default="")
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)


class KnowledgeEntityTaxonModel(Base):
    __tablename__ = "knowledge_entity_taxa"

    authority = Column(String, primary_key=True)
    external_id = Column(String, primary_key=True)
    entity_id = Column(
        String,
        ForeignKey("knowledge_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scientific_name = Column(String, nullable=False, default="", index=True)
    verbatim_name = Column(String, nullable=False, default="")
    taxon_rank = Column(String, nullable=False, default="")
    taxon_path = Column(Text, nullable=False, default="")
    taxon_path_ids = Column(Text, nullable=False, default="")
    common_names_json = Column(Text, nullable=False, default="[]")
    match_method = Column(String, nullable=False, default="external_id")
    match_confidence = Column(String, nullable=False, default="high")
    created_by_run_id = Column(String, nullable=False, default="", index=True)
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
    origin = Column(String, nullable=False, default="manual", index=True)
    management_mode = Column(String, nullable=False, default="manual")
    status = Column(String, nullable=False, default="active", index=True)
    extractor_model = Column(String, nullable=False, default="")
    extractor_version = Column(String, nullable=False, default="")
    last_auto_sync_at = Column(String, nullable=False, default="")
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "subject_entity_id",
            "predicate",
            "object_entity_id",
            name="uq_knowledge_relation_triple",
        ),
    )


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
    source = Column(String, nullable=False, default="")

    __table_args__ = (Index("ix_knowledge_mentions_source", "source"),)


class KnowledgeRelationEvidenceModel(Base):
    __tablename__ = "knowledge_relation_evidence"

    relation_id = Column(
        String,
        ForeignKey("knowledge_relations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    chunk_id = Column(
        Integer,
        ForeignKey("curriculum_chunks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source = Column(String, nullable=False, default="")
    evidence_text = Column(Text, nullable=False, default="")
    created_at = Column(String, nullable=False)

    __table_args__ = (Index("ix_knowledge_relation_evidence_source", "source"),)


class EcologyGraphSyncJobModel(Base):
    __tablename__ = "ecology_graph_sync_jobs"

    id = Column(String, primary_key=True)
    source = Column(String, nullable=False, default="", index=True)
    source_checksum = Column(String, nullable=False, default="")
    operation = Column(String, nullable=False, default="sync")
    status = Column(String, nullable=False, default="queued", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    stats_json = Column(Text, nullable=False, default="{}")
    last_error = Column(Text, nullable=False, default="")
    lease_until = Column(String, nullable=False, default="")
    created_at = Column(String, nullable=False)
    started_at = Column(String, nullable=False, default="")
    finished_at = Column(String, nullable=False, default="")
    updated_at = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_ecology_graph_jobs_source_status", "source", "status"),
    )


class EcologyGraphSourceStateModel(Base):
    __tablename__ = "ecology_graph_source_states"

    source = Column(String, primary_key=True)
    source_checksum = Column(String, nullable=False, default="")
    lightrag_doc_id = Column(String, nullable=False, default="")
    status = Column(String, nullable=False, default="pending", index=True)
    last_job_id = Column(String, nullable=False, default="")
    entity_count = Column(Integer, nullable=False, default=0)
    relation_count = Column(Integer, nullable=False, default=0)
    rejected_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=False, default="")
    last_synced_at = Column(String, nullable=False, default="")
    updated_at = Column(String, nullable=False)


class GlobiImportRunModel(Base):
    __tablename__ = "globi_import_runs"

    id = Column(String, primary_key=True)
    version = Column(String, nullable=False, default="", index=True)
    source_url = Column(Text, nullable=False, default="")
    source_name = Column(String, nullable=False, default="")
    checksum = Column(String, nullable=False, default="", index=True)
    filter_json = Column(Text, nullable=False, default="{}")
    status = Column(String, nullable=False, default="queued", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    lease_until = Column(String, nullable=False, default="")
    total_rows = Column(Integer, nullable=False, default=0)
    candidate_rows = Column(Integer, nullable=False, default=0)
    accepted_rows = Column(Integer, nullable=False, default=0)
    rejected_rows = Column(Integer, nullable=False, default=0)
    created_entities = Column(Integer, nullable=False, default=0)
    updated_entities = Column(Integer, nullable=False, default=0)
    created_relations = Column(Integer, nullable=False, default=0)
    updated_relations = Column(Integer, nullable=False, default=0)
    stats_json = Column(Text, nullable=False, default="{}")
    started_at = Column(String, nullable=False, default="")
    finished_at = Column(String, nullable=False, default="")
    last_error = Column(Text, nullable=False, default="")
    created_by = Column(String, nullable=False, default="")
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)


class GlobiInteractionModel(Base):
    __tablename__ = "globi_interactions"

    id = Column(String, primary_key=True)
    import_run_id = Column(
        String,
        ForeignKey("globi_import_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_taxon_external_id = Column(String, nullable=False, default="")
    target_taxon_external_id = Column(String, nullable=False, default="")
    source_taxon_name = Column(String, nullable=False, default="")
    target_taxon_name = Column(String, nullable=False, default="")
    source_taxon_common_names = Column(Text, nullable=False, default="")
    target_taxon_common_names = Column(Text, nullable=False, default="")
    source_taxon_path = Column(Text, nullable=False, default="")
    target_taxon_path = Column(Text, nullable=False, default="")
    raw_interaction_type = Column(String, nullable=False, default="")
    normalized_predicate = Column(String, nullable=False, index=True)
    source_entity_id = Column(
        String,
        ForeignKey("knowledge_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_entity_id = Column(
        String,
        ForeignKey("knowledge_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    study_source_id = Column(String, nullable=False, default="")
    study_source_citation = Column(Text, nullable=False, default="")
    study_url = Column(Text, nullable=False, default="")
    study_doi = Column(String, nullable=False, default="")
    study_source_archive_uri = Column(Text, nullable=False, default="")
    locality = Column(Text, nullable=False, default="")
    latitude = Column(String, nullable=False, default="")
    longitude = Column(String, nullable=False, default="")
    event_date = Column(String, nullable=False, default="")
    source_last_seen_at = Column(String, nullable=False, default="")
    region_status = Column(String, nullable=False, default="global", index=True)
    record_hash = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(String, nullable=False)


class GlobiImportInteractionModel(Base):
    __tablename__ = "globi_import_interactions"

    import_run_id = Column(
        String,
        ForeignKey("globi_import_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    interaction_id = Column(
        String,
        ForeignKey("globi_interactions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(String, nullable=False)

    __table_args__ = (Index("ix_globi_import_interactions_interaction", "interaction_id"),)


class KnowledgeRelationGlobiEvidenceModel(Base):
    __tablename__ = "knowledge_relation_globi_evidence"

    relation_id = Column(
        String,
        ForeignKey("knowledge_relations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    interaction_id = Column(
        String,
        ForeignKey("globi_interactions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_knowledge_relation_globi_interaction", "interaction_id"),
    )
