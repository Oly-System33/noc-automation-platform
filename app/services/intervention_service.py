import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import (
    AuditLogRecord,
    CallFlowRecord,
    IncidentRecord,
    ProcessedEventRecord,
    ScheduledActionRecord,
)
from app.db.session import SessionLocal
from app.rules.rule_loader import rule_loader
from app.schemas.interventions import (
    InterventionItem,
    InterventionRunbook,
    InterventionSourceType,
    InterventionStatus,
)


class InterventionError(RuntimeError):
    code = "intervention_error"


class InterventionNotFound(InterventionError):
    code = "intervention_not_found"


class InterventionRetryNotSafe(InterventionError):
    code = "retry_not_safe"


class InterventionDataError(InterventionError):
    code = "interventions_unavailable"


class InterventionService:
    _ACTION_NAMES = {"jira", "calls", "email", "telegram", "teams"}
    _SAFE_MODES = {"delayed", "manual_approval", "immediate"}
    _SAFE_APPROVAL = {"never", "always", "no_oncall"}

    def __init__(
        self,
        session_factory=SessionLocal,
        loader=rule_loader,
        processing_timeout_minutes=10,
        now_provider=None,
    ):
        self._session_factory = session_factory
        self._loader = loader
        self.processing_timeout_minutes = processing_timeout_minutes
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    def list_interventions(self, limit=100):
        now = self._as_utc(self._now_provider())
        cutoff = now - timedelta(minutes=self.processing_timeout_minutes)
        session = self._session_factory()

        try:
            call_flows = (
                session.query(CallFlowRecord)
                .join(
                    IncidentRecord,
                    IncidentRecord.event_id == CallFlowRecord.event_id,
                )
                .filter(
                    CallFlowRecord.state == "manual_required",
                    IncidentRecord.current_status == "open",
                )
                .order_by(CallFlowRecord.id.desc())
                .limit(limit)
                .all()
            )
            scheduled_actions = (
                session.query(ScheduledActionRecord)
                .filter(
                    or_(
                        ScheduledActionRecord.state == "failed",
                        (
                            (ScheduledActionRecord.state == "processing")
                            & (ScheduledActionRecord.processing_started_at <= cutoff)
                        ),
                    )
                )
                .order_by(ScheduledActionRecord.id.desc())
                .limit(limit)
                .all()
            )
            processed_events = (
                session.query(ProcessedEventRecord)
                .filter(
                    or_(
                        ProcessedEventRecord.state == "failed",
                        (
                            (ProcessedEventRecord.state == "processing")
                            & (ProcessedEventRecord.processing_started_at <= cutoff)
                        ),
                    )
                )
                .order_by(ProcessedEventRecord.id.desc())
                .limit(limit)
                .all()
            )

            items = [
                self._to_item(
                    InterventionSourceType.CALL_FLOW, row, now, session
                )
                for row in call_flows
                if self._call_flow_is_current(row, session)
            ]
            items.extend(
                self._to_item(
                    InterventionSourceType.SCHEDULED_ACTION, row, now, session
                )
                for row in scheduled_actions
                if self._scheduled_is_current(row, now)
                and self._incident_is_open(row.event_id, session)
            )
            items.extend(
                self._to_item(
                    InterventionSourceType.PROCESSED_EVENT, row, now, session
                )
                for row in processed_events
                if self._processed_is_current(row, now)
                and self._incident_is_open(row.event_id, session)
            )
            items.sort(
                key=lambda item: (item.detected_at, item.intervention_id),
                reverse=True,
            )
            return items[:limit]
        except SQLAlchemyError as error:
            session.rollback()
            raise InterventionDataError() from error
        finally:
            session.close()

    def reject_retry(self, intervention_id):
        source_type, source_id = self._parse_id(intervention_id)
        session = self._session_factory()

        try:
            record = self._get_current(session, source_type, source_id)
            session.add(AuditLogRecord(
                event_id=record.event_id,
                level="WARNING",
                component="intervention_service",
                message="Unsafe intervention retry rejected",
                details={
                    "intervention_id": intervention_id,
                    "source_type": source_type.value,
                    "source_id": source_id,
                    "reason": "retry_not_safe",
                },
            ))
            session.commit()
        except InterventionNotFound:
            session.rollback()
            raise
        except SQLAlchemyError as error:
            session.rollback()
            raise InterventionDataError() from error
        finally:
            session.close()

        raise InterventionRetryNotSafe()

    def get_runbook(self, intervention_id):
        source_type, source_id = self._parse_id(intervention_id)
        session = self._session_factory()

        try:
            record = self._get_current(session, source_type, source_id)
            incident = (
                session.query(IncidentRecord)
                .filter(IncidentRecord.event_id == record.event_id)
                .order_by(IncidentRecord.updated_at.desc())
                .first()
            )
            runbook = self._build_runbook(
                intervention_id,
                source_type,
                record,
                incident,
            )
            session.add(AuditLogRecord(
                event_id=record.event_id,
                level="INFO",
                component="intervention_service",
                message="Intervention runbook viewed",
                details={
                    "intervention_id": intervention_id,
                    "source": runbook.source,
                },
            ))
            session.commit()
            return runbook
        except InterventionNotFound:
            session.rollback()
            raise
        except SQLAlchemyError as error:
            session.rollback()
            raise InterventionDataError() from error
        finally:
            session.close()

    def _build_runbook(self, intervention_id, source_type, record, incident):
        if source_type == InterventionSourceType.SCHEDULED_ACTION:
            actions = self._safe_actions(record.actions)
            pre_actions = self._safe_actions(record.pre_actions)
            if actions or pre_actions:
                return InterventionRunbook(
                    intervention_id=intervention_id,
                    source="persisted_action_plan",
                    actions=actions,
                    target=self._safe_target(record.target),
                    delay_minutes=self._persisted_delay(record),
                    execution_mode=self._allowed(record.execution_mode, self._SAFE_MODES),
                    approval_when=self._allowed(record.approval_when, self._SAFE_APPROVAL),
                    pre_actions=pre_actions,
                    pre_target=self._safe_target(record.pre_target),
                )

        client = self._first_value(
            getattr(incident, "client", None), record.client
        )
        host = self._first_value(getattr(incident, "host", None), record.host)
        trigger = self._first_value(
            getattr(incident, "trigger", None), getattr(record, "trigger", None)
        )
        trigger_group = self._first_value(
            getattr(incident, "trigger_group", None),
            getattr(record, "trigger_group", None),
        )

        if not client or not host:
            raise InterventionNotFound()

        try:
            if not trigger_group and trigger:
                trigger_group = self._loader.get_trigger_group(client, trigger)
            action = self._loader.get_action(client, host, trigger_group)
        except FileNotFoundError as error:
            raise InterventionNotFound() from error

        if not action:
            raise InterventionNotFound()

        actions = self._safe_actions(action.get("action"))
        pre_actions = self._safe_actions(action.get("pre_actions"))
        if not actions and not pre_actions:
            raise InterventionNotFound()

        return InterventionRunbook(
            intervention_id=intervention_id,
            source="current_runbook",
            warning="Current runbook; this may differ from the historical plan.",
            actions=actions,
            target=self._safe_target(action.get("target")),
            delay_minutes=self._safe_nonnegative_int(action.get("delay_minutes")),
            execution_mode=self._allowed(action.get("execution_mode"), self._SAFE_MODES),
            approval_when=self._allowed(action.get("approval_when"), self._SAFE_APPROVAL),
            pre_actions=pre_actions,
            pre_target=self._safe_target(action.get("pre_target")),
        )

    def _get_current(self, session, source_type, source_id):
        model = {
            InterventionSourceType.CALL_FLOW: CallFlowRecord,
            InterventionSourceType.SCHEDULED_ACTION: ScheduledActionRecord,
            InterventionSourceType.PROCESSED_EVENT: ProcessedEventRecord,
        }[source_type]
        record = session.get(model, source_id)
        now = self._as_utc(self._now_provider())

        if record is None:
            raise InterventionNotFound()
        if source_type == InterventionSourceType.CALL_FLOW:
            current = self._call_flow_is_current(record, session)
        elif source_type == InterventionSourceType.SCHEDULED_ACTION:
            current = self._scheduled_is_current(
                record, now
            ) and self._incident_is_open(record.event_id, session)
        else:
            current = self._processed_is_current(
                record, now
            ) and self._incident_is_open(record.event_id, session)
        if not current:
            raise InterventionNotFound()
        return record

    def _incident_is_open(self, event_id, session):
        return (
            session.query(IncidentRecord.id)
            .filter(
                IncidentRecord.event_id == event_id,
                IncidentRecord.current_status == "open",
            )
            .first()
            is not None
        )

    def _call_flow_is_current(self, record, session):
        if self._normalize(record.state) != "manual_required":
            return False
        return (
            session.query(IncidentRecord.id)
            .filter(
                IncidentRecord.event_id == record.event_id,
                IncidentRecord.current_status == "open",
            )
            .first()
            is not None
        )

    def _scheduled_is_current(self, record, now):
        state = self._normalize(record.state)
        return state == "failed" or (
            state == "processing"
            and self._is_stale(record.processing_started_at, now)
        )

    def _processed_is_current(self, record, now):
        state = self._normalize(record.state)
        return state == "failed" or (
            state == "processing"
            and self._is_stale(record.processing_started_at, now)
        )

    def _to_item(self, source_type, record, now, session):
        state = self._normalize(record.state)
        if source_type == InterventionSourceType.CALL_FLOW:
            status = InterventionStatus.MANUAL_REQUIRED
            detected_at = record.manual_required_at or record.updated_at or record.created_at
            failure_reason = "Manual call handling required"
            max_attempts = record.max_attempts
        elif state == "failed":
            status = InterventionStatus.FAILED
            detected_at = (
                getattr(record, "updated_at", None)
                or getattr(record, "processed_at", None)
                or record.created_at
            )
            failure_reason = (
                "Scheduled action failed"
                if source_type == InterventionSourceType.SCHEDULED_ACTION
                else "Event processing failed"
            )
            max_attempts = None
        else:
            status = InterventionStatus.STUCK
            detected_at = record.processing_started_at or record.created_at
            failure_reason = "Processing exceeded the safe timeout"
            max_attempts = None

        description = self._safe_description(getattr(record, "trigger", None))
        return InterventionItem(
            intervention_id=f"{source_type.value}:{record.id}",
            source_type=source_type,
            source_id=record.id,
            event_id=record.event_id,
            client=record.client,
            host=record.host,
            description=description,
            severity=getattr(record, "severity", None),
            status=status,
            detected_at=self._as_utc(detected_at or now),
            attempt_count=getattr(record, "attempt_count", None),
            max_attempts=max_attempts,
            runbook_available=self._runbook_is_available(
                source_type, record, session
            ),
            failure_reason=failure_reason,
        )

    def _runbook_is_available(self, source_type, record, session):
        incident = (
            session.query(IncidentRecord)
            .filter(IncidentRecord.event_id == record.event_id)
            .order_by(IncidentRecord.updated_at.desc())
            .first()
        )
        try:
            self._build_runbook(
                f"{source_type.value}:{record.id}",
                source_type,
                record,
                incident,
            )
        except InterventionNotFound:
            return False
        return True

    def _parse_id(self, value):
        match = re.fullmatch(r"(call_flow|scheduled_action|processed_event):([1-9]\d*)", value or "")
        if not match:
            raise InterventionNotFound()
        return InterventionSourceType(match.group(1)), int(match.group(2))

    def _safe_actions(self, value):
        if isinstance(value, str):
            values = value.split(",")
        elif isinstance(value, (list, tuple)):
            values = value
        else:
            return []
        return [
            normalized
            for item in values
            if isinstance(item, str)
            and (normalized := item.strip().lower()) in self._ACTION_NAMES
        ]

    def _safe_target(self, value):
        if not isinstance(value, str):
            return None
        value = value.strip()
        if not value or len(value) > 100:
            return None
        if re.search(r"@|https?://|\d{7,}|(?:token|secret|password|phone|email)", value, re.I):
            return None
        return value if re.fullmatch(r"[\w .:/-]+", value) else None

    def _safe_description(self, value):
        if not isinstance(value, str):
            return None
        value = re.sub(
            r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
            "[redacted]",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(r"https?://\S+", "[redacted]", value, flags=re.IGNORECASE)
        value = re.sub(r"(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)", "[redacted]", value)
        value = re.sub(
            r'''(["']?(?:password|passwd|secret|token|api[_-]?key)["']?'''
            r'''\s*[:=]\s*)(["']?)[^"',;\s}]+\2''',
            r"\1\2[redacted]\2",
            value,
            flags=re.IGNORECASE,
        )
        value = " ".join(value.split())[:500]
        return value or None

    def _persisted_delay(self, record):
        if record.scheduled_at is None or record.created_at is None:
            return None
        seconds = (self._as_utc(record.scheduled_at) - self._as_utc(record.created_at)).total_seconds()
        return max(0, round(seconds / 60))

    def _safe_nonnegative_int(self, value):
        if isinstance(value, bool):
            return None
        try:
            value = int(value)
        except (TypeError, ValueError):
            return None
        return value if value >= 0 else None

    def _allowed(self, value, allowed):
        value = self._normalize(value)
        return value if value in allowed else None

    def _is_stale(self, started_at, now):
        if started_at is None:
            return False
        cutoff = self._as_utc(now) - timedelta(minutes=self.processing_timeout_minutes)
        return self._as_utc(started_at) <= cutoff

    def _as_utc(self, value):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _normalize(self, value):
        return str(value).strip().lower() if value is not None else None

    def _first_value(self, *values):
        return next((value for value in values if value is not None and str(value).strip()), None)


intervention_service = InterventionService()
