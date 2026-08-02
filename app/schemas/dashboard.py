from datetime import datetime, timedelta, timezone
from enum import Enum

from pydantic import BaseModel


class DashboardStatus(str, Enum):
    ACTIVE = "active"
    SCHEDULED = "scheduled"
    PAUSED = "paused"
    PENDING_APPROVAL = "pending_approval"
    EXECUTING = "executing"
    WAITING_CONFIRMATION = "waiting_confirmation"
    RETRY_SCHEDULED = "retry_scheduled"
    MANUAL_REQUIRED = "manual_required"
    STUCK = "stuck"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class DashboardOperationStatus(str, Enum):
    SCHEDULED = "scheduled"
    PENDING_APPROVAL = "pending_approval"
    PAUSED = "paused"
    EXECUTING = "executing"
    STUCK = "stuck"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _normalize_state(value):
    if not isinstance(value, str):
        return None

    return value.strip().lower() or None


def _as_utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def resolve_dashboard_status(
    *,
    incident_status: str | None = None,
    processed_event_state: str | None = None,
    processed_event_started_at: datetime | None = None,
    scheduled_action_state: str | None = None,
    scheduled_action_states: list[str] | tuple[str, ...] | set[str] | None = None,
    scheduled_action_scheduled_at: datetime | None = None,
    scheduled_action_processing_started_at: datetime | None = None,
    call_flow_state: str | None = None,
    now: datetime | None = None,
    processing_timeout_minutes: int = 10,
) -> DashboardStatus:
    incident_status = _normalize_state(incident_status)
    processed_event_state = _normalize_state(processed_event_state)
    scheduled_action_state = _normalize_state(scheduled_action_state)
    normalized_scheduled_states = {
        normalized
        for state in scheduled_action_states or []
        if (normalized := _normalize_state(state)) is not None
    }

    if scheduled_action_state:
        normalized_scheduled_states.add(scheduled_action_state)

    call_flow_state = _normalize_state(call_flow_state)
    current_time = _as_utc(now or datetime.now(timezone.utc))
    processing_cutoff = current_time - timedelta(
        minutes=processing_timeout_minutes
    )

    def is_stuck(state, started_at):
        return (
            state == "processing"
            and started_at is not None
            and _as_utc(started_at) <= processing_cutoff
        )

    if incident_status == "closed":
        return DashboardStatus.CLOSED

    if (
        is_stuck(processed_event_state, processed_event_started_at)
        or is_stuck(
            (
                "processing"
                if "processing" in normalized_scheduled_states
                else None
            ),
            scheduled_action_processing_started_at,
        )
    ):
        return DashboardStatus.STUCK

    if (
        processed_event_state == "failed"
        or "failed" in normalized_scheduled_states
    ):
        return DashboardStatus.FAILED

    if "pending_approval" in normalized_scheduled_states:
        return DashboardStatus.PENDING_APPROVAL

    if call_flow_state == "manual_required":
        return DashboardStatus.MANUAL_REQUIRED

    if call_flow_state == "waiting_confirmation":
        return DashboardStatus.WAITING_CONFIRMATION

    if call_flow_state == "retry_scheduled":
        return DashboardStatus.RETRY_SCHEDULED

    if (
        processed_event_state == "processing"
        or "processing" in normalized_scheduled_states
        or call_flow_state == "calling"
    ):
        return DashboardStatus.EXECUTING

    if "paused" in normalized_scheduled_states:
        return DashboardStatus.PAUSED

    if "pending" in normalized_scheduled_states:
        return DashboardStatus.SCHEDULED

    if (
        "cancelled" in normalized_scheduled_states
        or call_flow_state == "cancelled"
    ):
        return DashboardStatus.CANCELLED

    return DashboardStatus.ACTIVE


def resolve_operation_status(
    *,
    state: str,
    processing_started_at: datetime | None = None,
    now: datetime | None = None,
    processing_timeout_minutes: int = 10,
) -> DashboardOperationStatus:
    state = _normalize_state(state)

    if state == "processing":
        current_time = _as_utc(now or datetime.now(timezone.utc))
        cutoff = current_time - timedelta(
            minutes=processing_timeout_minutes
        )

        if (
            processing_started_at is not None
            and _as_utc(processing_started_at) <= cutoff
        ):
            return DashboardOperationStatus.STUCK

        return DashboardOperationStatus.EXECUTING

    status_by_state = {
        "pending": DashboardOperationStatus.SCHEDULED,
        "pending_approval": DashboardOperationStatus.PENDING_APPROVAL,
        "paused": DashboardOperationStatus.PAUSED,
        "executed": DashboardOperationStatus.EXECUTED,
        "failed": DashboardOperationStatus.FAILED,
        "cancelled": DashboardOperationStatus.CANCELLED,
    }

    try:
        return status_by_state[state]
    except KeyError:
        raise ValueError("unsupported_operation_state") from None


class DashboardIncidentItem(BaseModel):
    event_id: str
    client: str | None = None
    host: str | None = None
    trigger: str | None = None
    severity: str | None = None
    incident_status: str | None = None
    display_status: DashboardStatus
    opened_at: datetime | None = None
    updated_at: datetime | None = None
    current_action: str | None = None
    target: str | None = None
    scheduled_action_id: int | None = None
    scheduled_action_state: str | None = None
    scheduled_at: datetime | None = None
    paused_at: datetime | None = None
    resumed_at: datetime | None = None
    attempt_count: int | None = None
    call_flow_state: str | None = None
    stuck_since: datetime | None = None
    error_message: str | None = None


class DashboardOperationItem(BaseModel):
    scheduled_action_id: int
    event_id: str
    client: str | None = None
    host: str | None = None
    trigger: str | None = None
    severity: str | None = None
    incident_status: str | None = None
    action: str | None = None
    target: str | None = None
    internal_state: str
    display_status: DashboardOperationStatus
    scheduled_at: datetime | None = None
    processing_started_at: datetime | None = None
    paused_at: datetime | None = None
    resumed_at: datetime | None = None
    attempt_count: int | None = None
    created_at: datetime | None = None
    pause_reason: str | None = None
    cancel_reason: str | None = None
    error_message: str | None = None


class DashboardStatusCounts(BaseModel):
    active: int = 0
    scheduled: int = 0
    paused: int = 0
    pending_approval: int = 0
    executing: int = 0
    waiting_confirmation: int = 0
    retry_scheduled: int = 0
    manual_required: int = 0
    stuck: int = 0
    failed: int = 0
    cancelled: int = 0
    closed: int = 0


class DashboardSummaryResponse(BaseModel):
    generated_at: datetime
    counts: DashboardStatusCounts
    by_client: dict[str, int]
    total: int


class DashboardIncidentListResponse(BaseModel):
    items: list[DashboardIncidentItem]
    total: int
    generated_at: datetime


class DashboardOperationListResponse(BaseModel):
    items: list[DashboardOperationItem]
    total: int
    generated_at: datetime


class DashboardApprovalListResponse(BaseModel):
    items: list[DashboardOperationItem]
    total: int
    generated_at: datetime
