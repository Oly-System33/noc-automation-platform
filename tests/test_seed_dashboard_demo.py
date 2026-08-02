import inspect
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from sqlalchemy import DateTime

from app.db.models import (
    CallFlowRecord,
    IncidentRecord,
    ProcessedEventRecord,
    ScheduledActionRecord,
)
from app.schemas.dashboard import DashboardStatus, resolve_dashboard_status
from scripts import seed_dashboard_demo as seed


NOW = datetime(2026, 8, 2, 6, 0, tzinfo=timezone.utc)


class FakeQuery:

    def __init__(self, session, model):
        self.session = session
        self.model = model
        self.prefix = None

    def filter(self, expression):
        value = getattr(getattr(expression, "right", None), "value", None)
        self.prefix = str(value or "").removesuffix("%")
        return self

    def delete(self, synchronize_session=False):
        del synchronize_session
        records = self.session.data.setdefault(self.model, [])
        kept = [
            record for record in records
            if not str(getattr(record, "event_id", "") or "").startswith(
                self.prefix
            )
        ]
        removed = len(records) - len(kept)
        self.session.data[self.model] = kept
        return removed


class FakeSession:

    def __init__(self, data=None):
        self.data = data or {}
        self.query_order = []
        self.commit_count = 0
        self.rollback_count = 0
        self.close_count = 0

    def query(self, model):
        self.query_order.append(model)
        return FakeQuery(self, model)

    def add_all(self, records):
        for record in records:
            self.data.setdefault(type(record), []).append(record)

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1

    def close(self):
        self.close_count += 1


def visible_statuses(records_by_model):
    incidents = {
        record.event_id: record
        for record in records_by_model[IncidentRecord]
    }
    scheduled = {
        record.event_id: record
        for record in records_by_model[ScheduledActionRecord]
    }
    calls = {
        record.event_id: record
        for record in records_by_model[CallFlowRecord]
    }
    processed = {
        record.event_id: record
        for record in records_by_model[ProcessedEventRecord]
    }
    statuses = {}

    for event_id, incident in incidents.items():
        action = scheduled.get(event_id)
        call = calls.get(event_id)
        processed_event = processed.get(event_id)
        statuses[event_id] = resolve_dashboard_status(
            incident_status=incident.current_status,
            processed_event_state=(
                processed_event.state if processed_event else None
            ),
            processed_event_started_at=(
                processed_event.processing_started_at
                if processed_event else None
            ),
            scheduled_action_state=action.state if action else None,
            scheduled_action_states=[action.state] if action else [],
            scheduled_action_processing_started_at=(
                action.processing_started_at if action else None
            ),
            call_flow_state=call.state if call else None,
            now=NOW,
            processing_timeout_minutes=seed.PROCESSING_TIMEOUT_MINUTES,
        )

    return statuses


class DashboardDemoRecordTest(unittest.TestCase):

    def setUp(self):
        self.records = seed.build_demo_records(now=NOW)

    def test_demo_prefix_and_complete_state_set_are_stable(self):
        self.assertEqual(seed.DEMO_EVENT_PREFIX, "demo-dashboard-")
        self.assertEqual(len(self.records[IncidentRecord]), 12)
        self.assertEqual(
            {
                record.event_id
                for record in self.records[IncidentRecord]
            },
            {
                f"demo-dashboard-{status}"
                for status in seed.EXPECTED_STATUSES
            },
        )

    def test_all_datetime_columns_are_timezone_aware(self):
        for records in self.records.values():
            for record in records:
                for column in record.__table__.columns:
                    if not isinstance(column.type, DateTime):
                        continue

                    value = getattr(record, column.name)

                    if value is not None:
                        self.assertIsNotNone(
                            value.tzinfo,
                            f"{record.__tablename__}.{column.name}",
                        )

        for incident in self.records[IncidentRecord]:
            self.assertIsNotNone(
                datetime.fromisoformat(incident.opened_at).tzinfo
            )

    def test_records_resolve_to_every_expected_dashboard_status(self):
        statuses = visible_statuses(self.records)

        self.assertEqual(
            set(statuses.values()),
            {DashboardStatus(status) for status in seed.EXPECTED_STATUSES},
        )

        for status in seed.EXPECTED_STATUSES:
            self.assertEqual(
                statuses[seed.demo_event_id(status)],
                DashboardStatus(status),
            )

    def test_executing_is_recent_and_stuck_exceeds_timeout(self):
        actions = {
            record.event_id: record
            for record in self.records[ScheduledActionRecord]
        }
        processed = self.records[ProcessedEventRecord][0]
        executing = actions[seed.demo_event_id("executing")]

        self.assertGreater(
            executing.processing_started_at,
            NOW - timedelta(
                minutes=seed.PROCESSING_TIMEOUT_MINUTES
            ),
        )
        self.assertLessEqual(
            processed.processing_started_at,
            NOW - timedelta(
                minutes=seed.PROCESSING_TIMEOUT_MINUTES
            ),
        )

    def test_scheduled_paused_closed_and_call_states_are_explicit(self):
        statuses = visible_statuses(self.records)

        expected = {
            "scheduled": DashboardStatus.SCHEDULED,
            "paused": DashboardStatus.PAUSED,
            "closed": DashboardStatus.CLOSED,
            "waiting_confirmation": DashboardStatus.WAITING_CONFIRMATION,
            "retry_scheduled": DashboardStatus.RETRY_SCHEDULED,
            "manual_required": DashboardStatus.MANUAL_REQUIRED,
        }

        for name, status in expected.items():
            with self.subTest(name=name):
                self.assertEqual(statuses[seed.demo_event_id(name)], status)

    def test_values_are_synthetic_and_contain_no_contact_data(self):
        all_records = [
            record
            for records in self.records.values()
            for record in records
        ]

        for record in all_records:
            self.assertTrue(record.event_id.startswith(seed.DEMO_EVENT_PREFIX))
            if hasattr(record, "client"):
                self.assertEqual(record.client, seed.DEMO_CLIENT)

        for call in self.records[CallFlowRecord]:
            self.assertIsNone(call.phone)
            self.assertIsNone(call.summary_payload)

        for action in self.records[ScheduledActionRecord]:
            self.assertIsNone(action.contacts_payload)
            self.assertEqual(action.actions, ["demo_action"])

        self.assertNotIn("Banco X", inspect.getsource(seed))

    def test_script_does_not_import_or_invoke_operational_services(self):
        source = inspect.getsource(seed)
        forbidden = (
            "EventProcessor",
            "RuleEngine",
            "ActionDispatcher",
            "ScheduledActionWorker",
            "VonageService",
            "JiraService",
            "TelegramService",
            "TeamsService",
            "EmailService",
        )

        for name in forbidden:
            self.assertNotIn(name, source)


