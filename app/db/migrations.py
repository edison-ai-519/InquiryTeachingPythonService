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

        if "knowledge_entities" in table_names:
            entity_columns = {
                column["name"] for column in inspector.get_columns("knowledge_entities")
            }
            entity_definitions = {
                "origin": "VARCHAR NOT NULL DEFAULT 'manual'",
                "management_mode": "VARCHAR NOT NULL DEFAULT 'manual'",
                "extractor_model": "VARCHAR NOT NULL DEFAULT ''",
                "extractor_version": "VARCHAR NOT NULL DEFAULT ''",
                "last_auto_sync_at": "VARCHAR NOT NULL DEFAULT ''",
            }
            for name, definition in entity_definitions.items():
                if name not in entity_columns:
                    connection.execute(
                        text(f"ALTER TABLE knowledge_entities ADD COLUMN {name} {definition}")
                    )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_knowledge_entities_origin "
                    "ON knowledge_entities (origin)"
                )
            )

        if "knowledge_relations" in table_names:
            relation_columns = {
                column["name"] for column in inspector.get_columns("knowledge_relations")
            }
            relation_definitions = {
                "origin": "VARCHAR NOT NULL DEFAULT 'manual'",
                "management_mode": "VARCHAR NOT NULL DEFAULT 'manual'",
                "status": "VARCHAR NOT NULL DEFAULT 'active'",
                "extractor_model": "VARCHAR NOT NULL DEFAULT ''",
                "extractor_version": "VARCHAR NOT NULL DEFAULT ''",
                "last_auto_sync_at": "VARCHAR NOT NULL DEFAULT ''",
            }
            for name, definition in relation_definitions.items():
                if name not in relation_columns:
                    connection.execute(
                        text(f"ALTER TABLE knowledge_relations ADD COLUMN {name} {definition}")
                    )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_knowledge_relations_origin "
                    "ON knowledge_relations (origin)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_knowledge_relations_status "
                    "ON knowledge_relations (status)"
                )
            )
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_knowledge_relation_triple "
                    "ON knowledge_relations "
                    "(subject_entity_id, predicate, object_entity_id)"
                )
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
                    origin VARCHAR NOT NULL DEFAULT 'manual',
                    management_mode VARCHAR NOT NULL DEFAULT 'manual',
                    extractor_model VARCHAR NOT NULL DEFAULT '',
                    extractor_version VARCHAR NOT NULL DEFAULT '',
                    last_auto_sync_at VARCHAR NOT NULL DEFAULT '',
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
            text("CREATE INDEX IF NOT EXISTS ix_knowledge_entities_origin ON knowledge_entities (origin)")
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
                    origin VARCHAR NOT NULL DEFAULT 'manual',
                    management_mode VARCHAR NOT NULL DEFAULT 'manual',
                    status VARCHAR NOT NULL DEFAULT 'active',
                    extractor_model VARCHAR NOT NULL DEFAULT '',
                    extractor_version VARCHAR NOT NULL DEFAULT '',
                    last_auto_sync_at VARCHAR NOT NULL DEFAULT '',
                    created_at VARCHAR NOT NULL,
                    updated_at VARCHAR NOT NULL,
                    FOREIGN KEY(subject_entity_id) REFERENCES knowledge_entities(id) ON DELETE CASCADE,
                    FOREIGN KEY(object_entity_id) REFERENCES knowledge_entities(id) ON DELETE CASCADE,
                    UNIQUE(subject_entity_id, predicate, object_entity_id)
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
            text("CREATE INDEX IF NOT EXISTS ix_knowledge_relations_origin ON knowledge_relations (origin)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_knowledge_relations_status ON knowledge_relations (status)")
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_knowledge_relation_triple "
                "ON knowledge_relations (subject_entity_id, predicate, object_entity_id)"
            )
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
                CREATE TABLE IF NOT EXISTS ecology_graph_sync_jobs (
                    id VARCHAR PRIMARY KEY,
                    source VARCHAR NOT NULL DEFAULT '',
                    source_checksum VARCHAR NOT NULL DEFAULT '',
                    operation VARCHAR NOT NULL DEFAULT 'sync',
                    status VARCHAR NOT NULL DEFAULT 'queued',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    stats_json TEXT NOT NULL DEFAULT '{}',
                    last_error TEXT NOT NULL DEFAULT '',
                    lease_until VARCHAR NOT NULL DEFAULT '',
                    created_at VARCHAR NOT NULL,
                    started_at VARCHAR NOT NULL DEFAULT '',
                    finished_at VARCHAR NOT NULL DEFAULT '',
                    updated_at VARCHAR NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_ecology_graph_jobs_source_status "
                "ON ecology_graph_sync_jobs (source, status)"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS ecology_graph_source_states (
                    source VARCHAR PRIMARY KEY,
                    source_checksum VARCHAR NOT NULL DEFAULT '',
                    lightrag_doc_id VARCHAR NOT NULL DEFAULT '',
                    status VARCHAR NOT NULL DEFAULT 'pending',
                    last_job_id VARCHAR NOT NULL DEFAULT '',
                    entity_count INTEGER NOT NULL DEFAULT 0,
                    relation_count INTEGER NOT NULL DEFAULT 0,
                    rejected_count INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT NOT NULL DEFAULT '',
                    last_synced_at VARCHAR NOT NULL DEFAULT '',
                    updated_at VARCHAR NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS knowledge_entity_taxa (
                    authority VARCHAR NOT NULL,
                    external_id VARCHAR NOT NULL,
                    entity_id VARCHAR NOT NULL,
                    scientific_name VARCHAR NOT NULL DEFAULT '',
                    verbatim_name VARCHAR NOT NULL DEFAULT '',
                    taxon_rank VARCHAR NOT NULL DEFAULT '',
                    taxon_path TEXT NOT NULL DEFAULT '',
                    taxon_path_ids TEXT NOT NULL DEFAULT '',
                    common_names_json TEXT NOT NULL DEFAULT '[]',
                    match_method VARCHAR NOT NULL DEFAULT 'external_id',
                    match_confidence VARCHAR NOT NULL DEFAULT 'high',
                    created_by_run_id VARCHAR NOT NULL DEFAULT '',
                    created_at VARCHAR NOT NULL,
                    updated_at VARCHAR NOT NULL,
                    PRIMARY KEY (authority, external_id),
                    FOREIGN KEY(entity_id) REFERENCES knowledge_entities(id) ON DELETE CASCADE
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_knowledge_entity_taxa_entity_id "
                "ON knowledge_entity_taxa (entity_id)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_knowledge_entity_taxa_scientific_name "
                "ON knowledge_entity_taxa (scientific_name)"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS globi_import_runs (
                    id VARCHAR PRIMARY KEY,
                    version VARCHAR NOT NULL DEFAULT '',
                    source_url TEXT NOT NULL DEFAULT '',
                    source_name VARCHAR NOT NULL DEFAULT '',
                    checksum VARCHAR NOT NULL DEFAULT '',
                    filter_json TEXT NOT NULL DEFAULT '{}',
                    status VARCHAR NOT NULL DEFAULT 'queued',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    lease_until VARCHAR NOT NULL DEFAULT '',
                    total_rows INTEGER NOT NULL DEFAULT 0,
                    candidate_rows INTEGER NOT NULL DEFAULT 0,
                    accepted_rows INTEGER NOT NULL DEFAULT 0,
                    rejected_rows INTEGER NOT NULL DEFAULT 0,
                    created_entities INTEGER NOT NULL DEFAULT 0,
                    updated_entities INTEGER NOT NULL DEFAULT 0,
                    created_relations INTEGER NOT NULL DEFAULT 0,
                    updated_relations INTEGER NOT NULL DEFAULT 0,
                    stats_json TEXT NOT NULL DEFAULT '{}',
                    started_at VARCHAR NOT NULL DEFAULT '',
                    finished_at VARCHAR NOT NULL DEFAULT '',
                    last_error TEXT NOT NULL DEFAULT '',
                    created_by VARCHAR NOT NULL DEFAULT '',
                    created_at VARCHAR NOT NULL,
                    updated_at VARCHAR NOT NULL
                )
                """
            )
        )
        globi_run_columns = {
            column["name"] for column in inspect(connection).get_columns("globi_import_runs")
        }
        if "attempts" not in globi_run_columns:
            connection.execute(
                text("ALTER TABLE globi_import_runs ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0")
            )
        if "lease_until" not in globi_run_columns:
            connection.execute(
                text("ALTER TABLE globi_import_runs ADD COLUMN lease_until VARCHAR NOT NULL DEFAULT ''")
            )
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_globi_import_runs_version ON globi_import_runs (version)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_globi_import_runs_status ON globi_import_runs (status)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_globi_import_runs_checksum ON globi_import_runs (checksum)"))
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS globi_interactions (
                    id VARCHAR PRIMARY KEY,
                    import_run_id VARCHAR NOT NULL,
                    source_taxon_external_id VARCHAR NOT NULL DEFAULT '',
                    target_taxon_external_id VARCHAR NOT NULL DEFAULT '',
                    source_taxon_name VARCHAR NOT NULL DEFAULT '',
                    target_taxon_name VARCHAR NOT NULL DEFAULT '',
                    source_taxon_common_names TEXT NOT NULL DEFAULT '',
                    target_taxon_common_names TEXT NOT NULL DEFAULT '',
                    source_taxon_path TEXT NOT NULL DEFAULT '',
                    target_taxon_path TEXT NOT NULL DEFAULT '',
                    raw_interaction_type VARCHAR NOT NULL DEFAULT '',
                    normalized_predicate VARCHAR NOT NULL,
                    source_entity_id VARCHAR NOT NULL,
                    target_entity_id VARCHAR NOT NULL,
                    study_source_id VARCHAR NOT NULL DEFAULT '',
                    study_source_citation TEXT NOT NULL DEFAULT '',
                    study_url TEXT NOT NULL DEFAULT '',
                    study_doi VARCHAR NOT NULL DEFAULT '',
                    study_source_archive_uri TEXT NOT NULL DEFAULT '',
                    locality TEXT NOT NULL DEFAULT '',
                    latitude VARCHAR NOT NULL DEFAULT '',
                    longitude VARCHAR NOT NULL DEFAULT '',
                    event_date VARCHAR NOT NULL DEFAULT '',
                    source_last_seen_at VARCHAR NOT NULL DEFAULT '',
                    region_status VARCHAR NOT NULL DEFAULT 'global',
                    record_hash VARCHAR NOT NULL UNIQUE,
                    created_at VARCHAR NOT NULL,
                    FOREIGN KEY(import_run_id) REFERENCES globi_import_runs(id) ON DELETE CASCADE,
                    FOREIGN KEY(source_entity_id) REFERENCES knowledge_entities(id) ON DELETE CASCADE,
                    FOREIGN KEY(target_entity_id) REFERENCES knowledge_entities(id) ON DELETE CASCADE
                )
                """
            )
        )
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_globi_interactions_run ON globi_interactions (import_run_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_globi_interactions_source_entity ON globi_interactions (source_entity_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_globi_interactions_target_entity ON globi_interactions (target_entity_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_globi_interactions_predicate ON globi_interactions (normalized_predicate)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_globi_interactions_region ON globi_interactions (region_status)"))
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS globi_import_interactions (
                    import_run_id VARCHAR NOT NULL,
                    interaction_id VARCHAR NOT NULL,
                    created_at VARCHAR NOT NULL,
                    PRIMARY KEY (import_run_id, interaction_id),
                    FOREIGN KEY(import_run_id) REFERENCES globi_import_runs(id) ON DELETE CASCADE,
                    FOREIGN KEY(interaction_id) REFERENCES globi_interactions(id) ON DELETE CASCADE
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_globi_import_interactions_interaction "
                "ON globi_import_interactions (interaction_id)"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS knowledge_relation_globi_evidence (
                    relation_id VARCHAR NOT NULL,
                    interaction_id VARCHAR NOT NULL,
                    created_at VARCHAR NOT NULL,
                    PRIMARY KEY (relation_id, interaction_id),
                    FOREIGN KEY(relation_id) REFERENCES knowledge_relations(id) ON DELETE CASCADE,
                    FOREIGN KEY(interaction_id) REFERENCES globi_interactions(id) ON DELETE CASCADE
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_knowledge_relation_globi_interaction "
                "ON knowledge_relation_globi_evidence (interaction_id)"
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
