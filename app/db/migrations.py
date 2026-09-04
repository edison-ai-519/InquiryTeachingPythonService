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
