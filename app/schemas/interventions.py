from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel


class InterventionSourceType(str, Enum):
    CALL_FLOW = "call_flow"
    SCHEDULED_ACTION = "scheduled_action"
    PROCESSED_EVENT = "processed_event"


class InterventionStatus(str, Enum):
    MANUAL_REQUIRED = "manual_required"
    STUCK = "stuck"
    FAILED = "failed"


class InterventionItem(BaseModel):
    intervention_id: str
    source_type: InterventionSourceType
    source_id: int
    event_id: str | None = None
    client: str | None = None
    host: str | None = None
    description: str | None = None
    severity: str | None = None
    status: InterventionStatus
    detected_at: datetime
    attempt_count: int | None = None
    max_attempts: int | None = None
    retry_supported: Literal[False] = False
    retry_blocked_reason: Literal["retry_not_safe"] = "retry_not_safe"
    runbook_available: bool
    failure_reason: str


class InterventionRunbook(BaseModel):
    intervention_id: str
    source: Literal["persisted_action_plan", "current_runbook"]
    warning: str | None = None
    actions: list[str]
    target: str | None = None
    delay_minutes: int | None = None
    execution_mode: str | None = None
    approval_when: str | None = None
    pre_actions: list[str]
    pre_target: str | None = None


class InterventionErrorResponse(BaseModel):
    detail: str
    code: str
