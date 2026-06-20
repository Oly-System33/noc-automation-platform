from sqlalchemy import Column, DateTime, Integer, String, Text, func
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


class ScheduledActionRecord(Base):
    __tablename__ = "scheduled_actions"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, index=True, nullable=True)
    client = Column(String, nullable=True)
    host = Column(String, nullable=True)
    trigger = Column(Text, nullable=True)
    trigger_group = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    actions = Column(JSON_TYPE, nullable=True)
    target = Column(String, nullable=True)
    contacts_payload = Column(JSON_TYPE, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    state = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
