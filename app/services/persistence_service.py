from datetime import date, datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

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
from app.services.console import console


class PersistenceService:

    def _now(self):

        return datetime.now(timezone.utc)

    def normalize_zabbix_status(self, status):

        status = str(status)

        if status in ("1", "PROBLEM"):
            return "PROBLEM"

        if status in ("0", "RECOVERY"):
            return "RECOVERY"

        return status

    def _safe_value(self, value):

        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            if isinstance(value, float) and value != value:
                return None
            return value

        if isinstance(value, (datetime, date)):
            return value.isoformat()

        if isinstance(value, dict):
            return {
                str(key): self._safe_value(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [self._safe_value(item) for item in value]

        return str(value)

    def _event_payload(self, event):

        raw_payload = getattr(event, "raw_payload", None)

        if raw_payload:
            return self._safe_value(raw_payload)

        return self._safe_value({
            "host": getattr(event, "host", None),
            "trigger": getattr(event, "trigger", None),
            "severity": getattr(event, "severity", None),
            "status": getattr(event, "status", None),
            "event_id": getattr(event, "event_id", None),
            "timestamp": getattr(event, "timestamp", None),
            "duration": getattr(event, "duration", None),
        })

    def _run(self, operation):

        session = SessionLocal()

        try:
            result = operation(session)
            session.commit()
            return result

        except SQLAlchemyError as e:
            session.rollback()
            print(f"[{console.level('ERROR')}] Database operation failed: {e}")
            return None

        except Exception as e:
            session.rollback()
            print(f"[{console.level('ERROR')}] Database operation failed: {e}")
            return None

        finally:
            session.close()

    def record_event(self, event, client=None, host=None, trigger_group=None, raw_payload=None):

        def operation(session):
            record = EventRecord(
                event_id=getattr(event, "event_id", None),
                client=client,
                host=host,
                trigger=getattr(event, "trigger", None),
                trigger_group=trigger_group,
                severity=getattr(event, "severity", None),
                status=str(getattr(event, "status", None)),
                timestamp=getattr(event, "timestamp", None),
                duration=getattr(event, "duration", None),
                raw_payload=self._safe_value(raw_payload) or self._event_payload(event),
            )
            session.add(record)

        return self._run(operation)

    def update_event_context(self, event_id, client=None, host=None, trigger_group=None):

        if not event_id:
            return None

        def operation(session):
            records = (
                session.query(EventRecord)
                .filter(EventRecord.event_id == event_id)
                .all()
            )

            for record in records:
                if client:
                    record.client = client
                if host:
                    record.host = host
                if trigger_group:
                    record.trigger_group = trigger_group

        return self._run(operation)

    def open_incident(self, event, client, host, trigger_group=None):

        event_id = getattr(event, "event_id", None)

        if not event_id:
            return None

        def operation(session):
            incident = (
                session.query(IncidentRecord)
                .filter(IncidentRecord.event_id == event_id)
                .one_or_none()
            )

            if incident is None:
                incident = IncidentRecord(event_id=event_id)
                session.add(incident)

            incident.client = client
            incident.host = host
            incident.trigger = getattr(event, "trigger", None)
            incident.trigger_group = trigger_group
            incident.severity = getattr(event, "severity", None)
            incident.opened_at = getattr(event, "timestamp", None)
            incident.current_status = "open"

        return self._run(operation)

    def close_incident(self, event, client, host, duration=None, trigger_group=None):

        event_id = getattr(event, "event_id", None)

        if not event_id:
            return None

        def operation(session):
            incident = (
                session.query(IncidentRecord)
                .filter(IncidentRecord.event_id == event_id)
                .one_or_none()
            )

            if incident is None:
                return False

            incident.client = client or incident.client
            incident.host = host or incident.host
            incident.trigger = getattr(event, "trigger", None) or incident.trigger
            incident.trigger_group = trigger_group or incident.trigger_group
            incident.severity = getattr(event, "severity", None) or incident.severity
            incident.closed_at = getattr(event, "timestamp", None)
            incident.duration = duration or getattr(event, "duration", None)
            incident.current_status = "closed"

            return True

        return self._run(operation)

    def record_action(self, event, action_type, target, status, response=None, error_message=None, client=None, host=None, trigger_group=None):

        def operation(session):
            record = ActionRecord(
                event_id=getattr(event, "event_id", None),
                client=client,
                host=host,
                trigger_group=trigger_group,
                action_type=action_type,
                target=str(self._safe_value(target)) if target is not None else None,
                status=status,
                response=self._safe_value(response),
                error_message=error_message,
            )
            session.add(record)

        return self._run(operation)

    def record_audit_log(self, event_id, level, component, message, details=None):

        def operation(session):
            record = AuditLogRecord(
                event_id=event_id,
                level=level,
                component=component,
                message=message,
                details=self._safe_value(details),
            )
            session.add(record)

        return self._run(operation)

    def create_call_flow(self, event, client, host, target, phone, max_attempts, summary_payload=None):

        def operation(session):
            record = (
                session.query(CallFlowRecord)
                .filter(CallFlowRecord.event_id == getattr(event, "event_id", None))
                .one_or_none()
            )

            if record is None:
                record = CallFlowRecord(
                    event_id=getattr(event, "event_id", None),
                    client=client,
                    host=host,
                    trigger=getattr(event, "trigger", None),
                    severity=getattr(event, "severity", None),
                    target=target,
                    phone=phone,
                    state="pending",
                    max_attempts=max_attempts,
                    attempt_count=0,
                    confirmed="false",
                    next_attempt_at=self._now(),
                    summary_payload=self._safe_value(summary_payload),
                )
                session.add(record)
                session.flush()
            else:
                record.client = client or record.client
                record.host = host or record.host
                record.target = target or record.target
                record.phone = phone or record.phone
                record.max_attempts = max_attempts or record.max_attempts
                if summary_payload is not None:
                    record.summary_payload = self._safe_value(summary_payload)

            return self._call_flow_to_dict(record)

        return self._run(operation)

    def create_call_attempt(self, call_flow_id, event_id, attempt_number, phone):

        def operation(session):
            record = CallAttemptRecord(
                call_flow_id=call_flow_id,
                event_id=event_id,
                attempt_number=attempt_number,
                phone=phone,
                state="created",
            )
            session.add(record)
            session.flush()

            flow = session.query(CallFlowRecord).filter(CallFlowRecord.id == call_flow_id).one_or_none()

            if flow:
                flow.state = "calling"
                flow.attempt_count = max(flow.attempt_count or 0, attempt_number)

            return self._call_attempt_to_dict(record)

        return self._run(operation)

    def mark_call_attempt_started(self, event_id, attempt_number, vonage_uuid=None):

        def operation(session):
            attempt = (
                session.query(CallAttemptRecord)
                .filter(CallAttemptRecord.event_id == event_id)
                .filter(CallAttemptRecord.attempt_number == attempt_number)
                .one_or_none()
            )

            if not attempt:
                return None

            attempt.state = "started"
            attempt.started_at = self._now()
            attempt.vonage_uuid = vonage_uuid or attempt.vonage_uuid

            flow = session.query(CallFlowRecord).filter(CallFlowRecord.id == attempt.call_flow_id).one_or_none()

            if flow:
                flow.state = "waiting_confirmation"

            return self._call_attempt_to_dict(attempt)

        return self._run(operation)

    def mark_call_attempt_event(self, event_id, status, vonage_uuid=None, answered_at=None):

        def operation(session):
            query = session.query(CallAttemptRecord)

            if vonage_uuid:
                attempt = query.filter(CallAttemptRecord.vonage_uuid == vonage_uuid).order_by(CallAttemptRecord.id.desc()).first()
            else:
                attempt = (
                    query.filter(CallAttemptRecord.event_id == event_id)
                    .order_by(CallAttemptRecord.attempt_number.desc())
                    .first()
                )

            if not attempt:
                return None

            normalized = str(status or "").lower()

            if vonage_uuid and not attempt.vonage_uuid:
                attempt.vonage_uuid = vonage_uuid

            if normalized == "answered":
                attempt.state = "answered"
                attempt.answered_at = answered_at or self._now()
            elif normalized in ("completed", "busy", "failed", "rejected", "timeout", "unanswered", "cancelled"):
                attempt.state = "completed" if normalized == "completed" else normalized
                attempt.completed_at = self._now()
            elif normalized:
                attempt.state = normalized

            return self._call_attempt_to_dict(attempt)

        return self._run(operation)

    def mark_call_confirmed(self, event_id, digit="1"):

        def operation(session):
            flow = (
                session.query(CallFlowRecord)
                .filter(CallFlowRecord.event_id == event_id)
                .one_or_none()
            )

            if not flow:
                return None

            attempt = (
                session.query(CallAttemptRecord)
                .filter(CallAttemptRecord.event_id == event_id)
                .order_by(CallAttemptRecord.attempt_number.desc())
                .first()
            )
            confirmed_at = self._now()
            attempt_number = attempt.attempt_number if attempt else None

            if attempt:
                attempt.state = "confirmed"
                attempt.confirmed_at = confirmed_at
                attempt.dtmf_digit = digit

            flow.state = "confirmed"
            flow.confirmed = "true"
            flow.confirmed_at = confirmed_at
            flow.confirmed_attempt = attempt_number
            flow.next_attempt_at = None

            return {
                "flow": self._call_flow_to_dict(flow),
                "attempt": self._call_attempt_to_dict(attempt) if attempt else None,
            }

        return self._run(operation)

    def mark_call_attempt_no_confirmation(self, event_id, attempt_number):

        def operation(session):
            attempt = (
                session.query(CallAttemptRecord)
                .filter(CallAttemptRecord.event_id == event_id)
                .filter(CallAttemptRecord.attempt_number == attempt_number)
                .one_or_none()
            )

            if attempt:
                attempt.state = "no_confirmation"
                attempt.completed_at = self._now()

            return self._call_attempt_to_dict(attempt) if attempt else None

        return self._run(operation)

    def schedule_next_call_attempt(self, event_id, next_attempt_at):

        def operation(session):
            flow = session.query(CallFlowRecord).filter(CallFlowRecord.event_id == event_id).one_or_none()

            if not flow:
                return None

            flow.state = "retry_scheduled"
            flow.next_attempt_at = next_attempt_at

            return self._call_flow_to_dict(flow)

        return self._run(operation)

    def mark_call_flow_manual_required(self, event_id):

        def operation(session):
            flow = session.query(CallFlowRecord).filter(CallFlowRecord.event_id == event_id).one_or_none()

            if not flow:
                return None

            flow.state = "manual_required"
            flow.manual_required_at = self._now()
            flow.next_attempt_at = None

            return self._call_flow_to_dict(flow)

        return self._run(operation)

    def cancel_pending_call_flows(self, event_id, reason="recovery_received"):

        def operation(session):
            count = (
                session.query(CallFlowRecord)
                .filter(CallFlowRecord.event_id == event_id)
                .filter(CallFlowRecord.state.in_(["pending", "calling", "waiting_confirmation", "retry_scheduled"]))
                .update({"state": "cancelled", "next_attempt_at": None})
            )

            return {"success": True, "count": count, "reason": reason}

        return self._run(operation) or {"success": False, "count": 0, "reason": reason}

    def get_call_flow(self, event_id):

        def operation(session):
            flow = session.query(CallFlowRecord).filter(CallFlowRecord.event_id == event_id).one_or_none()
            return self._call_flow_to_dict(flow) if flow else None

        return self._run(operation)

    def _call_flow_to_dict(self, record):

        if not record:
            return None

        return {
            "id": record.id,
            "event_id": record.event_id,
            "client": record.client,
            "host": record.host,
            "trigger": record.trigger,
            "severity": record.severity,
            "target": record.target,
            "phone": record.phone,
            "state": record.state,
            "max_attempts": record.max_attempts,
            "attempt_count": record.attempt_count,
            "confirmed": record.confirmed == "true",
            "confirmed_at": record.confirmed_at.isoformat() if record.confirmed_at else None,
            "confirmed_attempt": record.confirmed_attempt,
            "manual_required_at": record.manual_required_at.isoformat() if record.manual_required_at else None,
            "next_attempt_at": record.next_attempt_at.isoformat() if record.next_attempt_at else None,
            "summary_payload": record.summary_payload,
        }

    def _call_attempt_to_dict(self, record):

        if not record:
            return None

        return {
            "id": record.id,
            "event_id": record.event_id,
            "call_flow_id": record.call_flow_id,
            "attempt_number": record.attempt_number,
            "phone": record.phone,
            "vonage_uuid": record.vonage_uuid,
            "state": record.state,
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "answered_at": record.answered_at.isoformat() if record.answered_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
            "confirmed_at": record.confirmed_at.isoformat() if record.confirmed_at else None,
            "dtmf_digit": record.dtmf_digit,
            "error_message": record.error_message,
        }

    def claim_event_processing(self, event, zabbix_status, client, host):

        zabbix_status = self.normalize_zabbix_status(zabbix_status)
        session = SessionLocal()

        try:
            record = ProcessedEventRecord(
                event_id=getattr(event, "event_id", None),
                zabbix_status=zabbix_status,
                client=client,
                host=host,
                trigger=getattr(event, "trigger", None),
                severity=getattr(event, "severity", None),
                state="processing",
                first_seen_at=self._now(),
                last_seen_at=self._now(),
                received_count=1,
                processing_started_at=self._now(),
            )
            session.add(record)
            session.commit()

            return {
                "success": True,
                "is_new": True,
                "state": record.state,
                "received_count": record.received_count,
                "error": None,
            }

        except IntegrityError:
            session.rollback()

            existing = (
                session.query(ProcessedEventRecord)
                .filter(ProcessedEventRecord.event_id == getattr(event, "event_id", None))
                .filter(ProcessedEventRecord.zabbix_status == zabbix_status)
                .one_or_none()
            )

            if existing:
                existing.received_count = (existing.received_count or 0) + 1
                existing.last_seen_at = self._now()
                existing.client = client or existing.client
                existing.host = host or existing.host
                session.commit()

                return {
                    "success": True,
                    "is_new": False,
                    "state": existing.state,
                    "received_count": existing.received_count,
                    "error": None,
                }

            return {
                "success": False,
                "is_new": False,
                "state": None,
                "received_count": None,
                "error": "Duplicate event detected but existing record was not found",
            }

        except Exception as e:
            session.rollback()
            print(f"[{console.level('ERROR')}] Database operation failed: {e}")
            return {
                "success": False,
                "is_new": False,
                "state": None,
                "received_count": None,
                "error": str(e),
            }

        finally:
            session.close()

    def mark_event_processed(self, event_id, zabbix_status):

        zabbix_status = self.normalize_zabbix_status(zabbix_status)

        def operation(session):
            updated = (
                session.query(ProcessedEventRecord)
                .filter(ProcessedEventRecord.event_id == event_id)
                .filter(ProcessedEventRecord.zabbix_status == zabbix_status)
                .update({
                    "state": "processed",
                    "processed_at": self._now(),
                    "error_message": None,
                })
            )

            return updated == 1

        return bool(self._run(operation))

    def mark_event_failed(self, event_id, zabbix_status, error_message):

        zabbix_status = self.normalize_zabbix_status(zabbix_status)

        def operation(session):
            updated = (
                session.query(ProcessedEventRecord)
                .filter(ProcessedEventRecord.event_id == event_id)
                .filter(ProcessedEventRecord.zabbix_status == zabbix_status)
                .update({
                    "state": "failed",
                    "error_message": error_message,
                })
            )

            return updated == 1

        return bool(self._run(operation))

    def build_scheduled_action_dedupe_key(self, event_id, trigger_group, target, actions):

        normalized_actions = sorted(str(action).strip().lower() for action in actions or [])

        return "|".join([
            str(event_id or ""),
            str(trigger_group or ""),
            str(target or ""),
            ",".join(normalized_actions),
        ])

    def create_scheduled_action(self, event, client, host, trigger_group, actions, target, contacts_payload, scheduled_at):

        session = SessionLocal()
        dedupe_key = self.build_scheduled_action_dedupe_key(
            event_id=getattr(event, "event_id", None),
            trigger_group=trigger_group,
            target=target,
            actions=actions,
        )

        try:
            record = ScheduledActionRecord(
                event_id=getattr(event, "event_id", None),
                client=client,
                host=host,
                trigger=getattr(event, "trigger", None),
                trigger_group=trigger_group,
                severity=getattr(event, "severity", None),
                actions=self._safe_value(actions),
                target=target,
                dedupe_key=dedupe_key,
                contacts_payload=self._safe_value(contacts_payload),
                scheduled_at=scheduled_at,
                state="pending",
                attempt_count=0,
            )
            session.add(record)
            session.flush()

            response = {
                "success": True,
                "scheduled_action_id": record.id,
                "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
                "state": record.state,
                "duplicate": False,
                "dedupe_key": dedupe_key,
                "error": None,
            }

            session.commit()

            return response

        except IntegrityError:
            session.rollback()
            existing = (
                session.query(ScheduledActionRecord)
                .filter(ScheduledActionRecord.dedupe_key == dedupe_key)
                .one_or_none()
            )

            return {
                "success": True,
                "scheduled_action_id": existing.id if existing else None,
                "scheduled_at": existing.scheduled_at.isoformat() if existing and existing.scheduled_at else None,
                "state": existing.state if existing else None,
                "duplicate": True,
                "dedupe_key": dedupe_key,
                "error": None,
            }

        except SQLAlchemyError as e:
            session.rollback()
            print(f"[{console.level('ERROR')}] Database operation failed: {e}")
            return {
                "success": False,
                "scheduled_action_id": None,
                "scheduled_at": None,
                "state": None,
                "duplicate": False,
                "dedupe_key": dedupe_key,
                "error": str(e),
            }

        except Exception as e:
            session.rollback()
            print(f"[{console.level('ERROR')}] Database operation failed: {e}")
            return {
                "success": False,
                "scheduled_action_id": None,
                "scheduled_at": None,
                "state": None,
                "duplicate": False,
                "dedupe_key": dedupe_key,
                "error": str(e),
            }

        finally:
            session.close()

    def get_due_scheduled_actions(self, batch_size):

        session = SessionLocal()

        try:
            records = (
                session.query(ScheduledActionRecord)
                .filter(ScheduledActionRecord.state == "pending")
                .filter(ScheduledActionRecord.scheduled_at <= self._now())
                .order_by(ScheduledActionRecord.scheduled_at)
                .limit(batch_size)
                .all()
            )

            return [self._scheduled_action_to_dict(record) for record in records]

        except Exception as e:
            print(f"[{console.level('ERROR')}] Database operation failed: {e}")
            return []

        finally:
            session.close()

    def _scheduled_action_to_dict(self, record):

        return {
            "id": record.id,
            "event_id": record.event_id,
            "client": record.client,
            "host": record.host,
            "trigger": record.trigger,
            "trigger_group": record.trigger_group,
            "severity": record.severity,
            "actions": record.actions,
            "target": record.target,
            "contacts_payload": record.contacts_payload,
            "scheduled_at": record.scheduled_at,
            "state": record.state,
            "created_at": record.created_at,
            "attempt_count": record.attempt_count,
            "dedupe_key": record.dedupe_key,
        }

    def claim_scheduled_action(self, scheduled_action_id):

        def operation(session):
            updated = (
                session.query(ScheduledActionRecord)
                .filter(ScheduledActionRecord.id == scheduled_action_id)
                .filter(ScheduledActionRecord.state == "pending")
                .update({
                    "state": "processing",
                    "processing_started_at": self._now(),
                    "attempt_count": ScheduledActionRecord.attempt_count + 1,
                })
            )

            return updated == 1

        return bool(self._run(operation))

    def get_incident_status(self, event_id):

        if not event_id:
            return None

        def operation(session):
            incident = (
                session.query(IncidentRecord)
                .filter(IncidentRecord.event_id == event_id)
                .one_or_none()
            )

            if not incident:
                return None

            return incident.current_status

        return self._run(operation)

    def mark_scheduled_action_executed(self, scheduled_action_id):

        def operation(session):
            updated = (
                session.query(ScheduledActionRecord)
                .filter(ScheduledActionRecord.id == scheduled_action_id)
                .filter(ScheduledActionRecord.state == "processing")
                .update({
                    "state": "executed",
                    "executed_at": self._now(),
                    "processing_started_at": None,
                    "error_message": None,
                    "last_error": None,
                })
            )

            return updated == 1

        return bool(self._run(operation))

    def mark_scheduled_action_failed(self, scheduled_action_id, error_message):

        def operation(session):
            updated = (
                session.query(ScheduledActionRecord)
                .filter(ScheduledActionRecord.id == scheduled_action_id)
                .filter(ScheduledActionRecord.state == "processing")
                .update({
                    "state": "failed",
                    "error_message": error_message,
                    "last_error": error_message,
                    "processing_started_at": None,
                })
            )

            return updated == 1

        return bool(self._run(operation))

    def cancel_scheduled_action(self, scheduled_action_id, reason):

        def operation(session):
            updated = (
                session.query(ScheduledActionRecord)
                .filter(ScheduledActionRecord.id == scheduled_action_id)
                .filter(ScheduledActionRecord.state.in_(["pending", "processing"]))
                .update({
                    "state": "cancelled",
                    "cancelled_at": self._now(),
                    "cancel_reason": reason,
                    "processing_started_at": None,
                })
            )

            return updated == 1

        return bool(self._run(operation))

    def cancel_pending_scheduled_actions(self, event_id, reason="recovery_received"):

        if not event_id:
            return {"success": False, "count": 0, "error": "Missing event_id"}

        session = SessionLocal()

        try:
            count = (
                session.query(ScheduledActionRecord)
                .filter(ScheduledActionRecord.event_id == event_id)
                .filter(ScheduledActionRecord.state == "pending")
                .update({
                    "state": "cancelled",
                    "cancelled_at": self._now(),
                    "cancel_reason": reason,
                    "processing_started_at": None,
                })
            )

            session.commit()

            return {"success": True, "count": count, "error": None}

        except Exception as e:
            session.rollback()
            print(f"[{console.level('ERROR')}] Database operation failed: {e}")
            return {"success": False, "count": 0, "error": str(e)}

        finally:
            session.close()

    def recover_stale_scheduled_actions(self, timeout_minutes, max_attempts):

        session = SessionLocal()
        cutoff = self._now() - timedelta(minutes=timeout_minutes)

        try:
            stale_records = (
                session.query(ScheduledActionRecord)
                .filter(ScheduledActionRecord.state == "processing")
                .filter(ScheduledActionRecord.processing_started_at <= cutoff)
                .all()
            )

            recovered = 0
            failed = 0

            for record in stale_records:
                if (record.attempt_count or 0) < max_attempts:
                    record.state = "pending"
                    record.processing_started_at = None
                    record.last_error = "Recovered stale processing action"
                    recovered += 1
                else:
                    record.state = "failed"
                    record.processing_started_at = None
                    record.error_message = "Max attempts exceeded after stale processing"
                    record.last_error = record.error_message
                    failed += 1

            session.commit()

            return {"success": True, "recovered": recovered, "failed": failed, "error": None}

        except Exception as e:
            session.rollback()
            print(f"[{console.level('ERROR')}] Database operation failed: {e}")
            return {"success": False, "recovered": 0, "failed": 0, "error": str(e)}

        finally:
            session.close()

    def get_startup_summary(self, scheduled_timeout_minutes=10, event_timeout_minutes=10):

        session = SessionLocal()
        now = self._now()
        scheduled_cutoff = now - timedelta(minutes=scheduled_timeout_minutes)
        event_cutoff = now - timedelta(minutes=event_timeout_minutes)

        try:
            return {
                "open_incidents": session.query(IncidentRecord).filter(IncidentRecord.current_status == "open").count(),
                "pending_scheduled": session.query(ScheduledActionRecord).filter(ScheduledActionRecord.state == "pending").count(),
                "due_scheduled": (
                    session.query(ScheduledActionRecord)
                    .filter(ScheduledActionRecord.state == "pending")
                    .filter(ScheduledActionRecord.scheduled_at <= now)
                    .count()
                ),
                "stuck_scheduled": (
                    session.query(ScheduledActionRecord)
                    .filter(ScheduledActionRecord.state == "processing")
                    .filter(ScheduledActionRecord.processing_started_at <= scheduled_cutoff)
                    .count()
                ),
                "stuck_events": (
                    session.query(ProcessedEventRecord)
                    .filter(ProcessedEventRecord.state == "processing")
                    .filter(ProcessedEventRecord.processing_started_at <= event_cutoff)
                    .count()
                ),
            }

        except Exception as e:
            print(f"[{console.level('ERROR')}] Database operation failed: {e}")
            return None

        finally:
            session.close()


persistence_service = PersistenceService()
