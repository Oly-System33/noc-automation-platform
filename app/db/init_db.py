from app.db.base import Base
from app.db.models import (  # noqa: F401
    ActionRecord,
    AuditLogRecord,
    CallAttemptRecord,
    CallFlowRecord,
    EventRecord,
    IncidentRecord,
    ProcessedEventRecord,
    ScheduledActionRecord,
)
from app.db.session import DATABASE_URL, engine, sanitize_database_url
from app.services.console import console
from sqlalchemy import text


def init_db():

    Base.metadata.create_all(bind=engine)

    with engine.begin() as connection:
        connection.execute(text(
            "ALTER TABLE scheduled_actions "
            "ADD COLUMN IF NOT EXISTS dedupe_key VARCHAR"
        ))
        connection.execute(text(
            "ALTER TABLE scheduled_actions "
            "ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMP WITH TIME ZONE"
        ))
        connection.execute(text(
            "ALTER TABLE scheduled_actions "
            "ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0"
        ))
        connection.execute(text(
            "ALTER TABLE scheduled_actions "
            "ADD COLUMN IF NOT EXISTS last_error TEXT"
        ))
        connection.execute(text(
            "ALTER TABLE scheduled_actions "
            "ADD COLUMN IF NOT EXISTS execution_mode VARCHAR"
        ))
        connection.execute(text(
            "ALTER TABLE scheduled_actions "
            "ADD COLUMN IF NOT EXISTS approval_when VARCHAR"
        ))
        connection.execute(text(
            "ALTER TABLE scheduled_actions "
            "ADD COLUMN IF NOT EXISTS pre_actions JSONB"
        ))
        connection.execute(text(
            "ALTER TABLE scheduled_actions "
            "ADD COLUMN IF NOT EXISTS pre_target VARCHAR"
        ))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS "
            "ix_scheduled_actions_state_scheduled_at "
            "ON scheduled_actions (state, scheduled_at)"
        ))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS "
            "ix_scheduled_actions_state_processing_started_at "
            "ON scheduled_actions (state, processing_started_at)"
        ))
        connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "uq_scheduled_actions_dedupe_key "
            "ON scheduled_actions (dedupe_key) "
            "WHERE dedupe_key IS NOT NULL"
        ))
        connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "uq_processed_events_event_status "
            "ON processed_events (event_id, zabbix_status)"
        ))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS "
            "ix_processed_events_state_processing_started_at "
            "ON processed_events (state, processing_started_at)"
        ))


if __name__ == "__main__":
    try:
        init_db()
    except Exception as e:
        print(
            f"[{console.level('ERROR')}] Database initialization failed | "
            f"database={sanitize_database_url(DATABASE_URL)} | error={e}"
        )
        raise SystemExit(1)

    print(
        f"[{console.green('DATABASE')}] Tables initialized successfully | "
        f"database={sanitize_database_url(DATABASE_URL)}"
    )
