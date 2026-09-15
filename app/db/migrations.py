import uuid

from sqlalchemy import inspect, text

from app.db.database import engine


def ensure_schema_compatibility() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    with engine.begin() as connection:
        if "chat_turns" in table_names:
            chat_turn_columns = {column["name"] for column in inspector.get_columns("chat_turns")}
            if "expert_message_id" not in chat_turn_columns:
                connection.execute(
                    text("ALTER TABLE chat_turns ADD COLUMN expert_message_id VARCHAR")
                )

        if "sessions" in table_names:
            session_columns = {column["name"] for column in inspector.get_columns("sessions")}
            if "draft_mode_enabled" not in session_columns:
                connection.execute(
                    text("ALTER TABLE sessions ADD COLUMN draft_mode_enabled INTEGER DEFAULT 0")
                )
            if "owner_user_id" not in session_columns:
                connection.execute(
                    text("ALTER TABLE sessions ADD COLUMN owner_user_id VARCHAR")
                )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_sessions_owner_user_id "
                    "ON sessions (owner_user_id)"
                )
            )

        if "users" in table_names:
            user_columns = {column["name"] for column in inspector.get_columns("users")}
            if "is_admin" not in user_columns:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
                )

        if "curriculum_sources" in table_names:
            curriculum_source_columns = {
                column["name"] for column in inspector.get_columns("curriculum_sources")
            }
            if "category" not in curriculum_source_columns:
                connection.execute(
                    text(
                        "ALTER TABLE curriculum_sources ADD COLUMN "
                        "category VARCHAR NOT NULL DEFAULT 'curriculum'"
                    )
                )
            source_column_definitions = {
                "id": "VARCHAR",
                "title": "VARCHAR NOT NULL DEFAULT ''",
                "policy_layer": "VARCHAR",
                "document_type": "VARCHAR NOT NULL DEFAULT 'reference'",
                "authority_scope": "VARCHAR NOT NULL DEFAULT ''",
                "region_code": "VARCHAR NOT NULL DEFAULT ''",
                "issuing_authority": "VARCHAR NOT NULL DEFAULT ''",
                "document_number": "VARCHAR NOT NULL DEFAULT ''",
                "source_url": "TEXT NOT NULL DEFAULT ''",
                "publish_date": "VARCHAR NOT NULL DEFAULT ''",
                "effective_date": "VARCHAR NOT NULL DEFAULT ''",
                "expiry_date": "VARCHAR NOT NULL DEFAULT ''",
                "validity_status": "VARCHAR NOT NULL DEFAULT 'unknown'",
                "review_status": "VARCHAR NOT NULL DEFAULT 'draft'",
                "review_note": "TEXT NOT NULL DEFAULT ''",
                "reviewed_by_user_id": "VARCHAR NOT NULL DEFAULT ''",
                "reviewed_at": "VARCHAR NOT NULL DEFAULT ''",
                "last_verified_at": "VARCHAR NOT NULL DEFAULT ''",
                "replaces_source_id": "VARCHAR NOT NULL DEFAULT ''",
            }
            for column_name, definition in source_column_definitions.items():
                if column_name not in curriculum_source_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE curriculum_sources ADD COLUMN "
                            f"{column_name} {definition}"
                        )
                    )

        if "curriculum_chunks" in table_names:
            curriculum_chunk_columns = {
                column["name"] for column in inspector.get_columns("curriculum_chunks")
            }
            chunk_column_definitions = {
                "heading_path": "TEXT NOT NULL DEFAULT ''",
                "article_number": "VARCHAR NOT NULL DEFAULT ''",
                "chunk_type": "VARCHAR NOT NULL DEFAULT 'content'",
            }
            for column_name, definition in chunk_column_definitions.items():
                if column_name not in curriculum_chunk_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE curriculum_chunks ADD COLUMN "
                            f"{column_name} {definition}"
                        )
                    )

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS curriculum_sources (
                    source VARCHAR PRIMARY KEY,
                    id VARCHAR,
                    category VARCHAR NOT NULL DEFAULT 'curriculum',
                    title VARCHAR NOT NULL DEFAULT '',
                    policy_layer VARCHAR,
                    document_type VARCHAR NOT NULL DEFAULT 'reference',
                    authority_scope VARCHAR NOT NULL DEFAULT '',
                    region_code VARCHAR NOT NULL DEFAULT '',
                    issuing_authority VARCHAR NOT NULL DEFAULT '',
                    document_number VARCHAR NOT NULL DEFAULT '',
                    source_url TEXT NOT NULL DEFAULT '',
                    publish_date VARCHAR NOT NULL DEFAULT '',
                    effective_date VARCHAR NOT NULL DEFAULT '',
                    expiry_date VARCHAR NOT NULL DEFAULT '',
                    validity_status VARCHAR NOT NULL DEFAULT 'unknown',
                    review_status VARCHAR NOT NULL DEFAULT 'draft',
                    review_note TEXT NOT NULL DEFAULT '',
                    reviewed_by_user_id VARCHAR NOT NULL DEFAULT '',
                    reviewed_at VARCHAR NOT NULL DEFAULT '',
                    last_verified_at VARCHAR NOT NULL DEFAULT '',
                    replaces_source_id VARCHAR NOT NULL DEFAULT '',
                    checksum VARCHAR NOT NULL DEFAULT '',
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    vector_chunk_count INTEGER NOT NULL DEFAULT 0,
                    vector_status VARCHAR NOT NULL DEFAULT 'pending',
                    embedding_model VARCHAR NOT NULL DEFAULT '',
                    last_error TEXT NOT NULL DEFAULT '',
                    updated_at VARCHAR NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_curriculum_sources_category "
                "ON curriculum_sources (category)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_curriculum_sources_id "
                "ON curriculum_sources (id)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_curriculum_sources_policy_filters "
                "ON curriculum_sources "
                "(category, policy_layer, region_code, validity_status, review_status)"
            )
        )
        existing_sources = connection.execute(
            text("SELECT source, id, category, title, review_status FROM curriculum_sources")
        ).mappings().all()
        for row in existing_sources:
            source_id = row["id"] or uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"knowledge-source:{row['source']}",
            ).hex
            review_status = row["review_status"] or "draft"
            if row["category"] != "rural_revitalization" and review_status == "draft":
                review_status = "published"
            connection.execute(
                text(
                    "UPDATE curriculum_sources SET id = :id, title = :title, "
                    "review_status = :review_status WHERE source = :source"
                ),
                {
                    "id": source_id,
                    "title": row["title"] or row["source"],
                    "review_status": review_status,
                    "source": row["source"],
                },
            )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS knowledge_source_topics (
                    source_id VARCHAR NOT NULL,
                    topic_code VARCHAR NOT NULL,
                    PRIMARY KEY (source_id, topic_code)
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_knowledge_source_topics_topic "
                "ON knowledge_source_topics (topic_code)"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS knowledge_source_review_events (
                    id VARCHAR PRIMARY KEY,
                    source_id VARCHAR NOT NULL,
                    action VARCHAR NOT NULL,
                    from_status VARCHAR NOT NULL DEFAULT '',
                    to_status VARCHAR NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    actor_user_id VARCHAR NOT NULL,
                    created_at VARCHAR NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_knowledge_source_review_events_source_id "
                "ON knowledge_source_review_events (source_id)"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS curriculum_source_agent_permissions (
                    source VARCHAR NOT NULL,
                    agent_id VARCHAR NOT NULL,
                    created_at VARCHAR NOT NULL,
                    PRIMARY KEY (source, agent_id),
                    FOREIGN KEY(source) REFERENCES curriculum_sources(source) ON DELETE CASCADE
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_curriculum_permissions_agent_id "
                "ON curriculum_source_agent_permissions (agent_id)"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS knowledge_entities (
                    id VARCHAR PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    entity_type VARCHAR NOT NULL,
                    aliases_json TEXT NOT NULL DEFAULT '[]',
                    description TEXT NOT NULL DEFAULT '',
                    source VARCHAR NOT NULL DEFAULT '',
                    created_at VARCHAR NOT NULL,
                    updated_at VARCHAR NOT NULL
                )
                """
            )
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_knowledge_entities_name ON knowledge_entities (name)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_knowledge_entities_entity_type ON knowledge_entities (entity_type)")
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS knowledge_entity_sources (
                    entity_id VARCHAR NOT NULL,
                    source VARCHAR NOT NULL,
                    created_at VARCHAR NOT NULL,
                    PRIMARY KEY (entity_id, source),
                    FOREIGN KEY(entity_id) REFERENCES knowledge_entities(id) ON DELETE CASCADE,
                    FOREIGN KEY(source) REFERENCES curriculum_sources(source) ON DELETE CASCADE
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_knowledge_entity_sources_source "
                "ON knowledge_entity_sources (source)"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS knowledge_relations (
                    id VARCHAR PRIMARY KEY,
                    subject_entity_id VARCHAR NOT NULL,
                    predicate VARCHAR NOT NULL,
                    object_entity_id VARCHAR NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    evidence_source TEXT NOT NULL DEFAULT '',
                    confidence VARCHAR NOT NULL DEFAULT 'medium',
                    created_at VARCHAR NOT NULL,
                    updated_at VARCHAR NOT NULL,
                    FOREIGN KEY(subject_entity_id) REFERENCES knowledge_entities(id) ON DELETE CASCADE,
                    FOREIGN KEY(object_entity_id) REFERENCES knowledge_entities(id) ON DELETE CASCADE
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_knowledge_relations_subject_entity_id "
                "ON knowledge_relations (subject_entity_id)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_knowledge_relations_object_entity_id "
                "ON knowledge_relations (object_entity_id)"
            )
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_knowledge_relations_predicate ON knowledge_relations (predicate)")
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS knowledge_entity_mentions (
                    entity_id VARCHAR NOT NULL,
                    chunk_id INTEGER NOT NULL,
                    source VARCHAR NOT NULL DEFAULT '',
                    PRIMARY KEY (entity_id, chunk_id),
                    FOREIGN KEY(entity_id) REFERENCES knowledge_entities(id) ON DELETE CASCADE,
                    FOREIGN KEY(chunk_id) REFERENCES curriculum_chunks(id) ON DELETE CASCADE
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_knowledge_mentions_source "
                "ON knowledge_entity_mentions (source)"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS knowledge_relation_evidence (
                    relation_id VARCHAR NOT NULL,
                    chunk_id INTEGER NOT NULL,
                    source VARCHAR NOT NULL DEFAULT '',
                    evidence_text TEXT NOT NULL DEFAULT '',
                    created_at VARCHAR NOT NULL,
                    PRIMARY KEY (relation_id, chunk_id),
                    FOREIGN KEY(relation_id) REFERENCES knowledge_relations(id) ON DELETE CASCADE,
                    FOREIGN KEY(chunk_id) REFERENCES curriculum_chunks(id) ON DELETE CASCADE
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_knowledge_relation_evidence_source "
                "ON knowledge_relation_evidence (source)"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    key VARCHAR PRIMARY KEY,
                    applied_at VARCHAR NOT NULL
                )
                """
            )
        )
        migration_key = "curriculum_agent_permissions_v1"
        applied = connection.execute(
            text("SELECT 1 FROM schema_migrations WHERE key = :key"),
            {"key": migration_key},
        ).first()
        if not applied:
            connection.execute(
                text(
                    """
                    INSERT OR IGNORE INTO curriculum_source_agent_permissions
                        (source, agent_id, created_at)
                    SELECT source, 'physics_teacher_agent', datetime('now')
                    FROM curriculum_sources
                    WHERE source = '义务教育物理课程标准（2022年版）.docx'
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT OR IGNORE INTO curriculum_source_agent_permissions
                        (source, agent_id, created_at)
                    SELECT source, 'mathematics_teacher_agent', datetime('now')
                    FROM curriculum_sources
                    WHERE source = '义务教育数学课程标准（2022年版）.docx'
                    """
                )
            )
            connection.execute(
                text(
                    "INSERT INTO schema_migrations (key, applied_at) "
                    "VALUES (:key, datetime('now'))"
                ),
                {"key": migration_key},
            )
