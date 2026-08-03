import logging
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError

from app.db.models import (
    ActionRecord,
    AuditLogRecord,
    CallAttemptRecord,
    CallFlowRecord,
    EventRecord,
    IncidentRecord,
    ProcessedEventRecord,
    ScheduledActionRecord,
)
from app.db.session import SessionLocal
from app.schemas.dashboard import (
    DashboardApprovalListResponse,
    DashboardApprovalItem,
    DashboardActionSummary,
    DashboardAuditSummary,
    DashboardCallAttemptSummary,
    DashboardIncidentDetail,
    DashboardIncidentItem,
    DashboardIncidentListResponse,
    DashboardOperationItem,
    DashboardOperationListResponse,
    DashboardOperationStatus,
    DashboardStatus,
    DashboardStatusCounts,
    DashboardSummaryResponse,
    DashboardInterventionSummary,
    resolve_dashboard_status,
    resolve_operation_status,
)
MAX_DASHBOARD_LIMIT = 100
MAX_ERROR_LENGTH = 500

logger = logging.getLogger(__name__)

ACTIVE_OPERATION_STATUSES = {
    DashboardOperationStatus.SCHEDULED,
    DashboardOperationStatus.PAUSED,
    DashboardOperationStatus.EXECUTING,
    DashboardOperationStatus.STUCK,
}

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

    def list_incidents(
        self, limit=100, offset=0, search=None, client=None, severity=None,
        status=None, incident_status=None,
    ):
        limit = max(1, min(int(limit), MAX_DASHBOARD_LIMIT))
        offset = max(0, int(offset))
        client_filter = str(client).strip().casefold() if client else None
        severity_filter = str(severity).strip().casefold() if severity else None
        search_filter = str(search).strip().casefold() if search else None
        status_filter = DashboardStatus(status) if status is not None else None
        incident_filter = str(incident_status).strip().casefold() if incident_status else None
        has_filters = any((client_filter, severity_filter, search_filter, status_filter, incident_filter)) or offset
        generated_at, items, total = self._load_items(
            limit=None if has_filters else limit,
            include_total=not has_filters,
        )

        if status_filter is not None:
            items = [
                item for item in items
                if item.display_status == status_filter
            ]

        if client_filter is not None:
            items = [
                item for item in items
                if str(item.client or "").strip().casefold() == client_filter
            ]

        if severity_filter is not None:
            items = [item for item in items if str(item.severity or "").strip().casefold() == severity_filter]

        if incident_filter is not None:
            items = [item for item in items if str(item.incident_status or "").strip().casefold() == incident_filter]

        if search_filter is not None:
            items = [
                item for item in items
                if search_filter in " ".join(str(value or "") for value in (
                    item.event_id, item.client, item.host, item.trigger,
                    item.severity, item.current_action, item.target,
                )).casefold()
            ]

        if has_filters:
            total = len(items)
            items = items[offset:offset + limit]

        return DashboardIncidentListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
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

    def get_incident_detail(self, event_id):
        event_id = str(event_id).strip()
        generated_at, incident_items, _ = self._load_items(limit=None, include_total=False)
        item = next((candidate for candidate in incident_items if candidate.event_id == event_id), None)
        if item is None:
            return None

        session = None
        try:
            session = self._session_factory()
            incident = session.query(IncidentRecord).filter(IncidentRecord.event_id == event_id).first()
            actions = self._query_by_event_ids(session, ActionRecord, [event_id])
            attempts = self._query_by_event_ids(session, CallAttemptRecord, [event_id])
            scheduled = self._query_by_event_ids(session, ScheduledActionRecord, [event_id])
            processed = self._query_by_event_ids(session, ProcessedEventRecord, [event_id])
            calls = self._query_by_event_ids(session, CallFlowRecord, [event_id])
            audits = self._query_by_event_ids(session, AuditLogRecord, [event_id])

            operation_response = self.list_operations(
                limit=100,
                event_id=event_id,
            )
            operations = operation_response.items
            operations = [operation.model_copy(update={"error_message": self._safe_detail_error(operation.error_message)}) for operation in operations]
            approvals = [self._approval_from_record(record, generated_at) for record in scheduled if record.execution_mode == "manual_approval"]
            approvals = [approval for approval in approvals if approval is not None]
            approvals.sort(key=lambda approval: (self._timestamp(approval.requested_at), approval.scheduled_action_id), reverse=True)

            interventions = []
            cutoff = generated_at - timedelta(minutes=self.processing_timeout_minutes)
            for record in scheduled:
                state = self._normalize_state(record.state)
                if state == "failed" or (state == "processing" and record.processing_started_at and self._as_utc(record.processing_started_at) <= cutoff):
                    interventions.append(DashboardInterventionSummary(
                        intervention_id=f"scheduled_action:{record.id}", source_type="scheduled_action",
                        status="failed" if state == "failed" else "stuck",
                        detected_at=self._as_utc(record.processing_started_at or record.created_at),
                        failure_reason="Scheduled action failed" if state == "failed" else "Processing exceeded the safe timeout",
                    ))
            for record in processed:
                state = self._normalize_state(record.state)
                if state == "failed" or (state == "processing" and record.processing_started_at and self._as_utc(record.processing_started_at) <= cutoff):
                    interventions.append(DashboardInterventionSummary(
                        intervention_id=f"processed_event:{record.id}", source_type="processed_event",
                        status="failed" if state == "failed" else "stuck",
                        detected_at=self._as_utc(record.processing_started_at or record.created_at),
                        failure_reason="Event processing failed" if state == "failed" else "Processing exceeded the safe timeout",
                    ))
            for record in calls:
                if self._normalize_state(record.state) == "manual_required":
                    interventions.append(DashboardInterventionSummary(
                        intervention_id=f"call_flow:{record.id}", source_type="call_flow", status="manual_required",
                        detected_at=self._as_utc(record.manual_required_at or record.updated_at or record.created_at),
                        failure_reason="Manual call handling required",
                    ))
            if self._normalize_state(incident.current_status) != "open":
                interventions = []
            interventions.sort(key=lambda value: (value.detected_at, value.intervention_id), reverse=True)

            safe_audits = []
            for record in sorted(audits, key=lambda value: (self._timestamp(value.created_at), value.id or 0), reverse=True)[:100]:
                details = record.details if isinstance(record.details, dict) else {}
                action_id = details.get("scheduled_action_id")
                safe_audits.append(DashboardAuditSummary(
                    audit_log_id=record.id, level=record.level, component=record.component,
                    message=self._safe_public_text(record.message, 500) or "Audit event",
                    created_at=self._as_utc(record.created_at),
                    scheduled_action_id=action_id if isinstance(action_id, int) else None,
                ))

            item_data = item.model_dump()
            item_data["error_message"] = self._safe_detail_error(item.error_message)
            return DashboardIncidentDetail(
                **item_data,
                trigger_group=incident.trigger_group,
                operations=operations[:100],
                actions=[DashboardActionSummary(
                    action_id=record.id, action=record.action_type,
                    status=record.status, created_at=self._as_utc_or_none(record.created_at),
                    error_message=self._safe_detail_error(record.error_message),
                ) for record in sorted(actions, key=lambda value: (self._timestamp(value.created_at), value.id or 0), reverse=True)[:100]],
                call_attempts=[DashboardCallAttemptSummary(
                    call_attempt_id=record.id, attempt_number=record.attempt_number, state=record.state,
                    started_at=self._as_utc_or_none(record.started_at), answered_at=self._as_utc_or_none(record.answered_at),
                    completed_at=self._as_utc_or_none(record.completed_at), confirmed_at=self._as_utc_or_none(record.confirmed_at),
                    error_message=self._safe_detail_error(record.error_message),
                ) for record in sorted(attempts, key=lambda value: (value.attempt_number, value.id or 0), reverse=True)[:100]],
                approvals=approvals[:100], interventions=interventions[:100], audit_logs=safe_audits,
            )
        except SQLAlchemyError as error:
            if session is not None:
                session.rollback()
            raise DashboardQueryError("dashboard_query_failed") from error
        finally:
            if session is not None:
                session.close()

    def list_operations(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        search: str | None = None,
        client: str | None = None,
        status: DashboardOperationStatus | None = None,
        action: str | None = None,
        internal_state: str | None = None,
        event_id: str | None = None,
        active_only: bool = False,
    ) -> DashboardOperationListResponse:
        limit = max(1, min(int(limit), MAX_DASHBOARD_LIMIT))
        offset = max(0, int(offset))
        client_filter = str(client).strip().casefold() if client else None
        search_filter = str(search).strip().casefold() if search else None
        action_filter = str(action).strip().casefold() if action else None
        state_filter = str(internal_state).strip().casefold() if internal_state else None
        event_filter = str(event_id).strip() if event_id else None
        status_filter = (
            DashboardOperationStatus(status) if status is not None else None
        )
        generated_at, items = self._load_operation_items(
            approval_only=False,
        )

        if client_filter is not None:
            items = [
                item for item in items
                if str(item.client or "").strip().casefold() == client_filter
            ]

        if status_filter is not None:
            items = [
                item for item in items
                if item.display_status == status_filter
            ]

        if active_only:
            items = [
                item for item in items
                if item.display_status in ACTIVE_OPERATION_STATUSES
            ]

        if action_filter is not None:
            items = [item for item in items if str(item.action or "").casefold() == action_filter]
        if state_filter is not None:
            items = [item for item in items if str(item.internal_state).casefold() == state_filter]
        if event_filter is not None:
            items = [item for item in items if item.event_id == event_filter]
        if search_filter is not None:
            items = [item for item in items if search_filter in " ".join(
                str(value or "") for value in (item.event_id, item.client, item.host, item.trigger, item.action, item.target)
            ).casefold()]

        return DashboardOperationListResponse(
            items=items[offset:offset + limit],
            total=len(items),
            limit=limit,
            offset=offset,
            generated_at=generated_at,
        )

    def list_approvals(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        status: str = "pending",
        search: str | None = None,
        client: str | None = None,
    ) -> DashboardApprovalListResponse:
        limit = max(1, min(int(limit), MAX_DASHBOARD_LIMIT))
        offset = max(0, int(offset))
        client_filter = str(client).strip().casefold() if client else None
        search_filter = str(search).strip().casefold() if search else None
        generated_at, items = self._load_approval_items()

        if client_filter is not None:
            items = [
                item for item in items
                if str(item.client or "").strip().casefold() == client_filter
            ]

        if status == "pending":
            items = [item for item in items if item.operation_state == "pending_approval"]
        elif status != "all":
            items = [item for item in items if item.decision == status]
        if search_filter is not None:
            items = [item for item in items if search_filter in " ".join(
                str(value or "") for value in (item.event_id, item.client, item.action, item.target, item.reason)
            ).casefold()]

        return DashboardApprovalListResponse(
            items=items[offset:offset + limit],
            total=len(items),
            limit=limit,
            offset=offset,
            generated_at=generated_at,
        )

    def _load_approval_items(self):
        session = None
        generated_at = self._as_utc(self._now_provider())
        try:
            session = self._session_factory()
            records = session.query(ScheduledActionRecord).filter(
                ScheduledActionRecord.execution_mode == "manual_approval"
            ).all()
            items = []
            for record in records:
                if self._normalize_state(record.execution_mode) != "manual_approval":
                    continue
                if record.id is None or record.event_id is None:
                    continue
                item = self._approval_from_record(record, generated_at)
                if item is not None:
                    items.append(item)
            items.sort(key=lambda item: (self._timestamp(item.requested_at), item.scheduled_action_id), reverse=True)
            return generated_at, items
        except SQLAlchemyError as error:
            if session is not None:
                session.rollback()
            raise DashboardQueryError("dashboard_query_failed") from error
        finally:
            if session is not None:
                session.close()

    def _approval_from_record(self, record, generated_at):
        decision = record.approval_decision
        if decision not in ("approved", "rejected"):
            decision = (
                "pending"
                if self._normalize_state(record.state) == "pending_approval"
                else None
            )
        try:
            display_status = resolve_operation_status(
                state=record.state, processing_started_at=record.processing_started_at,
                now=generated_at, processing_timeout_minutes=self.processing_timeout_minutes,
            )
        except ValueError:
            return None
        return DashboardApprovalItem(
            scheduled_action_id=record.id, event_id=record.event_id, client=record.client,
            action=self._format_actions(record.actions),
            target=self._safe_target(record.target),
            reason=record.approval_when, decision=decision,
            requested_at=self._as_utc_or_none(record.approval_requested_at or record.created_at),
            decided_at=self._as_utc_or_none(record.approval_decided_at), operation_state=record.state,
            result=self._normalize_state(record.state),
            display_status=display_status, created_at=self._as_utc_or_none(record.created_at),
        )

    def _load_operation_items(self, *, approval_only):
        session = None
        generated_at = self._as_utc(self._now_provider())

        try:
            session = self._session_factory()
            query = session.query(ScheduledActionRecord)

            if approval_only:
                query = query.filter(
                    ScheduledActionRecord.state == "pending_approval"
                )

            records = query.all()

            if approval_only:
                records = [
                    record for record in records
                    if self._normalize_state(record.state)
                    == "pending_approval"
                ]

            if not records:
                return generated_at, []

            event_ids = list({
                record.event_id
                for record in records
                if record.event_id is not None
            })
            incidents = (
                self._query_by_event_ids(
                    session,
                    IncidentRecord,
                    event_ids,
                )
                if event_ids else []
            )
            incidents_by_event_id = {
                incident.event_id: incident for incident in incidents
            }
            entries = []

            for record in records:
                if record.id is None or record.event_id is None:
                    logger.warning(
                        "Scheduled action missing dashboard identifiers"
                    )
                    continue

                try:
                    display_status = resolve_operation_status(
                        state=record.state,
                        processing_started_at=record.processing_started_at,
                        now=generated_at,
                        processing_timeout_minutes=(
                            self.processing_timeout_minutes
                        ),
                    )
                except ValueError:
                    logger.warning(
                        "Unsupported scheduled action state: id=%s",
                        record.id,
                    )
                    continue

                incident = incidents_by_event_id.get(record.event_id)
                activity_at = self._operation_activity_at(record)

                actions = self._operation_actions(record.actions)
                if approval_only:
                    actions = [", ".join(
                        action for action in actions if action
                    ) or None]

                for action_index, action in enumerate(actions):
                    item = DashboardOperationItem(
                        scheduled_action_id=record.id,
                        event_id=record.event_id,
                        client=self._first_value(
                            record.client,
                            incident.client if incident else None,
                        ),
                        host=self._first_value(
                            record.host,
                            incident.host if incident else None,
                        ),
                        trigger=self._first_value(
                            record.trigger,
                            incident.trigger if incident else None,
                        ),
                        severity=self._first_value(
                            record.severity,
                            incident.severity if incident else None,
                        ),
                        incident_status=(
                            incident.current_status if incident else None
                        ),
                        action=action,
                        target=self._safe_target(record.target),
                        internal_state=record.state,
                        display_status=display_status,
                        scheduled_at=self._as_utc_or_none(
                            record.scheduled_at
                        ),
                        processing_started_at=self._as_utc_or_none(
                            record.processing_started_at
                        ),
                        paused_at=self._as_utc_or_none(record.paused_at),
                        resumed_at=self._as_utc_or_none(record.resumed_at),
                        attempt_count=record.attempt_count,
                        created_at=self._as_utc_or_none(record.created_at),
                        activity_at=self._as_utc_or_none(activity_at),
                        executed_at=self._as_utc_or_none(record.executed_at),
                        cancelled_at=self._as_utc_or_none(record.cancelled_at),
                        max_attempts=self._max_attempts(),
                        pause_reason=record.pause_reason,
                        cancel_reason=record.cancel_reason,
                        error_message=self._safe_error(
                            record.error_message or record.last_error
                        ),
                    )
                    entries.append((
                        self._timestamp(activity_at),
                        record.id or 0,
                        -action_index,
                        item,
                    ))

            entries.sort(
                key=lambda entry: entry[:3],
                reverse=True,
            )

            return generated_at, [entry[3] for entry in entries]

        except SQLAlchemyError as e:
            if session is not None:
                session.rollback()
            logger.error(
                "Dashboard operation query failed: %s",
                type(e).__name__,
            )
            raise DashboardQueryError("dashboard_query_failed") from e

        finally:
            if session is not None:
                session.close()

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
            logger.error(
                "Dashboard query failed: %s",
                type(e).__name__,
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
            closed_at=self._parse_datetime(incident.closed_at),
            duration=incident.duration,
            updated_at=self._as_utc_or_none(incident.updated_at),
            current_action=current_action,
            target=self._safe_target(target),
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

    def _operation_activity_at(self, record):
        state = self._normalize_state(record.state)

        if state == "processing":
            return (
                record.processing_started_at
                or record.resumed_at
                or record.created_at
            )

        if state == "paused":
            return record.paused_at or record.created_at

        if state == "executed":
            return (
                record.executed_at
                or record.processing_started_at
                or record.created_at
            )

        if state == "cancelled":
            return record.cancelled_at or record.created_at

        if state == "failed":
            return record.processing_started_at or record.created_at

        return record.scheduled_at or record.created_at

    def _operation_actions(self, value):
        if isinstance(value, str):
            action = value.strip()
            return [action] if action else [None]

        if isinstance(value, (list, tuple)):
            actions = [
                action.strip()
                for action in value
                if isinstance(action, str) and action.strip()
            ]
            return actions or [None]

        return [None]

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

    def _safe_detail_error(self, value):
        safe = self._safe_error(value)
        return "Operation failed" if safe else None

    def _safe_public_text(self, value, max_length):
        value = self._safe_error(value)
        if value is None:
            return None
        value = re.sub(
            r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
            "***",
            value,
            flags=re.IGNORECASE,
        )
        value = re.sub(r"https?://\S+", "***", value, flags=re.IGNORECASE)
        value = re.sub(
            r"(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)",
            "***",
            value,
        )
        return value[:max_length] or None

    def _safe_target(self, value):
        if not isinstance(value, str):
            return None
        value = value.strip()
        if not value or len(value) > 100:
            return None
        if re.search(
            r"@|https?://|\d{7,}|(?:token|secret|password|phone|email)",
            value,
            re.IGNORECASE,
        ):
            return None
        return value if re.fullmatch(r"[\w .:/-]+", value) else None

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

    def _max_attempts(self):
        try:
            value = int(os.getenv("SCHEDULED_ACTION_MAX_ATTEMPTS", "3"))
        except ValueError:
            return 3
        return value if value > 0 else 3

    def _first_value(self, *values):
        for value in values:
            if value is not None and str(value).strip():
                return value

        return None


dashboard_query_service = DashboardQueryService()
