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
            unique_constraints = inspector.get_unique_constraints("users")
            unique_indexes = inspector.get_indexes("users")
            has_global_username_unique = any(
                constraint.get("column_names") == ["username"]
                for constraint in unique_constraints
            ) or any(
                index.get("unique") and index.get("column_names") == ["username"]
                for index in unique_indexes
            )
            has_role_username_unique = any(
                constraint.get("column_names") == ["username", "is_admin"]
                for constraint in unique_constraints
            ) or any(
                index.get("unique") and index.get("column_names") == ["username", "is_admin"]
                for index in unique_indexes
            )
            if has_global_username_unique and not has_role_username_unique:
                connection.execute(text("ALTER TABLE users RENAME TO users_legacy_unique_username"))
                connection.execute(
                    text(
                        """
                        CREATE TABLE users (
                            id VARCHAR PRIMARY KEY,
                            username VARCHAR NOT NULL,
                            password_hash TEXT NOT NULL,
                            is_admin INTEGER NOT NULL DEFAULT 0,
                            created_at VARCHAR NOT NULL,
                            CONSTRAINT uq_users_username_is_admin UNIQUE (username, is_admin)
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO users (id, username, password_hash, is_admin, created_at)
                        SELECT id, username, password_hash, is_admin, created_at
                        FROM users_legacy_unique_username
                        """
                    )
                )
                connection.execute(text("DROP TABLE users_legacy_unique_username"))
                connection.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_users_username ON users (username)")
                )

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS curriculum_sources (
                    source VARCHAR PRIMARY KEY,
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
