from datetime import datetime

from pydantic import BaseModel


class AuditLogItem(BaseModel):
    id: int
    event_id: str | None = None
    scheduled_action_id: int | None = None
    level: str
    component: str
    operation: str = "Audit event"
    message: str
    context: dict[str, str | int | bool | None]
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
    limit: int
    offset: int
    generated_at: datetime


class WorkerOperationalConfiguration(BaseModel):
    enabled: bool
    running: bool
    ready: bool
    poll_interval_seconds: int
    batch_size: int
    processing_timeout_minutes: int
    max_attempts: int


class RunbookOperationalConfiguration(BaseModel):
    available: bool
    count: int
    cache_count: int
    last_reload: datetime | None = None


class OperationalConfigurationResponse(BaseModel):
    generated_at: datetime
    worker: WorkerOperationalConfiguration
    runbooks: RunbookOperationalConfiguration


class OperationalErrorResponse(BaseModel):
    detail: str
