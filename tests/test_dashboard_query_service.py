import json
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError

from app.db.models import (
    ActionRecord,
    CallFlowRecord,
    EventRecord,
    IncidentRecord,
    ProcessedEventRecord,
    ScheduledActionRecord,
)
from app.schemas.dashboard import DashboardOperationStatus, DashboardStatus
from app.services.dashboard_query_service import (
    DashboardQueryError,
    DashboardQueryService,
)


NOW = datetime(2026, 8, 2, 3, 0, tzinfo=timezone.utc)


class FakeQuery:

    def __init__(self, session, model, rows):
        self.session = session
        self.model = model
        self.rows = list(rows)
        self.limit_value = None

    def count(self):
        self.session.execute(self.model, "count")
        return len(self.rows)

    def order_by(self, *args):
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def filter(self, *args):
        return self

    def all(self):
        self.session.execute(self.model, "all")
        rows = sorted(
            self.rows,
            key=lambda record: (
                getattr(record, "updated_at", None)
                or getattr(record, "created_at", None)
                or datetime.min.replace(tzinfo=timezone.utc),
                getattr(record, "id", 0) or 0,
            ),
            reverse=True,
        )

        if self.limit_value is not None:
            rows = rows[:self.limit_value]

        return rows


class FakeSession:

    def __init__(self, data=None, fail_on_execution=None):
        self.data = data or {}
        self.fail_on_execution = fail_on_execution
        self.execution_count = 0
        self.executions = []
        self.rollback_count = 0
        self.close_count = 0
        self.commit_count = 0

    def query(self, model):
        return FakeQuery(self, model, self.data.get(model, []))

    def execute(self, model, operation):
        self.execution_count += 1
        self.executions.append((model, operation))

        if self.execution_count == self.fail_on_execution:
            raise SQLAlchemyError("database read failed")

    def rollback(self):
        self.rollback_count += 1

    def close(self):
        self.close_count += 1

    def commit(self):
        self.commit_count += 1


def make_incident(
    event_id="event-1",
    *,
    record_id=1,
    state="open",
    client="Banco X",
    updated_at=NOW,
    opened_at="2026-08-02T02:00:00+00:00",
):
    record = IncidentRecord(
        event_id=event_id,
        client=client,
        host="host-1",
        trigger="trigger-1",
        severity="High",
        opened_at=opened_at,
        current_status=state,
    )
    record.id = record_id
    record.created_at = updated_at - timedelta(hours=1)
    record.updated_at = updated_at
    return record


def make_event(event_id="event-1", *, record_id=1, status="1"):
    record = EventRecord(
        event_id=event_id,
        client="Event Client",
        host="event-host",
        trigger="event-trigger",
        severity="Warning",
        status=status,
        timestamp="2026-08-02T02:00:00+00:00",
    )
    record.id = record_id
    record.created_at = NOW - timedelta(minutes=30)
    return record


def make_processed(
    state,
    *,
    event_id="event-1",
    record_id=1,
    started_at=None,
    updated_at=NOW,
    error=None,
):
    record = ProcessedEventRecord(
        event_id=event_id,
        zabbix_status="PROBLEM",
        state=state,
        processing_started_at=started_at,
        error_message=error,
    )
    record.id = record_id
    record.created_at = updated_at - timedelta(minutes=5)
    record.updated_at = updated_at
    record.last_seen_at = updated_at
    record.processed_at = updated_at if state == "processed" else None
    return record


def make_scheduled(
    state,
    *,
    event_id="event-1",
    record_id=1,
    activity_at=NOW,
    actions=None,
    error=None,
    client="Banco X",
    host="host-1",
    trigger="trigger-1",
    severity="High",
):
    record = ScheduledActionRecord(
        event_id=event_id,
        client=client,
        host=host,
        trigger=trigger,
        severity=severity,
        state=state,
        actions=actions if actions is not None else ["telegram"],
        target="noc",
        scheduled_at=activity_at,
        attempt_count=2,
        error_message=error,
        last_error=error,
    )
    record.id = record_id
    record.created_at = activity_at - timedelta(minutes=5)
    record.processing_started_at = (
        activity_at if state == "processing" else None
    )
    record.paused_at = activity_at if state == "paused" else None
    record.resumed_at = activity_at if state == "processing" else None
    record.executed_at = activity_at if state == "executed" else None
    record.cancelled_at = activity_at if state == "cancelled" else None
    return record


