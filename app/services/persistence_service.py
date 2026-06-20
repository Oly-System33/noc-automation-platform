from datetime import date, datetime, timezone

from sqlalchemy.exc import SQLAlchemyError

from app.db.models import (
    ActionRecord,
    AuditLogRecord,
    EventRecord,
    IncidentRecord,
    ScheduledActionRecord,
)
from app.db.session import SessionLocal


class PersistenceService:

    def _now(self):

        return datetime.now(timezone.utc)

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
            print(f"[ERROR] Database operation failed: {e}")
            return None

        except Exception as e:
            session.rollback()
            print(f"[ERROR] Database operation failed: {e}")
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

    def create_scheduled_action(self, event, client, host, trigger_group, actions, target, contacts_payload, scheduled_at):

        session = SessionLocal()

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
                contacts_payload=self._safe_value(contacts_payload),
                scheduled_at=scheduled_at,
                state="pending",
            )
            session.add(record)
            session.flush()

            response = {
                "success": True,
                "scheduled_action_id": record.id,
                "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
                "state": record.state,
                "error": None,
            }

            session.commit()

            return response

        except SQLAlchemyError as e:
            session.rollback()
            print(f"[ERROR] Database operation failed: {e}")
            return {
                "success": False,
                "scheduled_action_id": None,
                "scheduled_at": None,
                "state": None,
                "error": str(e),
            }

        except Exception as e:
            session.rollback()
            print(f"[ERROR] Database operation failed: {e}")
            return {
                "success": False,
                "scheduled_action_id": None,
                "scheduled_at": None,
                "state": None,
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
            print(f"[ERROR] Database operation failed: {e}")
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
        }

    def claim_scheduled_action(self, scheduled_action_id):

        def operation(session):
            updated = (
                session.query(ScheduledActionRecord)
                .filter(ScheduledActionRecord.id == scheduled_action_id)
                .filter(ScheduledActionRecord.state == "pending")
                .update({"state": "processing"})
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
                    "error_message": None,
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
                })
            )

            session.commit()

            return {"success": True, "count": count, "error": None}

        except Exception as e:
            session.rollback()
            print(f"[ERROR] Database operation failed: {e}")
            return {"success": False, "count": 0, "error": str(e)}

        finally:
            session.close()


persistence_service = PersistenceService()
