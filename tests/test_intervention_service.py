import json
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError

from app.db.models import (
    AuditLogRecord,
    CallFlowRecord,
    IncidentRecord,
    ProcessedEventRecord,
    ScheduledActionRecord,
)
from app.services.intervention_service import (
    InterventionDataError,
    InterventionNotFound,
    InterventionRetryNotSafe,
    InterventionService,
)


NOW = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)


class FakeRuleLoader:
    def __init__(self, action=None):
        self.action = action

    def get_trigger_group(self, client, trigger):
        return "availability"

    def get_action(self, client, host, trigger_group):
        return self.action


class FakeQuery:
    def __init__(self, session, model):
        self.session = session
        self.model = getattr(model, "class_", model)

    def join(self, *args):
        return self

    def filter(self, *args):
        if self.session.fail_reads:
            raise SQLAlchemyError("password=database-secret")
        return self

    def order_by(self, *args):
        return self

    def limit(self, value):
        self._limit = value
        return self

    def all(self):
        rows = list(self.session.data.get(self.model, []))
        return rows[:getattr(self, "_limit", None)]

    def first(self):
        rows = self.session.data.get(self.model, [])
        return rows[0] if rows else None


class FakeSession:
    def __init__(self, data=None, fail_reads=False):
        self.data = data or {}
        self.fail_reads = fail_reads
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0

    def query(self, model):
        return FakeQuery(self, model)

    def get(self, model, record_id):
        if self.fail_reads:
            raise SQLAlchemyError("token=database-secret")
        return next(
            (row for row in self.data.get(model, []) if row.id == record_id),
            None,
        )

    def add(self, record):
        self.added.append(record)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closes += 1


def incident(event_id="event-call"):
    row = IncidentRecord(
        event_id=event_id,
        client="Client A",
        host="host-a",
        trigger="Host unavailable",
        trigger_group="availability",
        severity="High",
        current_status="open",
    )
    row.id = 1
    row.created_at = NOW - timedelta(hours=1)
    row.updated_at = NOW
    return row


def call_flow():
    row = CallFlowRecord(
        event_id="event-call",
        client="Client A",
        host="host-a",
        trigger="Host unavailable",
        severity="High",
        state="manual_required",
        attempt_count=3,
        max_attempts=3,
    )
    row.id = 4
    row.manual_required_at = NOW - timedelta(minutes=1)
    row.created_at = NOW - timedelta(hours=1)
    row.updated_at = NOW - timedelta(minutes=1)
    return row


def scheduled(record_id, state, detected_at, error=None):
    row = ScheduledActionRecord(
        event_id=f"event-scheduled-{record_id}",
        client="Client A",
        host="host-a",
        trigger="CPU high",
        trigger_group="capacity",
        severity="Warning",
        actions=["jira", "email"],
        target="noc-team",
        contacts_payload={"phone": "+15551234567", "token": "raw-secret"},
        state=state,
        attempt_count=2,
        error_message=error,
        last_error=error,
    )
    row.id = record_id
    row.created_at = detected_at - timedelta(minutes=5)
    row.scheduled_at = detected_at
    row.processing_started_at = detected_at if state == "processing" else None
    return row


def processed(record_id, state, detected_at, error=None):
    row = ProcessedEventRecord(
        event_id=f"event-processed-{record_id}",
        zabbix_status="PROBLEM",
        client="Client A",
        host="host-a",
        trigger="Disk full",
        severity="Average",
        state=state,
        processing_started_at=detected_at if state == "processing" else None,
        error_message=error,
    )
    row.id = record_id
    row.created_at = detected_at - timedelta(minutes=1)
    row.updated_at = detected_at
    row.last_seen_at = detected_at
    return row


