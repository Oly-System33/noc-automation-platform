from app.db.base import Base
from app.db.models import (  # noqa: F401
    ActionRecord,
    AuditLogRecord,
    EventRecord,
    IncidentRecord,
    ScheduledActionRecord,
)
from app.db.session import DATABASE_URL, engine, sanitize_database_url


def init_db():

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    try:
        init_db()
    except Exception as e:
        print(
            "[ERROR] Database initialization failed | "
            f"database={sanitize_database_url(DATABASE_URL)} | error={e}"
        )
        raise SystemExit(1)

    print(
        "[DATABASE] Tables initialized successfully | "
        f"database={sanitize_database_url(DATABASE_URL)}"
    )
