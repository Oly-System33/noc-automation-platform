import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError

from app.db.models import (
    ActionRecord,
    CallFlowRecord,
    EventRecord,
    IncidentRecord,
    ProcessedEventRecord,
    ScheduledActionRecord,
)
from app.db.session import SessionLocal
from app.schemas.dashboard import (
    DashboardIncidentItem,
    DashboardIncidentListResponse,
    DashboardStatus,
    DashboardStatusCounts,
    DashboardSummaryResponse,
    resolve_dashboard_status,
)
from app.services.console import console


MAX_DASHBOARD_LIMIT = 500
MAX_ERROR_LENGTH = 500

SCHEDULED_ACTION_PRIORITY = {
    "failed": 1,
    "pending_approval": 2,
    "processing": 3,
    "paused": 4,
    "pending": 5,
    "cancelled": 6,
    "executed": 7,
}

CALL_FLOW_PRIORITY = {
    "manual_required": 0,
    "waiting_confirmation": 1,
    "retry_scheduled": 2,
    "calling": 3,
    "cancelled": 4,
    "confirmed": 5,
    "pending": 6,
}

PROCESSED_EVENT_PRIORITY = {
    "failed": 1,
    "processing": 2,
    "processed": 3,
}


class DashboardQueryError(RuntimeError):
    pass


