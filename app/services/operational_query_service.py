import logging
import os
import re
from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import AuditLogRecord
from app.db.session import SessionLocal
from app.rules.rule_loader import RUNBOOKS_PATH, rule_loader
from app.schemas.operational import (
    AuditLogItem,
    AuditLogListResponse,
    OperationalConfigurationResponse,
    RunbookOperationalConfiguration,
    WorkerOperationalConfiguration,
)
from app.services import scheduled_action_worker
from app.services.scheduled_action_worker import is_worker_enabled


logger = logging.getLogger(__name__)
SAFE_AUDIT_CONTEXT_KEYS = {
    "scheduled_action_id", "source_type", "source_id", "reason",
    "previous_state", "new_state", "state", "source", "execution_mode",
    "intervention_id", "duplicate", "attempt_count",
}


class OperationalQueryError(RuntimeError):
    pass


class OperationalQueryService:
    def __init__(self, session_factory=SessionLocal, now_provider=None):
        self._session_factory = session_factory
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    def list_audit_logs(
        self, *, limit=100, offset=0, search=None, level=None, component=None,
        event_id=None, created_from=None, created_to=None,
    ):
        session = None
        try:
            session = self._session_factory()
            query = session.query(AuditLogRecord)
            if search:
                pattern = f"%{self._escape_like(str(search).strip())}%"
                query = query.filter(or_(
                    AuditLogRecord.message.ilike(pattern, escape="\\"),
                    AuditLogRecord.component.ilike(pattern, escape="\\"),
                    AuditLogRecord.event_id.ilike(pattern, escape="\\"),
                ))
            if level:
                query = query.filter(AuditLogRecord.level == level)
            if component:
                query = query.filter(AuditLogRecord.component == component)
            if event_id:
                query = query.filter(AuditLogRecord.event_id == event_id)
            if created_from:
                query = query.filter(
                    AuditLogRecord.created_at >= self._as_utc(created_from)
                )
            if created_to:
                query = query.filter(
                    AuditLogRecord.created_at <= self._as_utc(created_to)
                )
            total = query.count()
            records = query.order_by(
                AuditLogRecord.created_at.desc(), AuditLogRecord.id.desc()
            ).offset(offset).limit(limit).all()
            return AuditLogListResponse(
                items=[self._audit_item(record) for record in records], total=total,
                limit=limit, offset=offset, generated_at=self._as_utc(self._now_provider()),
            )
        except SQLAlchemyError as error:
            if session is not None:
                session.rollback()
            logger.warning("Audit log query failed: %s", type(error).__name__)
            raise OperationalQueryError("audit_query_failed") from error
        finally:
            if session is not None:
                session.close()

    def get_configuration(self):
        worker = scheduled_action_worker.worker
        thread = scheduled_action_worker.worker_thread
        running = bool(thread and thread.is_alive())
        poll_interval = (
            worker.poll_interval
            if worker is not None
            else self._positive_int_env("SCHEDULED_ACTION_POLL_INTERVAL_SECONDS", 30)
        )
        batch_size = (
            worker.batch_size
            if worker is not None
            else self._positive_int_env("SCHEDULED_ACTION_BATCH_SIZE", 20)
        )
        processing_timeout = (
            worker.processing_timeout_minutes
            if worker is not None
            else self._positive_int_env(
                "SCHEDULED_ACTION_PROCESSING_TIMEOUT_MINUTES", 10
            )
        )
        max_attempts = (
            worker.max_attempts
            if worker is not None
            else self._positive_int_env("SCHEDULED_ACTION_MAX_ATTEMPTS", 3)
        )
        try:
            runbook_count = sum(1 for path in RUNBOOKS_PATH.glob("*.xlsx") if path.is_file())
            available = RUNBOOKS_PATH.is_dir() and runbook_count > 0
        except OSError:
            runbook_count = 0
            available = False
        return OperationalConfigurationResponse(
            generated_at=self._as_utc(self._now_provider()),
            worker=WorkerOperationalConfiguration(
                enabled=is_worker_enabled(), running=running,
                ready=(not is_worker_enabled()) or running,
                poll_interval_seconds=poll_interval, batch_size=batch_size,
                processing_timeout_minutes=processing_timeout,
                max_attempts=max_attempts,
            ),
            runbooks=RunbookOperationalConfiguration(
                available=available, count=runbook_count,
                cache_count=len(rule_loader.cache), last_reload=None,
            ),
        )

    def _audit_item(self, record):
        details = record.details if isinstance(record.details, dict) else {}
        context = {
            key: self._safe_context_value(value) for key, value in details.items()
            if key in SAFE_AUDIT_CONTEXT_KEYS
            and (value is None or isinstance(value, (str, int, bool)))
        }
        scheduled_action_id = context.get("scheduled_action_id")
        message = self._safe_text(record.message, 500) or "Audit event"
        return AuditLogItem(
            id=record.id, event_id=record.event_id,
            scheduled_action_id=scheduled_action_id if isinstance(scheduled_action_id, int) else None,
            level=self._safe_text(record.level, 50) or "UNKNOWN",
            component=self._safe_text(record.component, 100) or "unknown",
            operation=self._safe_text(record.message, 100) or "Audit event",
            message=message, context=context,
            created_at=self._as_utc(record.created_at),
        )

    def _safe_context_value(self, value):
        if not isinstance(value, str):
            return value
        return self._safe_text(value, 200)

    def _safe_text(self, value, max_length):
        if value is None:
            return None
        value = " ".join(str(value).split())
        value = re.sub(
            r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
            "***",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(r"https?://\S+", "***", value, flags=re.IGNORECASE)
        value = re.sub(
            r'''(["']?(?:token|password|secret|api[_-]?key)["']?'''
            r'''\s*[:=]\s*)(["']?)[^"',;\s}]+\2''',
            r"\1\2***\2",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(r"(?<!\w)\+?\d[\d ()-]{6,}\d(?!\w)", "***", value)
        return value[:max_length] or None

    def _positive_int_env(self, name, default):
        try:
            value = int(os.getenv(name, default))
        except (TypeError, ValueError):
            return default
        return value if value > 0 else default

    def _escape_like(self, value):
        return (
            value.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )

    def _as_utc(self, value):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


operational_query_service = OperationalQueryService()
