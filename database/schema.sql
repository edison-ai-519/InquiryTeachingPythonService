-- InquiryTeachingPythonService - SQLite schema
-- Covers sessions, seven-stage outputs, messages, rollback turns,
-- RAG records, and file-level expert permissions.

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- Teaching-design session and workflow cursor.
CREATE TABLE IF NOT EXISTS sessions (
    id                  TEXT PRIMARY KEY,
    title               TEXT,
    topic               TEXT NOT NULL,
    flow_name           TEXT NOT NULL DEFAULT 'inquiry_7_stage',
    current_stage_index INTEGER NOT NULL DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'active',
    draft_mode_enabled  INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);

-- Draft and confirmed output for every stage in a session.
CREATE TABLE IF NOT EXISTS stage_outputs (
    id            TEXT PRIMARY KEY,
    session_id    TEXT NOT NULL,
    flow_name     TEXT NOT NULL,
    stage_id      TEXT NOT NULL,
    stage_name    TEXT NOT NULL,
    order_index   INTEGER NOT NULL,
    draft_content TEXT NOT NULL DEFAULT '',
    final_content TEXT NOT NULL DEFAULT '',
    confirmed     INTEGER NOT NULL DEFAULT 0 CHECK (confirmed IN (0, 1)),
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    CONSTRAINT uq_session_stage UNIQUE (session_id, stage_id),
    CONSTRAINT fk_stage_outputs_session
        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
);

-- Teacher, optional domain-expert, main-tutor, and legacy messages.
CREATE TABLE IF NOT EXISTS messages (
    id           TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL,
    stage_id     TEXT NOT NULL,
    role         TEXT NOT NULL,
    content      TEXT NOT NULL,
    agent_id     TEXT,
    message_type TEXT NOT NULL DEFAULT 'chat',
    created_at   TEXT NOT NULL,
    CONSTRAINT fk_messages_session
        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
);

-- Uploaded reference files scoped to one teaching session.
CREATE TABLE IF NOT EXISTS session_files (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    name            TEXT NOT NULL,
    extension       TEXT NOT NULL,
    mime_type       TEXT NOT NULL DEFAULT '',
    size_bytes      INTEGER NOT NULL DEFAULT 0,
    extracted_text  TEXT NOT NULL DEFAULT '',
    extracted_chars INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'processing',
    error_message   TEXT NOT NULL DEFAULT '',
    stored_path     TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    CONSTRAINT fk_session_files_session
        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
);

-- RAG request, retrieved context, and serialized source metadata.
CREATE TABLE IF NOT EXISTS rag_records (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    stage_id    TEXT NOT NULL,
    query       TEXT,
    context     TEXT,
    source_json TEXT,
    created_at  TEXT NOT NULL,
    CONSTRAINT fk_rag_records_session
        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
);

-- Locally imported curriculum-standard chunks used by BM25 retrieval.
CREATE TABLE IF NOT EXISTS curriculum_chunks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source       TEXT NOT NULL,
    source_index INTEGER NOT NULL,
    content      TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    CONSTRAINT uq_curriculum_source_index UNIQUE (source, source_index)
);

CREATE INDEX IF NOT EXISTS ix_curriculum_chunks_source
    ON curriculum_chunks (source);

-- Per-file ingestion and vector-index status.
CREATE TABLE IF NOT EXISTS curriculum_sources (
    source             TEXT PRIMARY KEY,
    checksum           TEXT NOT NULL DEFAULT '',
    chunk_count        INTEGER NOT NULL DEFAULT 0,
    vector_chunk_count INTEGER NOT NULL DEFAULT 0,
    vector_status      TEXT NOT NULL DEFAULT 'pending',
    embedding_model    TEXT NOT NULL DEFAULT '',
    last_error         TEXT NOT NULL DEFAULT '',
    updated_at         TEXT NOT NULL
);

-- Explicit file-level RAG access for selectable expert agents.
CREATE TABLE IF NOT EXISTS curriculum_source_agent_permissions (
    source     TEXT NOT NULL,
    agent_id   TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (source, agent_id),
    CONSTRAINT fk_curriculum_permission_source
        FOREIGN KEY (source) REFERENCES curriculum_sources (source) ON DELETE CASCADE
);