class DashboardDemoPersistenceTest(unittest.TestCase):

    def test_running_seed_twice_replaces_instead_of_duplicating(self):
        real_incident = IncidentRecord(
            event_id="real-event-1",
            client="Real Client",
            current_status="open",
        )
        session = FakeSession({IncidentRecord: [real_incident]})

        seed.seed_demo_data(session_factory=lambda: session, now=NOW)
        seed.seed_demo_data(session_factory=lambda: session, now=NOW)

        incidents = session.data[IncidentRecord]
        demo_incidents = [
            record for record in incidents
            if record.event_id.startswith(seed.DEMO_EVENT_PREFIX)
        ]
        self.assertEqual(len(demo_incidents), 12)
        self.assertIn(real_incident, incidents)
        self.assertEqual(session.commit_count, 2)

    def test_clean_removes_only_demo_records_in_safe_order(self):
        records = seed.build_demo_records(now=NOW)
        real_incident = IncidentRecord(
            event_id="real-event-1",
            client="Real Client",
            current_status="open",
        )
        records[IncidentRecord].append(real_incident)
        session = FakeSession(records)

        removed = seed.clean_demo_records(session_factory=lambda: session)

        self.assertEqual(session.query_order, list(seed.CLEANUP_MODELS))
        self.assertEqual(sum(removed.values()), 34)
        self.assertEqual(session.data[IncidentRecord], [real_incident])
        self.assertTrue(all(
            not record.event_id.startswith(seed.DEMO_EVENT_PREFIX)
            for model_records in session.data.values()
            for record in model_records
        ))

    def test_clean_cli_does_not_seed_again(self):
        with patch.object(
            seed,
            "clean_demo_records",
            return_value={"incidents": 12},
        ) as clean:
            with patch.object(seed, "seed_demo_data") as seed_data:
                result = seed.main(["--clean"])

        self.assertEqual(result, 0)
        clean.assert_called_once_with()
        seed_data.assert_not_called()


class DashboardDemoVerificationTest(unittest.TestCase):

    def build_service(self, statuses):
        service = MagicMock()
        service.list_incidents.return_value = SimpleNamespace(
            items=[
                SimpleNamespace(
                    event_id=seed.demo_event_id(status),
                    display_status=DashboardStatus(status),
                )
                for status in statuses
            ]
        )
        return service

    def test_verify_accepts_complete_demo_state_set(self):
        service = self.build_service(seed.EXPECTED_STATUSES)

        result = seed.verify_demo_data(
            query_service=service,
            output=None,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["missing"], [])
        service.list_incidents.assert_called_once_with(
            limit=100,
            client=seed.DEMO_CLIENT,
        )

    def test_verify_detects_missing_state_and_cli_returns_nonzero(self):
        service = self.build_service(seed.EXPECTED_STATUSES[:-1])
        verification = seed.verify_demo_data(
            query_service=service,
            output=None,
        )

        self.assertFalse(verification["success"])
        self.assertEqual(verification["missing"], ["closed"])

        with patch.object(
            seed,
            "verify_demo_data",
            return_value={"success": False},
        ):
            self.assertEqual(seed.main(["--verify"]), 1)


if __name__ == "__main__":
    unittest.main()