def make_call(
    state,
    *,
    event_id="event-1",
    record_id=1,
    updated_at=NOW,
    phone="5491100000000",
):
    record = CallFlowRecord(
        event_id=event_id,
        state=state,
        target="guardia",
        phone=phone,
        attempt_count=3,
    )
    record.id = record_id
    record.created_at = updated_at - timedelta(minutes=5)
    record.updated_at = updated_at
    return record


def make_action(
    *,
    event_id="event-1",
    record_id=1,
    status="success",
    error=None,
):
    record = ActionRecord(
        event_id=event_id,
        action_type="jira",
        target="NOC",
        status=status,
        error_message=error,
    )
    record.id = record_id
    record.created_at = NOW
    return record


class DashboardQueryServiceTest(unittest.TestCase):

    def build_service(self, data, fail_on_execution=None):
        session = FakeSession(data, fail_on_execution=fail_on_execution)
        service = DashboardQueryService(
            session_factory=lambda: session,
            processing_timeout_minutes=10,
            now_provider=lambda: NOW,
        )
        return service, session

    def list_one(self, *, incident=None, processed=None, scheduled=None, calls=None, events=None, actions=None):
        data = {
            IncidentRecord: [incident or make_incident()],
            EventRecord: events or [],
            ProcessedEventRecord: processed or [],
            ScheduledActionRecord: scheduled or [],
            CallFlowRecord: calls or [],
            ActionRecord: actions or [],
        }
        service, session = self.build_service(data)
        response = service.list_incidents()
        return response.items[0], response, session

    def test_open_incident_without_operations_is_active(self):
        item, _, _ = self.list_one()

        self.assertEqual(item.display_status, DashboardStatus.ACTIVE)

    def test_incident_and_event_fields_are_mapped_from_real_columns(self):
        incident = make_incident()
        incident.client = None
        incident.host = None
        incident.trigger = None
        incident.severity = None
        item, _, _ = self.list_one(
            incident=incident,
            events=[make_event()],
        )

        self.assertEqual(item.event_id, "event-1")
        self.assertEqual(item.client, "Event Client")
        self.assertEqual(item.host, "event-host")
        self.assertEqual(item.trigger, "event-trigger")
        self.assertEqual(item.severity, "Warning")
        self.assertEqual(item.incident_status, "open")
        self.assertEqual(item.opened_at.isoformat(), "2026-08-02T02:00:00+00:00")
        self.assertEqual(item.updated_at, NOW)

    def test_invalid_opened_at_uses_valid_problem_event_timestamp(self):
        incident = make_incident(opened_at="03:00:00")
        item, _, _ = self.list_one(
            incident=incident,
            events=[make_event()],
        )

        self.assertEqual(item.opened_at.isoformat(), "2026-08-02T02:00:00+00:00")

    def test_invalid_dates_without_event_fallback_become_none(self):
        incident = make_incident(opened_at="03:00:00")
        item, _, _ = self.list_one(incident=incident)

        self.assertIsNone(item.opened_at)

    def test_scheduled_action_states_map_to_visible_statuses(self):
        cases = [
            ("pending", NOW + timedelta(hours=1), DashboardStatus.SCHEDULED),
            ("paused", NOW, DashboardStatus.PAUSED),
            ("processing", NOW - timedelta(minutes=1), DashboardStatus.EXECUTING),
            ("processing", NOW - timedelta(minutes=11), DashboardStatus.STUCK),
            ("failed", NOW, DashboardStatus.FAILED),
            ("pending_approval", NOW, DashboardStatus.PENDING_APPROVAL),
        ]

        for state, activity_at, expected in cases:
            with self.subTest(state=state, expected=expected):
                item, _, _ = self.list_one(
                    scheduled=[make_scheduled(state, activity_at=activity_at)]
                )
                self.assertEqual(item.display_status, expected)

        future_item, _, _ = self.list_one(
            scheduled=[
                make_scheduled(
                    "pending",
                    activity_at=NOW + timedelta(hours=2),
                )
            ]
        )
        self.assertNotEqual(future_item.display_status, DashboardStatus.PAUSED)

    def test_call_flow_states_map_to_visible_statuses(self):
        cases = [
            ("waiting_confirmation", DashboardStatus.WAITING_CONFIRMATION),
            ("retry_scheduled", DashboardStatus.RETRY_SCHEDULED),
            ("manual_required", DashboardStatus.MANUAL_REQUIRED),
            ("calling", DashboardStatus.EXECUTING),
        ]

        for state, expected in cases:
            with self.subTest(state=state):
                item, _, _ = self.list_one(calls=[make_call(state)])
                self.assertEqual(item.display_status, expected)
                self.assertEqual(item.call_flow_state, state)
                self.assertEqual(item.attempt_count, 3)

    def test_closed_incident_overrides_all_operations(self):
        item, _, _ = self.list_one(
            incident=make_incident(state="closed"),
            processed=[
                make_processed(
                    "processing",
                    started_at=NOW - timedelta(hours=1),
                )
            ],
            scheduled=[make_scheduled("failed", error="failed")],
            calls=[make_call("manual_required")],
        )

        self.assertEqual(item.display_status, DashboardStatus.CLOSED)

    def test_relevant_scheduled_action_uses_operational_precedence(self):
        cases = [
            (["paused", "failed"], DashboardStatus.FAILED, "failed"),
            (["paused", "processing"], DashboardStatus.EXECUTING, "processing"),
            (["pending", "paused"], DashboardStatus.PAUSED, "paused"),
        ]

        for states, expected_status, selected_state in cases:
            with self.subTest(states=states):
                records = [
                    make_scheduled(
                        state,
                        record_id=index + 1,
                        activity_at=NOW - timedelta(minutes=index + 1),
                    )
                    for index, state in enumerate(states)
                ]
                item, _, _ = self.list_one(scheduled=records)

                self.assertEqual(item.display_status, expected_status)
                self.assertEqual(item.scheduled_action_state, selected_state)

    def test_stale_processing_action_has_highest_operational_priority(self):
        stale = make_scheduled(
            "processing",
            record_id=1,
            activity_at=NOW - timedelta(hours=1),
        )
        failed = make_scheduled("failed", record_id=2, activity_at=NOW)
        item, _, _ = self.list_one(scheduled=[failed, stale])

        self.assertEqual(item.display_status, DashboardStatus.STUCK)
        self.assertEqual(item.scheduled_action_id, 1)
        self.assertEqual(item.stuck_since, NOW - timedelta(hours=1))

    def test_equal_priority_uses_latest_activity_then_highest_id(self):
        older = make_scheduled(
            "paused",
            record_id=10,
            activity_at=NOW - timedelta(minutes=2),
        )
        newer = make_scheduled(
            "paused",
            record_id=5,
            activity_at=NOW - timedelta(minutes=1),
        )
        item, _, _ = self.list_one(scheduled=[older, newer])
        self.assertEqual(item.scheduled_action_id, 5)

        same_time_lower_id = make_scheduled("paused", record_id=20)
        same_time_higher_id = make_scheduled("paused", record_id=21)
        item, _, _ = self.list_one(
            scheduled=[same_time_lower_id, same_time_higher_id]
        )
        self.assertEqual(item.scheduled_action_id, 21)

    def test_call_flow_selection_uses_priority_then_recency_and_id(self):
        waiting = make_call("waiting_confirmation", record_id=1, updated_at=NOW)
        manual = make_call(
            "manual_required",
            record_id=2,
            updated_at=NOW - timedelta(hours=1),
        )
        item, _, _ = self.list_one(calls=[waiting, manual])
        self.assertEqual(item.call_flow_state, "manual_required")

        lower = make_call("calling", record_id=3, updated_at=NOW)
        higher = make_call("calling", record_id=4, updated_at=NOW)
        item, _, _ = self.list_one(calls=[lower, higher])
        self.assertEqual(item.call_flow_state, "calling")
        self.assertEqual(item.attempt_count, 3)

    def test_processed_event_selection_uses_priority_and_is_deterministic(self):
        stale = make_processed(
            "processing",
            record_id=1,
            started_at=NOW - timedelta(hours=1),
            updated_at=NOW - timedelta(hours=1),
        )
        failed = make_processed("failed", record_id=2, error="failure")
        item, _, _ = self.list_one(processed=[failed, stale])
        self.assertEqual(item.display_status, DashboardStatus.STUCK)

        lower = make_processed("failed", record_id=5, error="lower")
        higher = make_processed("failed", record_id=6, error="higher")
        item, _, _ = self.list_one(processed=[lower, higher])
        self.assertEqual(item.display_status, DashboardStatus.FAILED)
        self.assertEqual(item.error_message, "higher")

    def test_stuck_since_uses_earliest_processing_started_at(self):
        processed = make_processed(
            "processing",
            started_at=NOW - timedelta(minutes=20),
        )
        scheduled = make_scheduled(
            "processing",
            activity_at=NOW - timedelta(minutes=30),
        )
        item, _, _ = self.list_one(
            processed=[processed],
            scheduled=[scheduled],
        )

        self.assertEqual(item.stuck_since, NOW - timedelta(minutes=30))

    def test_scheduled_fields_and_action_fallback_are_mapped(self):
        scheduled = make_scheduled(
            "paused",
            record_id=15,
            actions=["jira", "telegram"],
        )
        item, _, _ = self.list_one(scheduled=[scheduled])

        self.assertEqual(item.current_action, "jira, telegram")
        self.assertEqual(item.target, "noc")
        self.assertEqual(item.scheduled_action_id, 15)
        self.assertEqual(item.paused_at, NOW)
        self.assertEqual(item.attempt_count, 2)

        fallback_item, _, _ = self.list_one(actions=[make_action()])
        self.assertEqual(fallback_item.current_action, "jira")
        self.assertIsNone(fallback_item.target)

    def test_call_driven_status_uses_call_action_and_target(self):
        scheduled = make_scheduled(
            "paused",
            actions=["telegram"],
        )
        call = make_call("waiting_confirmation")
        item, _, _ = self.list_one(
            scheduled=[scheduled],
            calls=[call],
        )

        self.assertEqual(
            item.display_status,
            DashboardStatus.WAITING_CONFIRMATION,
        )
        self.assertEqual(item.current_action, "calls")
        self.assertEqual(item.target, "guardia")
        self.assertEqual(item.attempt_count, 3)

    def test_malformed_actions_are_not_stringified(self):
        scheduled = make_scheduled("paused", actions={"phone": "secret"})
        item, _, _ = self.list_one(scheduled=[scheduled])

        self.assertIsNone(item.current_action)

    def test_phone_and_sensitive_payloads_are_not_serialized(self):
        item, _, _ = self.list_one(
            calls=[make_call("waiting_confirmation", phone="5491112345678")]
        )
        payload = item.model_dump_json()

        self.assertNotIn("5491112345678", payload)
        self.assertNotIn("phone", payload)

        call_action = make_action(status="failed")
        call_action.action_type = "calls"
        call_action.target = "5491199999999"
        action_item, _, _ = self.list_one(actions=[call_action])
        action_payload = action_item.model_dump_json()
        self.assertNotIn("5491199999999", action_payload)

    def test_errors_are_sanitized_and_limited(self):
        error = (
            "password=super-secret "
            "https://user:pass@example.com/path "
            "token=abc123 client_secret=client-value "
            "Authorization: Basic encoded-value\n"
            + ("x" * 1000)
        )
        scheduled = make_scheduled("failed", error=error)
        item, _, _ = self.list_one(scheduled=[scheduled])

        self.assertLessEqual(len(item.error_message), 500)
        self.assertNotIn("super-secret", item.error_message)
        self.assertNotIn("user:pass", item.error_message)
        self.assertNotIn("abc123", item.error_message)
        self.assertNotIn("client-value", item.error_message)
        self.assertNotIn("encoded-value", item.error_message)
        self.assertNotIn("\n", item.error_message)

    def test_stuck_since_aggregates_all_processed_events(self):
        newer = make_processed(
            "processing",
            record_id=2,
            started_at=NOW - timedelta(minutes=20),
            updated_at=NOW,
            error="newer",
        )
        older = make_processed(
            "processing",
            record_id=1,
            started_at=NOW - timedelta(minutes=40),
            updated_at=NOW - timedelta(minutes=1),
            error="older",
        )
        item, _, _ = self.list_one(processed=[newer, older])

        self.assertEqual(item.display_status, DashboardStatus.STUCK)
        self.assertEqual(item.stuck_since, NOW - timedelta(minutes=40))
        self.assertEqual(item.error_message, "older")

    def test_unknown_states_sort_after_known_terminal_states(self):
        unknown = make_scheduled("future_state", record_id=20)
        executed = make_scheduled("executed", record_id=10)
        item, _, _ = self.list_one(scheduled=[unknown, executed])

        self.assertEqual(item.scheduled_action_state, "executed")

    def test_list_total_is_global_while_items_respect_limit(self):
        incidents = [
            make_incident(
                event_id=f"event-{index}",
                record_id=index,
                updated_at=NOW - timedelta(minutes=index),
            )
            for index in range(1, 4)
        ]
        service, session = self.build_service({IncidentRecord: incidents})

        response = service.list_incidents(limit=1)

        self.assertEqual(response.total, 3)
        self.assertEqual(len(response.items), 1)
        self.assertEqual(response.items[0].event_id, "event-1")
        self.assertEqual(session.execution_count, 7)

    def test_limit_is_clamped_to_supported_range(self):
        incidents = [
            make_incident(event_id=f"event-{index}", record_id=index)
            for index in range(1, 503)
        ]
        service, _ = self.build_service({IncidentRecord: incidents})

        response = service.list_incidents(limit=1000)

        self.assertEqual(len(response.items), 500)
        self.assertEqual(response.total, 502)

    def test_status_filter_is_applied_before_limit_and_total(self):
        incidents = [
            make_incident("active", record_id=1, updated_at=NOW),
            make_incident(
                "paused-newer",
                record_id=2,
                updated_at=NOW - timedelta(minutes=1),
            ),
            make_incident(
                "paused-older",
                record_id=3,
                updated_at=NOW - timedelta(minutes=2),
            ),
        ]
        scheduled = [
            make_scheduled("paused", event_id="paused-newer"),
            make_scheduled("paused", event_id="paused-older", record_id=2),
        ]
        service, session = self.build_service({
            IncidentRecord: incidents,
            ScheduledActionRecord: scheduled,
        })

        response = service.list_incidents(
            limit=1,
            status=DashboardStatus.PAUSED,
        )

        self.assertEqual(response.total, 2)
        self.assertEqual(
            [item.event_id for item in response.items],
            ["paused-newer"],
        )
        self.assertEqual(session.execution_count, 6)

    def test_client_filter_is_exact_case_insensitive_and_before_limit(self):
        incidents = [
            make_incident("banco-x-newer", record_id=1, client="Banco X"),
            make_incident(
                "other",
                record_id=2,
                client="Banco XY",
                updated_at=NOW - timedelta(minutes=1),
            ),
            make_incident(
                "banco-x-older",
                record_id=3,
                client="banco x",
                updated_at=NOW - timedelta(minutes=2),
            ),
        ]
        service, _ = self.build_service({IncidentRecord: incidents})

        response = service.list_incidents(limit=1, client=" BANCO X ")

        self.assertEqual(response.total, 2)
        self.assertEqual(
            [item.event_id for item in response.items],
            ["banco-x-newer"],
        )

    def test_combined_filters_and_empty_results(self):
        incidents = [
            make_incident("matching", record_id=1, client="Banco X"),
            make_incident("active", record_id=2, client="Banco X"),
            make_incident("other-client", record_id=3, client="Banco Y"),
        ]
        scheduled = [
            make_scheduled("paused", event_id="matching"),
            make_scheduled("paused", event_id="other-client", record_id=2),
        ]
        service, _ = self.build_service({
            IncidentRecord: incidents,
            ScheduledActionRecord: scheduled,
        })

        response = service.list_incidents(
            client="banco x",
            status=DashboardStatus.PAUSED,
        )
        empty = service.list_incidents(client="missing")

        self.assertEqual(response.total, 1)
        self.assertEqual(response.items[0].event_id, "matching")
        self.assertEqual(empty.total, 0)
        self.assertEqual(empty.items, [])

    def test_query_count_is_constant_and_empty_skips_related_queries(self):
        for incident_count in (1, 100):
            with self.subTest(incident_count=incident_count):
                incidents = [
                    make_incident(
                        event_id=f"event-{index}",
                        record_id=index,
                    )
                    for index in range(incident_count)
                ]
                service, session = self.build_service({
                    IncidentRecord: incidents,
                })
                service.list_incidents()
                self.assertEqual(session.execution_count, 7)

        service, session = self.build_service({IncidentRecord: []})
        response = service.list_incidents()
        self.assertEqual(response.items, [])
        self.assertEqual(response.total, 0)
        self.assertEqual(session.execution_count, 2)

    def test_summary_counts_each_incident_once_and_groups_clients(self):
        incidents = [
            make_incident("active", record_id=1, client="Banco X"),
            make_incident("paused", record_id=2, client="Banco X"),
            make_incident("closed", record_id=3, client=None, state="closed"),
        ]
        scheduled = [
            make_scheduled("paused", event_id="paused"),
            make_scheduled("pending", event_id="paused", record_id=2),
        ]
        service, session = self.build_service({
            IncidentRecord: incidents,
            ScheduledActionRecord: scheduled,
        })

        summary = service.get_summary()

        self.assertEqual(summary.total, 3)
        self.assertEqual(summary.counts.active, 1)
        self.assertEqual(summary.counts.paused, 1)
        self.assertEqual(summary.counts.closed, 1)
        self.assertEqual(summary.counts.failed, 0)
        self.assertEqual(summary.by_client, {"Banco X": 2, "unknown": 1})
        self.assertEqual(sum(summary.counts.model_dump().values()), 3)
        self.assertEqual(session.execution_count, 6)

    def test_operations_expand_actions_and_map_available_data(self):
        scheduled = make_scheduled(
            "paused",
            record_id=42,
            actions=["jira", "telegram"],
            client=None,
            host=None,
            trigger=None,
            severity=None,
            error="token=secret database unavailable",
        )
        scheduled.pause_reason = "manual_pause"
        scheduled.contacts_payload = {
            "phone": "5491112345678",
            "email": "secret@example.com",
        }
        incident = make_incident(
            client="Banco X",
            state="open",
        )
        service, session = self.build_service({
            ScheduledActionRecord: [scheduled],
            IncidentRecord: [incident],
        })

        response = service.list_operations()

        self.assertEqual(response.total, 2)
        self.assertEqual(
            [item.action for item in response.items],
            ["jira", "telegram"],
        )
        item = response.items[0]
        self.assertEqual(item.scheduled_action_id, 42)
        self.assertEqual(item.client, "Banco X")
        self.assertEqual(item.host, "host-1")
        self.assertEqual(item.incident_status, "open")
        self.assertEqual(item.display_status, DashboardOperationStatus.PAUSED)
        self.assertEqual(item.pause_reason, "manual_pause")
        payload = item.model_dump_json()
        self.assertNotIn("5491112345678", payload)
        self.assertNotIn("secret@example.com", payload)
        self.assertNotIn("token=secret", payload)
        self.assertEqual(session.execution_count, 2)

    def test_operation_statuses_include_stuck_resumed_and_executed(self):
        stale = make_scheduled(
            "processing",
            event_id="stale",
            record_id=1,
            activity_at=NOW - timedelta(minutes=11),
        )
        resumed = make_scheduled(
            "processing",
            event_id="resumed",
            record_id=2,
            activity_at=NOW - timedelta(minutes=1),
        )
        executed = make_scheduled(
            "executed",
            event_id="executed",
            record_id=3,
            activity_at=NOW,
        )
        service, _ = self.build_service({
            ScheduledActionRecord: [stale, resumed, executed],
        })

        response = service.list_operations()
        status_by_event = {
            item.event_id: item.display_status for item in response.items
        }

        self.assertEqual(
            status_by_event["stale"],
            DashboardOperationStatus.STUCK,
        )
        self.assertEqual(
            status_by_event["resumed"],
            DashboardOperationStatus.EXECUTING,
        )
        self.assertEqual(
            status_by_event["executed"],
            DashboardOperationStatus.EXECUTED,
        )

    def test_operations_filter_order_total_and_limit(self):
        older = make_scheduled(
            "paused",
            event_id="older",
            record_id=1,
            activity_at=NOW - timedelta(minutes=2),
            client="Banco X",
        )
        newer = make_scheduled(
            "paused",
            event_id="newer",
            record_id=2,
            activity_at=NOW - timedelta(minutes=1),
            client="banco x",
        )
        other = make_scheduled(
            "failed",
            event_id="other",
            record_id=3,
            activity_at=NOW,
            client="Banco Y",
        )
        service, _ = self.build_service({
            ScheduledActionRecord: [older, newer, other],
        })

        response = service.list_operations(
            limit=1,
            client=" BANCO X ",
            status=DashboardOperationStatus.PAUSED,
        )

        self.assertEqual(response.total, 2)
        self.assertEqual(len(response.items), 1)
        self.assertEqual(response.items[0].event_id, "newer")

    def test_operation_query_count_is_constant_and_unknown_state_is_skipped(self):
        records = [
            make_scheduled(
                "pending",
                event_id=f"event-{index}",
                record_id=index,
            )
            for index in range(1, 101)
        ]
        records.append(
            make_scheduled(
                "unknown",
                event_id="unknown",
                record_id=101,
            )
        )
        service, session = self.build_service({
            ScheduledActionRecord: records,
        })

        response = service.list_operations()

        self.assertEqual(response.total, 100)
        self.assertEqual(session.execution_count, 2)

    def test_approvals_only_include_internal_pending_approval(self):
        states = [
            "pending_approval",
            "manual_required",
            "waiting_confirmation",
            "paused",
            "pending",
        ]
        records = [
            make_scheduled(
                state,
                event_id=state,
                record_id=index,
                client="Banco X" if index < 3 else "Banco Y",
                actions=["jira", "telegram"] if index == 1 else None,
            )
            for index, state in enumerate(states, start=1)
        ]
        service, session = self.build_service({
            ScheduledActionRecord: records,
        })

        response = service.list_approvals(limit=1, client="banco x")

        self.assertEqual(response.total, 2)
        self.assertEqual(len(response.items), 1)
        self.assertTrue(all(
            item.internal_state == "pending_approval"
            for item in response.items
        ))
        self.assertEqual(session.execution_count, 2)

    def test_operation_database_errors_raise_controlled_exception(self):
        for fail_on_execution in (1, 2):
            with self.subTest(fail_on_execution=fail_on_execution):
                service, session = self.build_service(
                    {ScheduledActionRecord: [make_scheduled("pending")]},
                    fail_on_execution=fail_on_execution,
                )

                with self.assertRaisesRegex(
                    DashboardQueryError,
                    "dashboard_query_failed",
                ):
                    service.list_operations()

                self.assertEqual(session.rollback_count, 1)
                self.assertEqual(session.close_count, 1)
                self.assertEqual(session.commit_count, 0)

    def test_successful_reads_close_without_commit_or_rollback(self):
        _, _, session = self.list_one()

        self.assertEqual(session.close_count, 1)
        self.assertEqual(session.commit_count, 0)
        self.assertEqual(session.rollback_count, 0)

    def test_database_errors_raise_controlled_exception_and_close_session(self):
        for fail_on_execution in range(1, 8):
            with self.subTest(fail_on_execution=fail_on_execution):
                data = {IncidentRecord: [make_incident()]}
                service, session = self.build_service(
                    data,
                    fail_on_execution=fail_on_execution,
                )

                with self.assertRaisesRegex(
                    DashboardQueryError,
                    "dashboard_query_failed",
                ):
                    service.list_incidents()

                self.assertEqual(session.rollback_count, 1)
                self.assertEqual(session.close_count, 1)
                self.assertEqual(session.commit_count, 0)


if __name__ == "__main__":
    unittest.main()
