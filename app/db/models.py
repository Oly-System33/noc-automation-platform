from sqlalchemy import Column, DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


JSON_TYPE = JSONB


class EventRecord(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, index=True, nullable=True)
    client = Column(String, nullable=True)
    host = Column(String, nullable=True)
    trigger = Column(Text, nullable=True)
    trigger_group = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    status = Column(String, nullable=True)
    timestamp = Column(String, nullable=True)
    duration = Column(String, nullable=True)
    raw_payload = Column(JSON_TYPE, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IncidentRecord(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, index=True, nullable=False, unique=True)
    client = Column(String, nullable=True)
    host = Column(String, nullable=True)
    trigger = Column(Text, nullable=True)
    trigger_group = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    opened_at = Column(String, nullable=True)
    closed_at = Column(String, nullable=True)
    duration = Column(String, nullable=True)
    current_status = Column(String, nullable=False, default="open")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ActionRecord(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, index=True, nullable=True)
    client = Column(String, nullable=True)
    host = Column(String, nullable=True)
    trigger_group = Column(String, nullable=True)
    action_type = Column(String, nullable=False)
    target = Column(Text, nullable=True)
    status = Column(String, nullable=False)
    response = Column(JSON_TYPE, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuditLogRecord(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, index=True, nullable=True)
    level = Column(String, nullable=False)
    component = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON_TYPE, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ProcessedEventRecord(Base):
    __tablename__ = "processed_events"
    __table_args__ = (
        UniqueConstraint("event_id", "zabbix_status", name="uq_processed_events_event_status"),
        Index("ix_processed_events_state_processing_started_at", "state", "processing_started_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, nullable=False)
    zabbix_status = Column(String, nullable=False)
    client = Column(String, nullable=True)
    host = Column(String, nullable=True)
    trigger = Column(Text, nullable=True)
    severity = Column(String, nullable=True)
    state = Column(String, nullable=False, default="processing")
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    received_count = Column(Integer, nullable=False, default=1)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ScheduledActionRecord(Base):
    __tablename__ = "scheduled_actions"
    __table_args__ = (
        Index("ix_scheduled_actions_state_scheduled_at", "state", "scheduled_at"),
        Index("ix_scheduled_actions_state_processing_started_at", "state", "processing_started_at"),
        UniqueConstraint("dedupe_key", name="uq_scheduled_actions_dedupe_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, index=True, nullable=True)
    client = Column(String, nullable=True)
    host = Column(String, nullable=True)
    trigger = Column(Text, nullable=True)
    trigger_group = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    actions = Column(JSON_TYPE, nullable=True)
    target = Column(String, nullable=True)
    dedupe_key = Column(String, nullable=True)
    contacts_payload = Column(JSON_TYPE, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    state = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    last_error = Column(Text, nullable=True)