-- Knowledge graph nodes and their optional RAG knowledge-base bindings.
CREATE TABLE IF NOT EXISTS knowledge_entities (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    entity_type  TEXT NOT NULL,
    aliases_json TEXT NOT NULL DEFAULT '[]',
    description  TEXT NOT NULL DEFAULT '',
    source       TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_entity_sources (
    entity_id  TEXT NOT NULL,
    source     TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (entity_id, source),
    CONSTRAINT fk_knowledge_entity_sources_entity
        FOREIGN KEY (entity_id) REFERENCES knowledge_entities (id) ON DELETE CASCADE,
    CONSTRAINT fk_knowledge_entity_sources_source
        FOREIGN KEY (source) REFERENCES curriculum_sources (source) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_knowledge_entity_sources_source
    ON knowledge_entity_sources (source);

CREATE TABLE IF NOT EXISTS knowledge_relations (
    id                 TEXT PRIMARY KEY,
    subject_entity_id  TEXT NOT NULL,
    predicate          TEXT NOT NULL,
    object_entity_id   TEXT NOT NULL,
    description        TEXT NOT NULL DEFAULT '',
    evidence_source    TEXT NOT NULL DEFAULT '',
    confidence         TEXT NOT NULL DEFAULT 'medium',
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL,
    CONSTRAINT fk_knowledge_relations_subject
        FOREIGN KEY (subject_entity_id) REFERENCES knowledge_entities (id) ON DELETE CASCADE,
    CONSTRAINT fk_knowledge_relations_object
        FOREIGN KEY (object_entity_id) REFERENCES knowledge_entities (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_knowledge_relations_subject_entity_id
    ON knowledge_relations (subject_entity_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_relations_object_entity_id
    ON knowledge_relations (object_entity_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_relations_predicate
    ON knowledge_relations (predicate);

CREATE TABLE IF NOT EXISTS knowledge_entity_mentions (
    entity_id  TEXT NOT NULL,
    chunk_id   INTEGER NOT NULL,
    source     TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (entity_id, chunk_id),
    CONSTRAINT fk_knowledge_mentions_entity
        FOREIGN KEY (entity_id) REFERENCES knowledge_entities (id) ON DELETE CASCADE,
    CONSTRAINT fk_knowledge_mentions_chunk
        FOREIGN KEY (chunk_id) REFERENCES curriculum_chunks (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_knowledge_mentions_source
    ON knowledge_entity_mentions (source);

-- One rollback unit per chat round. Message IDs are application-managed
-- references because rollback currently deletes messages before this row.
CREATE TABLE IF NOT EXISTS chat_turns (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id              TEXT NOT NULL,
    session_id           TEXT NOT NULL,
    stage_id             TEXT NOT NULL,
    user_message_id      TEXT NOT NULL,
    expert_message_id    TEXT,
    assistant_message_id TEXT NOT NULL,
    rag_record_id        TEXT,
    draft_before         TEXT NOT NULL DEFAULT '',
    draft_after          TEXT NOT NULL DEFAULT '',
    created_at           TEXT NOT NULL,
    CONSTRAINT fk_chat_turns_session
        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
);

-- Session timeline and stage lookup indexes.
CREATE INDEX IF NOT EXISTS ix_sessions_updated_at
    ON sessions (updated_at);

CREATE INDEX IF NOT EXISTS ix_stage_outputs_session_id
    ON stage_outputs (session_id);
CREATE INDEX IF NOT EXISTS ix_stage_outputs_stage_id
    ON stage_outputs (stage_id);
CREATE INDEX IF NOT EXISTS ix_stage_outputs_session_order
    ON stage_outputs (session_id, order_index);

CREATE INDEX IF NOT EXISTS ix_messages_session_id
    ON messages (session_id);
CREATE INDEX IF NOT EXISTS ix_messages_stage_id
    ON messages (stage_id);
CREATE INDEX IF NOT EXISTS ix_messages_session_created
    ON messages (session_id, created_at);

CREATE INDEX IF NOT EXISTS ix_session_files_session_id
    ON session_files (session_id);

CREATE INDEX IF NOT EXISTS ix_rag_records_session_id
    ON rag_records (session_id);
CREATE INDEX IF NOT EXISTS ix_rag_records_session_stage
    ON rag_records (session_id, stage_id);

CREATE INDEX IF NOT EXISTS ix_curriculum_permissions_agent_id
    ON curriculum_source_agent_permissions (agent_id);

CREATE UNIQUE INDEX IF NOT EXISTS ix_chat_turns_turn_id
    ON chat_turns (turn_id);
CREATE INDEX IF NOT EXISTS ix_chat_turns_session_id
    ON chat_turns (session_id);
CREATE INDEX IF NOT EXISTS ix_chat_turns_stage_id
    ON chat_turns (stage_id);
CREATE INDEX IF NOT EXISTS ix_chat_turns_session_id_desc
    ON chat_turns (session_id, id DESC);

COMMIT;