class InterventionServiceTest(unittest.TestCase):
    def make_service(self, session, action=None):
        return InterventionService(
            session_factory=lambda: session,
            loader=FakeRuleLoader(action),
            now_provider=lambda: NOW,
        )

    def test_list_combines_exact_sources_sorts_limits_and_sanitizes(self):
        secret = '{"token":"hunter2","phone":"+15551234567"}'
        rows = {
            IncidentRecord: [incident()],
            CallFlowRecord: [call_flow()],
            ScheduledActionRecord: [
                scheduled(9, "failed", NOW - timedelta(minutes=2), secret),
                scheduled(8, "processing", NOW - timedelta(minutes=20), secret),
                scheduled(7, "pending", NOW, secret),
            ],
            ProcessedEventRecord: [
                processed(6, "failed", NOW - timedelta(minutes=3), secret),
                processed(5, "processing", NOW - timedelta(minutes=5), secret),
            ],
        }
        service = self.make_service(
            FakeSession(rows),
            action={"action": ["teams"], "target": "noc-team"},
        )

        result = service.list_interventions(limit=3)

        self.assertEqual(
            [item.intervention_id for item in result],
            ["call_flow:4", "processed_event:6", "scheduled_action:9"],
        )
        self.assertEqual(
            [item.status.value for item in result],
            ["manual_required", "failed", "failed"],
        )
        self.assertTrue(all(item.retry_supported is False for item in result))
        serialized = json.dumps([item.model_dump(mode="json") for item in result])
        self.assertNotIn("hunter2", serialized)
        self.assertNotIn("15551234567", serialized)
        self.assertNotIn("contacts_payload", serialized)
        description = service._safe_description(
            'Failure {"token":"hunter2","phone":"+15551234567"}'
        )
        self.assertNotIn("hunter2", description)
        self.assertNotIn("15551234567", description)

    def test_retry_rejection_is_audited_and_never_executes(self):
        row = scheduled(9, "failed", NOW - timedelta(minutes=2))
        session = FakeSession({
            IncidentRecord: [incident(row.event_id)],
            ScheduledActionRecord: [row],
        })
        service = self.make_service(session)

        with self.assertRaises(InterventionRetryNotSafe):
            service.reject_retry("scheduled_action:9")

        self.assertEqual(session.commits, 1)
        self.assertEqual(len(session.added), 1)
        audit = session.added[0]
        self.assertIsInstance(audit, AuditLogRecord)
        self.assertEqual(audit.details["reason"], "retry_not_safe")
        self.assertNotIn("dispatch", audit.details)

    def test_malformed_absent_and_no_longer_current_are_not_found(self):
        service = self.make_service(FakeSession())
        for value in ("bad", "scheduled_action:0", "unknown:1"):
            with self.subTest(value=value), self.assertRaises(InterventionNotFound):
                service.reject_retry(value)

        current = scheduled(2, "executed", NOW)
        service = self.make_service(
            FakeSession({ScheduledActionRecord: [current]})
        )
        with self.assertRaises(InterventionNotFound):
            service.reject_retry("scheduled_action:2")

        failed_without_open_incident = scheduled(
            3, "failed", NOW - timedelta(minutes=2)
        )
        service = self.make_service(FakeSession({
            ScheduledActionRecord: [failed_without_open_incident]
        }))
        with self.assertRaises(InterventionNotFound):
            service.reject_retry("scheduled_action:3")

    def test_persisted_runbook_is_allowlisted_and_audited(self):
        row = scheduled(9, "failed", NOW - timedelta(minutes=2))
        row.target = "operator@example.com"
        row.execution_mode = "delayed"
        row.approval_when = "always"
        row.pre_actions = ["telegram", "unknown"]
        row.pre_target = "+15551234567"
        session = FakeSession({
            IncidentRecord: [incident(row.event_id)],
            ScheduledActionRecord: [row],
        })

        result = self.make_service(session).get_runbook("scheduled_action:9")

        self.assertEqual(result.source, "persisted_action_plan")
        self.assertEqual(result.actions, ["jira", "email"])
        self.assertEqual(result.pre_actions, ["telegram"])
        self.assertIsNone(result.target)
        self.assertIsNone(result.pre_target)
        serialized = json.dumps(result.model_dump(mode="json"))
        self.assertNotIn("contacts", serialized)
        self.assertNotIn("15551234567", serialized)
        self.assertNotIn("raw-secret", serialized)
        self.assertEqual(session.added[0].message, "Intervention runbook viewed")

    def test_current_runbook_warns_and_excludes_contact_columns(self):
        row = processed(6, "failed", NOW - timedelta(minutes=3))
        action = {
            "action": ["teams"],
            "target": "noc-team",
            "delay_minutes": 4,
            "execution_mode": "manual_approval",
            "approval_when": "never",
            "contacts": [{"phone": "+15551234567"}],
            "secret": "raw-secret",
        }
        session = FakeSession({
            IncidentRecord: [incident(row.event_id)],
            ProcessedEventRecord: [row],
        })

        result = self.make_service(session, action).get_runbook(
            "processed_event:6"
        )

        self.assertEqual(result.source, "current_runbook")
        self.assertEqual(result.execution_mode, "manual_approval")
        self.assertIn("historical", result.warning)
        serialized = json.dumps(result.model_dump(mode="json"))
        self.assertNotIn("contacts", serialized)
        self.assertNotIn("raw-secret", serialized)

    def test_no_matching_runbook_returns_not_found_without_audit(self):
        row = processed(6, "failed", NOW - timedelta(minutes=3))
        session = FakeSession({ProcessedEventRecord: [row]})

        with self.assertRaises(InterventionNotFound):
            self.make_service(session, action=None).get_runbook(
                "processed_event:6"
            )

        self.assertEqual(session.added, [])

    def test_sqlalchemy_failures_are_controlled(self):
        session = FakeSession(fail_reads=True)
        with self.assertRaises(InterventionDataError):
            self.make_service(session).list_interventions()
        self.assertEqual(session.rollbacks, 1)
        self.assertEqual(session.closes, 1)


if __name__ == "__main__":
    unittest.main()