class DashboardQueryService:

    def __init__(
        self,
        session_factory=SessionLocal,
        processing_timeout_minutes=10,
        now_provider=None,
    ):
        self._session_factory = session_factory
        self.processing_timeout_minutes = processing_timeout_minutes
        self._now_provider = now_provider or (
            lambda: datetime.now(timezone.utc)
        )

    def list_incidents(self, limit=100):
        limit = max(1, min(int(limit), MAX_DASHBOARD_LIMIT))
        generated_at, items, total = self._load_items(
            limit=limit,
            include_total=True,
        )

        return DashboardIncidentListResponse(
            items=items,
            total=total,
            generated_at=generated_at,
        )

    def get_summary(self):
        generated_at, items, _ = self._load_items(
            limit=None,
            include_total=False,
        )
        counts = {status.value: 0 for status in DashboardStatus}
        by_client = defaultdict(int)

        for item in items:
            counts[item.display_status.value] += 1
            client = str(item.client or "").strip() or "unknown"
            by_client[client] += 1

        return DashboardSummaryResponse(
            generated_at=generated_at,
            counts=DashboardStatusCounts(**counts),
            by_client=dict(sorted(by_client.items())),
            total=len(items),
        )

    def _load_items(self, limit, include_total):
        session = None
        generated_at = self._as_utc(self._now_provider())

        try:
            session = self._session_factory()
            incident_query = session.query(IncidentRecord)
            total = incident_query.count() if include_total else None
            incident_query = incident_query.order_by(
                IncidentRecord.updated_at.desc(),
                IncidentRecord.created_at.desc(),
                IncidentRecord.id.desc(),
            )

            if limit is not None:
                incident_query = incident_query.limit(limit)

            incidents = incident_query.all()

            if not incidents:
                return generated_at, [], total or 0

            event_ids = [incident.event_id for incident in incidents]
            events = self._query_by_event_ids(
                session,
                EventRecord,
                event_ids,
            )
            processed_events = self._query_by_event_ids(
                session,
                ProcessedEventRecord,
                event_ids,
            )
            scheduled_actions = self._query_by_event_ids(
                session,
                ScheduledActionRecord,
                event_ids,
            )
            call_flows = self._query_by_event_ids(
                session,
                CallFlowRecord,
                event_ids,
            )
            actions = self._query_by_event_ids(
                session,
                ActionRecord,
                event_ids,
            )

            grouped_events = self._group_by_event_id(events)
            grouped_processed = self._group_by_event_id(processed_events)
            grouped_scheduled = self._group_by_event_id(scheduled_actions)
            grouped_calls = self._group_by_event_id(call_flows)
            grouped_actions = self._group_by_event_id(actions)
            items = [
                self._build_incident_item(
                    incident=incident,
                    events=grouped_events.get(incident.event_id, []),
                    processed_events=grouped_processed.get(
                        incident.event_id,
                        [],
                    ),
                    scheduled_actions=grouped_scheduled.get(
                        incident.event_id,
                        [],
                    ),
                    call_flows=grouped_calls.get(incident.event_id, []),
                    actions=grouped_actions.get(incident.event_id, []),
                    now=generated_at,
                )
                for incident in incidents
            ]

            return generated_at, items, total if total is not None else len(items)

        except SQLAlchemyError as e:
            if session is not None:
                session.rollback()
            print(
                f"[{console.level('ERROR')}] "
                "Dashboard query failed"
            )
            raise DashboardQueryError("dashboard_query_failed") from e

        finally:
            if session is not None:
                session.close()

    def _query_by_event_ids(self, session, model, event_ids):
        return (
            session.query(model)
            .filter(model.event_id.in_(event_ids))
            .all()
        )

    def _group_by_event_id(self, records):
        grouped = defaultdict(list)

        for record in records:
            if record.event_id is not None:
                grouped[record.event_id].append(record)

        return grouped

    def _build_incident_item(
        self,
        *,
        incident,
        events,
        processed_events,
        scheduled_actions,
        call_flows,
        actions,
        now,
    ):
        event = self._select_relevant_event(events)
        processed_event = self._select_relevant_processed_event(
            processed_events,
            now,
        )
        scheduled_action = self._select_relevant_scheduled_action(
            scheduled_actions,
            now,
        )
        call_flow = self._select_relevant_call_flow(call_flows)
        action = self._select_latest_action(actions)
        scheduled_processing_started_at = self._earliest_processing_start(
            scheduled_actions
        )
        scheduled_states = [
            record.state
            for record in scheduled_actions
            if self._normalize_state(record.state)
        ]
        display_status = resolve_dashboard_status(
            incident_status=incident.current_status,
            processed_event_state=(
                processed_event.state if processed_event else None
            ),
            processed_event_started_at=(
                processed_event.processing_started_at
                if processed_event else None
            ),
            scheduled_action_state=(
                scheduled_action.state if scheduled_action else None
            ),
            scheduled_action_states=scheduled_states,
            scheduled_action_scheduled_at=(
                scheduled_action.scheduled_at if scheduled_action else None
            ),
            scheduled_action_processing_started_at=(
                scheduled_processing_started_at
            ),
            call_flow_state=call_flow.state if call_flow else None,
            now=now,
            processing_timeout_minutes=self.processing_timeout_minutes,
        )
        stuck_since = self._get_stuck_since(
            processed_events,
            scheduled_actions,
            now,
        ) if display_status == DashboardStatus.STUCK else None
        call_drives_status = self._call_flow_drives_status(
            display_status=display_status,
            incident=incident,
            processed_event=processed_event,
            scheduled_actions=scheduled_actions,
            scheduled_action=scheduled_action,
            scheduled_processing_started_at=scheduled_processing_started_at,
            call_flow=call_flow,
            now=now,
        )
        current_action = self._format_actions(
            scheduled_action.actions if scheduled_action else None
        )

        if call_drives_status:
            current_action = "calls"
        elif current_action is None and action:
            current_action = action.action_type

        target = call_flow.target if call_drives_status else None

        if target is None and scheduled_action:
            target = scheduled_action.target

        if target is None and call_flow:
            target = call_flow.target

        attempt_count = None

        if call_flow and (call_drives_status or not scheduled_action):
            attempt_count = call_flow.attempt_count
        elif scheduled_action:
            attempt_count = scheduled_action.attempt_count

        return DashboardIncidentItem(
            event_id=incident.event_id,
            client=self._first_value(
                incident.client,
                event.client if event else None,
            ),
            host=self._first_value(
                incident.host,
                event.host if event else None,
            ),
            trigger=self._first_value(
                incident.trigger,
                event.trigger if event else None,
            ),
            severity=self._first_value(
                incident.severity,
                event.severity if event else None,
            ),
            incident_status=incident.current_status,
            display_status=display_status,
            opened_at=(
                self._parse_datetime(incident.opened_at)
                or self._parse_datetime(event.timestamp if event else None)
            ),
            updated_at=self._as_utc_or_none(incident.updated_at),
            current_action=current_action,
            target=target,
            scheduled_action_id=(
                scheduled_action.id if scheduled_action else None
            ),
            scheduled_action_state=(
                scheduled_action.state if scheduled_action else None
            ),
            scheduled_at=(
                scheduled_action.scheduled_at if scheduled_action else None
            ),
            paused_at=(
                scheduled_action.paused_at if scheduled_action else None
            ),
            resumed_at=(
                scheduled_action.resumed_at if scheduled_action else None
            ),
            attempt_count=attempt_count,
            call_flow_state=call_flow.state if call_flow else None,
            stuck_since=stuck_since,
            error_message=self._select_error_message(
                display_status=display_status,
                processed_events=processed_events,
                scheduled_action=scheduled_action,
                scheduled_actions=scheduled_actions,
                action=action,
                now=now,
            ),
        )

    def _select_relevant_event(self, records):
        return self._select(
            records,
            lambda record: (
                0 if self._normalize_state(record.status) in ("1", "problem") else 1,
                -self._timestamp(record.created_at),
                -(record.id or 0),
            ),
        )

    def _select_relevant_processed_event(self, records, now):
        return self._select(
            records,
            lambda record: (
                self._processed_event_rank(record, now),
                -self._timestamp(
                    record.updated_at
                    or record.processing_started_at
                    or record.processed_at
                    or record.last_seen_at
                    or record.created_at
                ),
                -(record.id or 0),
            ),
        )

    def _select_relevant_scheduled_action(self, records, now):
        return self._select(
            records,
            lambda record: (
                self._scheduled_action_rank(record, now),
                -self._timestamp(self._scheduled_activity_at(record)),
                -(record.id or 0),
            ),
        )

    def _select_relevant_call_flow(self, records):
        return self._select(
            records,
            lambda record: (
                CALL_FLOW_PRIORITY.get(
                    self._normalize_state(record.state),
                    max(CALL_FLOW_PRIORITY.values()) + 1,
                ),
                -self._timestamp(record.updated_at or record.created_at),
                -(record.id or 0),
            ),
        )

    def _select_latest_action(self, records):
        return self._select(
            records,
            lambda record: (
                -self._timestamp(record.created_at),
                -(record.id or 0),
            ),
        )

    def _select(self, records, key):
        return min(records, key=key) if records else None

    def _processed_event_rank(self, record, now):
        state = self._normalize_state(record.state)

        if state == "processing" and self._is_stale(
            record.processing_started_at,
            now,
        ):
            return 0

        return PROCESSED_EVENT_PRIORITY.get(
            state,
            max(PROCESSED_EVENT_PRIORITY.values()) + 1,
        )

    def _scheduled_action_rank(self, record, now):
        state = self._normalize_state(record.state)

        if state == "processing" and self._is_stale(
            record.processing_started_at,
            now,
        ):
            return 0

        return SCHEDULED_ACTION_PRIORITY.get(
            state,
            max(SCHEDULED_ACTION_PRIORITY.values()) + 1,
        )

    def _scheduled_activity_at(self, record):
        state = self._normalize_state(record.state)

        if state == "processing":
            return (
                record.processing_started_at
                or record.resumed_at
                or record.created_at
            )

        if state == "paused":
            return record.paused_at or record.created_at

        if state == "pending":
            return record.scheduled_at or record.created_at

        if state == "cancelled":
            return record.cancelled_at or record.created_at

        if state == "executed":
            return record.executed_at or record.created_at

        return record.created_at

    def _earliest_processing_start(self, records):
        timestamps = [
            self._as_utc(record.processing_started_at)
            for record in records
            if self._normalize_state(record.state) == "processing"
            and record.processing_started_at is not None
        ]

        return min(timestamps) if timestamps else None

    def _get_stuck_since(self, processed_events, scheduled_actions, now):
        candidates = []

        candidates.extend(
            self._as_utc(record.processing_started_at)
            for record in processed_events
            if self._normalize_state(record.state) == "processing"
            and self._is_stale(record.processing_started_at, now)
        )

        candidates.extend(
            self._as_utc(record.processing_started_at)
            for record in scheduled_actions
            if self._normalize_state(record.state) == "processing"
            and self._is_stale(record.processing_started_at, now)
        )

        return min(candidates) if candidates else None

    def _call_flow_drives_status(
        self,
        *,
        display_status,
        incident,
        processed_event,
        scheduled_actions,
        scheduled_action,
        scheduled_processing_started_at,
        call_flow,
        now,
    ):
        if not call_flow:
            return False

        without_call = resolve_dashboard_status(
            incident_status=incident.current_status,
            processed_event_state=(
                processed_event.state if processed_event else None
            ),
            processed_event_started_at=(
                processed_event.processing_started_at
                if processed_event else None
            ),
            scheduled_action_state=(
                scheduled_action.state if scheduled_action else None
            ),
            scheduled_action_states=[
                record.state for record in scheduled_actions
            ],
            scheduled_action_processing_started_at=(
                scheduled_processing_started_at
            ),
            now=now,
            processing_timeout_minutes=self.processing_timeout_minutes,
        )

        return display_status != without_call

    def _select_error_message(
        self,
        *,
        display_status,
        processed_events,
        scheduled_action,
        scheduled_actions,
        action,
        now,
    ):
        value = None

        if display_status == DashboardStatus.STUCK:
            candidates = []

            candidates.extend(
                (
                    self._as_utc(record.processing_started_at),
                    record.error_message,
                )
                for record in processed_events
                if self._normalize_state(record.state) == "processing"
                and self._is_stale(record.processing_started_at, now)
            )

            candidates.extend(
                (
                    self._as_utc(record.processing_started_at),
                    record.last_error or record.error_message,
                )
                for record in scheduled_actions
                if self._normalize_state(record.state) == "processing"
                and self._is_stale(record.processing_started_at, now)
            )

            if candidates:
                value = min(candidates, key=lambda candidate: candidate[0])[1]

        elif display_status == DashboardStatus.FAILED:
            if (
                scheduled_action
                and self._normalize_state(scheduled_action.state) == "failed"
            ):
                value = (
                    scheduled_action.error_message
                    or scheduled_action.last_error
                )
            else:
                failed_processed = self._select_relevant_processed_event(
                    [
                        record for record in processed_events
                        if self._normalize_state(record.state) == "failed"
                    ],
                    now,
                )

                if failed_processed:
                    value = failed_processed.error_message

        elif scheduled_action:
            value = scheduled_action.error_message or scheduled_action.last_error

        if value is None and action and self._normalize_state(action.status) == "failed":
            value = action.error_message

        return self._safe_error(value)

    def _safe_error(self, value):
        if value is None:
            return None

        value = str(value)
        value = re.sub(
            r"([a-z][a-z0-9+.-]*://)[^/@\s]+@",
            r"\1***@",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r"\bAuthorization\s*[:=]\s*(?:Basic|Bearer)?\s*[^,;\n]+",
            "Authorization: ***",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r"([\"']?(?:token|access[_-]?token|refresh[_-]?token|password|"
            r"secret|client[_-]?secret|api[_-]?key)[\"']?"
            r"\s*[:=]\s*)[\"']?[^\"'\s,;}]+[\"']?",
            r"\1***",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(
            r"\bBearer\s+[^\s,;]+",
            "Bearer ***",
            value,
            flags=re.IGNORECASE,
        )
        value = " ".join(value.split())

        return value[:MAX_ERROR_LENGTH] or None

    def _format_actions(self, value):
        if isinstance(value, str):
            return value.strip() or None

        if not isinstance(value, (list, tuple)):
            return None

        actions = [
            str(action).strip()
            for action in value
            if isinstance(action, str) and action.strip()
        ]

        return ", ".join(actions) or None

    def _is_stale(self, started_at, now):
        if started_at is None:
            return False

        cutoff = self._as_utc(now) - timedelta(
            minutes=self.processing_timeout_minutes
        )

        return self._as_utc(started_at) <= cutoff

    def _parse_datetime(self, value):
        if value is None:
            return None

        if isinstance(value, datetime):
            return self._as_utc(value)

        if not isinstance(value, str):
            return None

        value = value.strip()

        if not value:
            return None

        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        try:
            return self._as_utc(datetime.fromisoformat(value))
        except ValueError:
            return None

    def _as_utc(self, value):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)

    def _as_utc_or_none(self, value):
        return self._as_utc(value) if value is not None else None

    def _timestamp(self, value):
        return self._as_utc(value).timestamp() if value is not None else 0

    def _normalize_state(self, value):
        return str(value).strip().lower() if value is not None else None

    def _first_value(self, *values):
        for value in values:
            if value is not None and str(value).strip():
                return value

        return None


dashboard_query_service = DashboardQueryService()
