import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.api import scheduled_actions
from app.db.models import AuditLogRecord, ScheduledActionRecord
from app.services.persistence_service import PersistenceService
from app.services.scheduled_action_executor import ScheduledActionExecutor
from app.services.scheduled_action_worker import ScheduledActionWorker


NOW = datetime(2026, 8, 2, 1, 0, tzinfo=timezone.utc)


def build_session():
    session = MagicMock()
    query = MagicMock()
    session.query.return_value = query
    query.filter.return_value = query
    query.with_for_update.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    return session, query


def expression_values(query):
    values = []

    for call in query.filter.call_args_list:
        expression = call.args[0]
        right = getattr(expression, "right", None)
        values.append(getattr(right, "value", None))

    return values


class ScheduledActionPersistenceTest(unittest.TestCase):

    def setUp(self):
        self.service = PersistenceService()

    def test_pending_action_can_be_paused_with_traceability_and_audit(self):
        session, query = build_session()
        query.update.return_value = 1
        query.one.return_value = SimpleNamespace(event_id="event-1")

        with patch("app.services.persistence_service.SessionLocal", return_value=session):
            with patch.object(self.service, "_now", return_value=NOW):
                result = self.service.pause_scheduled_action(15, " operator_pause ")

        self.assertTrue(result["success"])
        self.assertEqual(result["previous_state"], "pending")
        self.assertEqual(result["state"], "paused")
        changes = query.update.call_args.args[0]
        self.assertEqual(changes["state"], "paused")
        self.assertEqual(changes["paused_at"], NOW)
        self.assertEqual(changes["pause_reason"], "operator_pause")
        self.assertIsNone(changes["processing_started_at"])
        self.assertNotIn("scheduled_at", changes)
        self.assertNotIn("attempt_count", changes)
        self.assertIn("pending", expression_values(query))
        audit = session.add.call_args.args[0]
        self.assertEqual(audit.component, "scheduled_actions")
        self.assertEqual(audit.message, "Scheduled action paused")
        session.commit.assert_called_once()

    def test_empty_pause_reason_uses_default(self):
        session, query = build_session()
        query.update.return_value = 1
        query.one.return_value = SimpleNamespace(event_id="event-1")

        with patch("app.services.persistence_service.SessionLocal", return_value=session):
            result = self.service.pause_scheduled_action(15, " ")

        self.assertEqual(
            query.update.call_args.args[0]["pause_reason"],
            "manual_pause",
        )

    def test_non_pending_states_cannot_be_paused(self):
        incompatible_states = [
            "paused",
            "pending_approval",
            "processing",
            "executed",
            "failed",
            "cancelled",
        ]

        for state in incompatible_states:
            with self.subTest(state=state):
                session, query = build_session()
                query.update.return_value = 0
                query.one_or_none.return_value = SimpleNamespace(state=state)

                with patch("app.services.persistence_service.SessionLocal", return_value=session):
                    result = self.service.pause_scheduled_action(15)

                self.assertFalse(result["success"])
                self.assertEqual(result["state"], state)
                self.assertEqual(result["error"], "invalid_state_transition")

    def test_missing_action_cannot_be_paused(self):
        session, query = build_session()
        query.update.return_value = 0
        query.one_or_none.return_value = None

        with patch("app.services.persistence_service.SessionLocal", return_value=session):
            result = self.service.pause_scheduled_action(999)

        self.assertEqual(result["error"], "scheduled_action_not_found")

    def test_two_pause_attempts_only_allow_one_success(self):
        first_session, first_query = build_session()
        first_query.update.return_value = 1
        first_query.one.return_value = SimpleNamespace(event_id="event-1")
        second_session, second_query = build_session()
        second_query.update.return_value = 0
        second_query.one_or_none.return_value = SimpleNamespace(state="paused")

        with patch(
            "app.services.persistence_service.SessionLocal",
            side_effect=[first_session, second_session],
        ):
            first = self.service.pause_scheduled_action(15)
            second = self.service.pause_scheduled_action(15)

        self.assertTrue(first["success"])
        self.assertFalse(second["success"])
        self.assertEqual(second["state"], "paused")

    def test_paused_action_with_open_incident_is_claimed_immediately(self):
        session, query = build_session()
        scheduled_at = NOW + timedelta(hours=1)
        incident = SimpleNamespace(current_status="open")
        record = SimpleNamespace(
            id=15,
            event_id="event-1",
            state="paused",
            scheduled_at=scheduled_at,
            paused_at=NOW - timedelta(minutes=1),
            pause_reason="manual_pause",
            attempt_count=2,
        )
        query.one_or_none.side_effect = [record, incident]
        query.update.return_value = 1

        with patch("app.services.persistence_service.SessionLocal", return_value=session):
            with patch.object(self.service, "_now", return_value=NOW):
                result = self.service.claim_paused_action_for_immediate_execution(15)

        self.assertTrue(result["success"])
        self.assertEqual(result["previous_state"], "paused")
        self.assertEqual(result["state"], "processing")
        changes = query.update.call_args.args[0]
        self.assertEqual(changes["state"], "processing")
        self.assertEqual(changes["resumed_at"], NOW)
        self.assertEqual(changes["processing_started_at"], NOW)
        self.assertNotIn("scheduled_at", changes)
        self.assertNotIn("attempt_count", changes)
        self.assertIn("paused", expression_values(query))
        self.assertGreaterEqual(query.with_for_update.call_count, 2)
        audit = session.add.call_args.args[0]
        self.assertEqual(
            audit.message,
            "Scheduled action resumed for immediate execution",
        )
        self.assertEqual(audit.details["execution_mode"], "immediate")

    def test_resume_is_immediate_for_past_scheduled_at(self):
        session, query = build_session()
        incident = SimpleNamespace(current_status="open")
        record = SimpleNamespace(
            event_id="event-1",
            state="paused",
            scheduled_at=NOW - timedelta(hours=1),
        )
        query.one_or_none.side_effect = [record, incident]
        query.update.return_value = 1

        with patch("app.services.persistence_service.SessionLocal", return_value=session):
            result = self.service.claim_paused_action_for_immediate_execution(15)

        self.assertTrue(result["success"])
        self.assertEqual(query.update.call_args.args[0]["state"], "processing")

    def test_non_paused_action_cannot_be_resumed(self):
        session, query = build_session()
        record = SimpleNamespace(event_id="event-1", state="cancelled")
        query.one_or_none.return_value = record

        with patch("app.services.persistence_service.SessionLocal", return_value=session):
            result = self.service.claim_paused_action_for_immediate_execution(15)

        self.assertEqual(result["state"], "cancelled")
        self.assertEqual(result["error"], "invalid_state_transition")
        query.update.assert_not_called()

    def test_missing_action_cannot_be_resumed(self):
        session, query = build_session()
        query.one_or_none.return_value = None

        with patch("app.services.persistence_service.SessionLocal", return_value=session):
            result = self.service.claim_paused_action_for_immediate_execution(999)

        self.assertEqual(result["error"], "scheduled_action_not_found")

    def test_closed_incident_cancels_paused_action_without_processing(self):
        session, query = build_session()
        incident = SimpleNamespace(current_status="closed")
        record = SimpleNamespace(event_id="event-1", state="paused")
        query.one_or_none.side_effect = [record, incident]
        query.update.return_value = 1

        with patch("app.services.persistence_service.SessionLocal", return_value=session):
            with patch.object(self.service, "_now", return_value=NOW):
                result = self.service.claim_paused_action_for_immediate_execution(15)

        self.assertFalse(result["success"])
        self.assertEqual(result["state"], "cancelled")
        self.assertEqual(result["error"], "incident_not_open")
        changes = query.update.call_args.args[0]
        self.assertEqual(changes["cancel_reason"], "incident_not_open")
        self.assertNotIn("resumed_at", changes)
        audit = session.add.call_args.args[0]
        self.assertEqual(audit.message, "Scheduled action resume rejected")

    def test_recovery_cancellation_includes_paused(self):
        session, query = build_session()
        query.update.return_value = 3

        with patch("app.services.persistence_service.SessionLocal", return_value=session):
            result = self.service.cancel_pending_scheduled_actions("event-1")

        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 3)
        state_values = expression_values(query)
        self.assertIn(["pending", "pending_approval", "paused"], state_values)
        self.assertEqual(
            query.update.call_args.args[0]["cancel_reason"],
            "recovery_received",
        )

    def test_due_query_and_stale_recovery_exclude_paused(self):
        due_session, due_query = build_session()
        due_query.all.return_value = []
        stale_session, stale_query = build_session()
        stale_query.all.return_value = []

        with patch(
            "app.services.persistence_service.SessionLocal",
            side_effect=[due_session, stale_session],
        ):
            self.service.get_due_scheduled_actions(20)
            self.service.recover_stale_scheduled_actions(10, 3)

        self.assertIn("pending", expression_values(due_query))
        self.assertIn("processing", expression_values(stale_query))
        self.assertNotIn("paused", expression_values(due_query))
        self.assertNotIn("paused", expression_values(stale_query))

    def test_serializer_includes_pause_and_execution_fields(self):
        record = ScheduledActionRecord(
            id=15,
            event_id="event-1",
            state="paused",
            scheduled_at=NOW + timedelta(minutes=5),
            paused_at=NOW,
            resumed_at=None,
            pause_reason="manual_test",
            processing_started_at=None,
            attempt_count=0,
            cancel_reason=None,
            last_error=None,
        )
        record.created_at = NOW

        result = self.service._scheduled_action_to_dict(record)

        for field in (
            "paused_at",
            "resumed_at",
            "pause_reason",
            "processing_started_at",
            "attempt_count",
            "cancel_reason",
            "last_error",
            "scheduled_at",
            "state",
        ):
            self.assertIn(field, result)

    def test_pending_approval_is_claimed_atomically_with_audit(self):
        session, query = build_session()
        record = SimpleNamespace(
            id=15,
            event_id="event-1",
            state="pending_approval",
        )
        incident = SimpleNamespace(current_status="open")
        query.one_or_none.side_effect = [record, incident]
        query.update.return_value = 1

        with patch(
            "app.services.persistence_service.SessionLocal",
            return_value=session,
        ):
            with patch.object(self.service, "_now", return_value=NOW):
                result = self.service.claim_pending_approval_action(
                    15,
                    source="dashboard_api",
                    note=" Approved from dashboard ",
                )

        self.assertTrue(result["success"])
        self.assertEqual(result["previous_state"], "pending_approval")
        self.assertEqual(result["state"], "processing")
        changes = query.update.call_args.args[0]
        self.assertEqual(changes["state"], "processing")
        self.assertEqual(changes["processing_started_at"], NOW)
        self.assertEqual(changes["approval_decision"], "approved")
        self.assertEqual(changes["approval_decided_at"], NOW)
        self.assertIn("pending_approval", expression_values(query))
        audit = session.add.call_args.args[0]
        self.assertIsInstance(audit, AuditLogRecord)
        self.assertEqual(audit.component, "scheduled_actions")
        self.assertEqual(audit.message, "Scheduled action approved")
        self.assertEqual(audit.details["source"], "dashboard_api")
        self.assertEqual(audit.details["note"], "Approved from dashboard")
        session.commit.assert_called_once()

    def test_incompatible_states_cannot_be_approved(self):
        incompatible_states = [
            "pending",
            "paused",
            "processing",
            "executed",
            "failed",
            "cancelled",
        ]

        for state in incompatible_states:
            with self.subTest(state=state):
                session, query = build_session()
                query.one_or_none.return_value = SimpleNamespace(
                    id=15,
                    event_id="event-1",
                    state=state,
                )

                with patch(
                    "app.services.persistence_service.SessionLocal",
                    return_value=session,
                ):
                    result = self.service.claim_pending_approval_action(15)

                self.assertFalse(result["success"])
                self.assertEqual(result["state"], state)
                self.assertEqual(
                    result["error"],
                    "invalid_state_transition",
                )
                query.update.assert_not_called()
                session.add.assert_not_called()

    def test_missing_pending_approval_returns_not_found(self):
        session, query = build_session()
        query.one_or_none.return_value = None

        with patch(
            "app.services.persistence_service.SessionLocal",
            return_value=session,
        ):
            result = self.service.claim_pending_approval_action(999)

        self.assertEqual(result["error"], "scheduled_action_not_found")
        self.assertIsNone(result["state"])
        query.update.assert_not_called()

    def test_closed_incident_cancels_approval_and_audits_rejection(self):
        session, query = build_session()
        record = SimpleNamespace(
            id=15,
            event_id="event-1",
            state="pending_approval",
        )
        incident = SimpleNamespace(current_status="closed")
        query.one_or_none.side_effect = [record, incident]
        query.update.return_value = 1

        with patch(
            "app.services.persistence_service.SessionLocal",
            return_value=session,
        ):
            with patch.object(self.service, "_now", return_value=NOW):
                result = self.service.claim_pending_approval_action(
                    15,
                    source="dashboard_api",
                    note="closed check",
                )

        self.assertFalse(result["success"])
        self.assertEqual(result["state"], "cancelled")
        self.assertEqual(result["error"], "incident_not_open")
        changes = query.update.call_args.args[0]
        self.assertEqual(changes["state"], "cancelled")
        self.assertEqual(changes["cancel_reason"], "incident_not_open")
        self.assertEqual(changes["approval_decision"], "rejected")
        self.assertEqual(changes["approval_decided_at"], NOW)
        audit = session.add.call_args.args[0]
        self.assertEqual(
            audit.message,
            "Scheduled action approval rejected",
        )
        self.assertEqual(audit.details["reason"], "incident_not_open")
        self.assertEqual(audit.details["source"], "dashboard_api")

    def test_two_approval_claims_only_allow_one_transition(self):
        first_session, first_query = build_session()
        first_query.one_or_none.side_effect = [
            SimpleNamespace(
                id=15,
                event_id="event-1",
                state="pending_approval",
            ),
            SimpleNamespace(current_status="open"),
        ]
        first_query.update.return_value = 1
        second_session, second_query = build_session()
        second_query.one_or_none.return_value = SimpleNamespace(
            id=15,
            event_id="event-1",
            state="processing",
        )

        with patch(
            "app.services.persistence_service.SessionLocal",
            side_effect=[first_session, second_session],
        ):
            first = self.service.claim_pending_approval_action(15)
            second = self.service.claim_pending_approval_action(15)

        self.assertTrue(first["success"])
        self.assertFalse(second["success"])
        self.assertEqual(second["error"], "invalid_state_transition")
        first_query.update.assert_called_once()
        second_query.update.assert_not_called()

    def test_pending_approval_can_be_rejected_atomically_with_audit(self):
        session, query = build_session()
        record = SimpleNamespace(
            id=15,
            event_id="event-1",
            state="pending_approval",
            cancelled_at=None,
            cancel_reason=None,
            processing_started_at=NOW,
        )
        query.one_or_none.return_value = record

        with patch(
            "app.services.persistence_service.SessionLocal",
            return_value=session,
        ), patch.object(self.service, "_now", return_value=NOW):
            result = self.service.reject_pending_approval_action(
                15,
                source='dashboard_api {"token":"source-secret"}',
                note='Operator rejected {"password":"hunter2"}',
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["previous_state"], "pending_approval")
        self.assertEqual(result["state"], "cancelled")
        self.assertEqual(record.state, "cancelled")
        self.assertEqual(record.cancelled_at, NOW)
        self.assertEqual(record.cancel_reason, "operator_rejected")
        self.assertIsNone(record.processing_started_at)
        self.assertEqual(record.approval_decision, "rejected")
        self.assertEqual(record.approval_decided_at, NOW)
        query.with_for_update.assert_called_once_with()
        session.begin.assert_called_once_with()
        audit = session.add.call_args.args[0]
        self.assertIsInstance(audit, AuditLogRecord)
        self.assertEqual(audit.message, "approval_rejected")
        self.assertEqual(audit.details["scheduled_action_id"], 15)
        self.assertEqual(audit.details["previous_state"], "pending_approval")
        self.assertEqual(audit.details["new_state"], "cancelled")
        self.assertNotIn("secret", json.dumps(audit.details))
        self.assertNotIn("hunter2", json.dumps(audit.details))

    def test_rejection_conflicts_for_wrong_and_repeated_states(self):
        for state in ("pending", "processing", "cancelled", "executed"):
            with self.subTest(state=state):
                session, query = build_session()
                query.one_or_none.return_value = SimpleNamespace(
                    id=15,
                    event_id="event-1",
                    state=state,
                )

                with patch(
                    "app.services.persistence_service.SessionLocal",
                    return_value=session,
                ):
                    result = self.service.reject_pending_approval_action(15)

                self.assertEqual(result["error"], "invalid_state_transition")
                self.assertEqual(result["state"], state)
                session.add.assert_not_called()

    def test_rejection_returns_not_found(self):
        session, query = build_session()
        query.one_or_none.return_value = None

        with patch(
            "app.services.persistence_service.SessionLocal",
            return_value=session,
        ):
            result = self.service.reject_pending_approval_action(999)

        self.assertEqual(result["error"], "scheduled_action_not_found")
        self.assertIsNone(result["state"])
        session.add.assert_not_called()


class ScheduledActionExecutorTest(unittest.TestCase):

    def test_successful_execution_finishes_as_executed(self):
        executor = ScheduledActionExecutor(dispatcher=object())
        action = {"id": 15, "event_id": "event-1", "state": "processing"}

        with patch(
            "app.services.scheduled_action_executor.persistence_service"
        ) as persistence:
            persistence.get_scheduled_action.return_value = action
            persistence.mark_scheduled_action_executed.return_value = True
            with patch.object(
                executor,
                "execute_action",
                return_value={"success": True, "results": []},
            ) as execute_action:
                result = executor.execute(15)

        self.assertTrue(result["success"])
        execute_action.assert_called_once_with(action)
        persistence.mark_scheduled_action_executed.assert_called_once_with(15)

    def test_failed_execution_finishes_as_failed(self):
        executor = ScheduledActionExecutor(dispatcher=object())
        action = {"id": 15, "event_id": "event-1", "state": "processing"}

        with patch(
            "app.services.scheduled_action_executor.persistence_service"
        ) as persistence:
            persistence.get_scheduled_action.return_value = action
            persistence.mark_scheduled_action_failed.return_value = True
            with patch.object(
                executor,
                "execute_action",
                return_value={
                    "success": False,
                    "results": [{"action": "telegram", "success": False}],
                },
            ):
                result = executor.execute(15)

        self.assertFalse(result["success"])
        persistence.mark_scheduled_action_failed.assert_called_once()
        persistence.mark_scheduled_action_executed.assert_not_called()

    def test_executor_rejects_action_not_in_processing(self):
        executor = ScheduledActionExecutor(dispatcher=object())

        with patch(
            "app.services.scheduled_action_executor.persistence_service"
        ) as persistence:
            persistence.get_scheduled_action.return_value = {
                "id": 15,
                "state": "paused",
            }
            result = executor.execute(15)

        self.assertEqual(result["error"], "scheduled_action_not_processing")
        persistence.mark_scheduled_action_executed.assert_not_called()


class ScheduledActionWorkerPauseTest(unittest.TestCase):

    def test_worker_uses_shared_executor_after_claim(self):
        executor = MagicMock()
        executor.dispatcher = object()
        worker = ScheduledActionWorker(executor=executor)
        action = {"id": 15, "event_id": "event-1"}

        with patch(
            "app.services.scheduled_action_worker.persistence_service"
        ) as persistence:
            persistence.claim_scheduled_action.return_value = True
            persistence.get_incident_status.return_value = "open"
            worker.process_scheduled_action(action)

        executor.execute.assert_called_once_with(15)

    def test_worker_does_not_execute_when_due_query_returns_no_paused_action(self):
        executor = MagicMock()
        executor.dispatcher = object()
        worker = ScheduledActionWorker(executor=executor)

        with patch(
            "app.services.scheduled_action_worker.persistence_service"
        ) as persistence:
            persistence.recover_stale_scheduled_actions.return_value = {
                "success": True,
                "recovered": 0,
                "failed": 0,
            }
            persistence.get_due_scheduled_actions.return_value = []
            worker.run_once()

        executor.execute.assert_not_called()
        persistence.claim_scheduled_action.assert_not_called()


class ScheduledActionApprovalWorkerTest(unittest.TestCase):

    def test_deferred_approval_reuses_claim_without_executing_inline(self):
        executor = MagicMock()
        executor.dispatcher = object()
        worker = ScheduledActionWorker(executor=executor)
        approval = {
            "success": True,
            "scheduled_action_id": 15,
            "previous_state": "pending_approval",
            "state": "processing",
            "error": None,
        }

        with patch(
            "app.services.scheduled_action_worker.persistence_service"
        ) as persistence:
            persistence.claim_pending_approval_action.return_value = approval
            result = worker.approve_scheduled_action(
                15,
                source="dashboard_api",
                note="MVP approval",
                defer_execution=True,
            )

        self.assertTrue(result["approved"])
        self.assertEqual(result["state"], "processing")
        persistence.claim_pending_approval_action.assert_called_once_with(
            15,
            source="dashboard_api",
            note="MVP approval",
        )
        executor.execute.assert_not_called()

    def test_cli_approval_preserves_immediate_execution_and_real_state(self):
        executor = MagicMock()
        executor.dispatcher = object()
        executor.execute.return_value = {"success": True, "results": []}
        worker = ScheduledActionWorker(executor=executor)

        with patch(
            "app.services.scheduled_action_worker.persistence_service"
        ) as persistence:
            persistence.claim_pending_approval_action.return_value = {
                "success": True,
                "scheduled_action_id": 15,
                "previous_state": "pending_approval",
                "state": "processing",
                "error": None,
            }
            persistence.get_scheduled_action.return_value = {
                "id": 15,
                "state": "executed",
            }
            result = worker.approve_scheduled_action(15)

        executor.execute.assert_called_once_with(15)
        self.assertTrue(result["success"])
        self.assertEqual(result["state"], "executed")

    def test_rejected_approval_never_executes(self):
        executor = MagicMock()
        executor.dispatcher = object()
        worker = ScheduledActionWorker(executor=executor)

        with patch(
            "app.services.scheduled_action_worker.persistence_service"
        ) as persistence:
            persistence.claim_pending_approval_action.return_value = {
                "success": False,
                "scheduled_action_id": 15,
                "state": "cancelled",
                "error": "incident_not_open",
            }
            result = worker.approve_scheduled_action(15)

        self.assertEqual(result["error"], "incident_not_open")
        executor.execute.assert_not_called()


class FakeBackgroundTasks:

    def __init__(self):
        self.calls = []

    def add_task(self, function, *args, **kwargs):
        self.calls.append((function, args, kwargs))


class ScheduledActionApiTest(unittest.TestCase):

    def test_pause_endpoint_returns_200(self):
        result = {
            "success": True,
            "scheduled_action_id": 15,
            "state": "paused",
            "error": None,
        }

        with patch.object(
            scheduled_actions.persistence_service,
            "pause_scheduled_action",
            return_value=result,
        ) as pause:
            response = scheduled_actions.pause_scheduled_action(
                15,
                scheduled_actions.PauseScheduledActionRequest(
                    reason="manual_test"
                ),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.body)["state"], "paused")
        pause.assert_called_once_with(15, reason="manual_test")

    def test_pause_endpoint_maps_not_found_conflict_and_internal_error(self):
        cases = [
            ("scheduled_action_not_found", 404),
            ("invalid_state_transition", 409),
            ("database exploded", 500),
        ]

        for error, expected_status in cases:
            with self.subTest(error=error):
                result = {
                    "success": False,
                    "scheduled_action_id": 15,
                    "state": None,
                    "error": error,
                }
                with patch.object(
                    scheduled_actions.persistence_service,
                    "pause_scheduled_action",
                    return_value=result,
                ):
                    response = scheduled_actions.pause_scheduled_action(15)

                body = json.loads(response.body)
                self.assertEqual(response.status_code, expected_status)
                if expected_status == 500:
                    self.assertEqual(body["error"], "internal_error")
                    self.assertNotIn("exploded", response.body.decode())

    def test_resume_endpoint_returns_202_and_schedules_once(self):
        result = {
            "success": True,
            "scheduled_action_id": 15,
            "state": "processing",
            "error": None,
        }
        background_tasks = FakeBackgroundTasks()

        with patch.object(
            scheduled_actions.persistence_service,
            "claim_paused_action_for_immediate_execution",
            return_value=result,
        ):
            response = scheduled_actions.resume_scheduled_action(
                15,
                background_tasks,
            )

        body = json.loads(response.body)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(body["state"], "processing")
        self.assertTrue(body["execution_started"])
        self.assertEqual(len(background_tasks.calls), 1)
        queued_function = background_tasks.calls[0][0]
        self.assertIs(
            queued_function.__self__,
            scheduled_actions.scheduled_action_executor,
        )
        self.assertIs(
            queued_function.__func__,
            scheduled_actions.scheduled_action_executor.execute.__func__,
        )
        self.assertEqual(background_tasks.calls[0][1], (15,))

    def test_second_resume_request_conflicts_without_second_execution(self):
        first = {
            "success": True,
            "scheduled_action_id": 15,
            "state": "processing",
            "error": None,
        }
        second = {
            "success": False,
            "scheduled_action_id": 15,
            "state": "processing",
            "error": "invalid_state_transition",
        }
        background_tasks = FakeBackgroundTasks()

        with patch.object(
            scheduled_actions.persistence_service,
            "claim_paused_action_for_immediate_execution",
            side_effect=[first, second],
        ):
            first_response = scheduled_actions.resume_scheduled_action(
                15,
                background_tasks,
            )
            second_response = scheduled_actions.resume_scheduled_action(
                15,
                background_tasks,
            )

        self.assertEqual(first_response.status_code, 202)
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(len(background_tasks.calls), 1)

    def test_closed_incident_resume_returns_409_without_execution(self):
        result = {
            "success": False,
            "scheduled_action_id": 15,
            "state": "cancelled",
            "error": "incident_not_open",
        }
        background_tasks = FakeBackgroundTasks()

        with patch.object(
            scheduled_actions.persistence_service,
            "claim_paused_action_for_immediate_execution",
            return_value=result,
        ):
            response = scheduled_actions.resume_scheduled_action(
                15,
                background_tasks,
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(json.loads(response.body)["state"], "cancelled")
        self.assertEqual(background_tasks.calls, [])

    def test_approve_endpoint_accepts_optional_body_and_queues_once(self):
        result = {
            "success": True,
            "scheduled_action_id": 15,
            "previous_state": "pending_approval",
            "state": "processing",
            "approved": True,
            "execution_started": True,
            "error": None,
        }

        for payload, expected_note in (
            (None, None),
            (
                scheduled_actions.ApproveScheduledActionRequest(
                    note="Approved from dashboard"
                ),
                "Approved from dashboard",
            ),
        ):
            with self.subTest(note=expected_note):
                background_tasks = FakeBackgroundTasks()

                with patch.object(
                    scheduled_actions.scheduled_action_approval_worker,
                    "approve_scheduled_action",
                    return_value=result,
                ) as approve:
                    response = scheduled_actions.approve_scheduled_action(
                        15,
                        background_tasks,
                        payload,
                    )

                body = json.loads(response.body)
                self.assertEqual(response.status_code, 202)
                self.assertEqual(body["previous_state"], "pending_approval")
                self.assertEqual(body["state"], "processing")
                self.assertTrue(body["approved"])
                self.assertTrue(body["execution_started"])
                approve.assert_called_once_with(
                    15,
                    source="dashboard_api",
                    note=expected_note,
                    defer_execution=True,
                )
                self.assertEqual(len(background_tasks.calls), 1)
                self.assertEqual(background_tasks.calls[0][1], (15,))

    def test_approve_endpoint_maps_not_found_and_conflicts(self):
        cases = [
            (
                {
                    "success": False,
                    "scheduled_action_id": 999,
                    "state": None,
                    "error": "scheduled_action_not_found",
                },
                404,
            ),
            (
                {
                    "success": False,
                    "scheduled_action_id": 15,
                    "state": "paused",
                    "error": "invalid_state_transition",
                },
                409,
            ),
            (
                {
                    "success": False,
                    "scheduled_action_id": 15,
                    "state": "cancelled",
                    "error": "incident_not_open",
                },
                409,
            ),
        ]

        for result, expected_status in cases:
            with self.subTest(error=result["error"]):
                background_tasks = FakeBackgroundTasks()

                with patch.object(
                    scheduled_actions.scheduled_action_approval_worker,
                    "approve_scheduled_action",
                    return_value=result,
                ):
                    response = scheduled_actions.approve_scheduled_action(
                        result["scheduled_action_id"],
                        background_tasks,
                    )

                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(background_tasks.calls, [])

    def test_second_approval_conflicts_without_second_execution(self):
        first = {
            "success": True,
            "scheduled_action_id": 15,
            "previous_state": "pending_approval",
            "state": "processing",
            "approved": True,
            "execution_started": True,
            "error": None,
        }
        second = {
            "success": False,
            "scheduled_action_id": 15,
            "previous_state": "processing",
            "state": "processing",
            "error": "invalid_state_transition",
        }
        background_tasks = FakeBackgroundTasks()

        with patch.object(
            scheduled_actions.scheduled_action_approval_worker,
            "approve_scheduled_action",
            side_effect=[first, second],
        ) as approve:
            first_response = scheduled_actions.approve_scheduled_action(
                15,
                background_tasks,
            )
            second_response = scheduled_actions.approve_scheduled_action(
                15,
                background_tasks,
            )

        self.assertEqual(first_response.status_code, 202)
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(approve.call_count, 2)
        self.assertEqual(len(background_tasks.calls), 1)

    def test_approve_endpoint_hides_unexpected_error_details(self):
        background_tasks = FakeBackgroundTasks()

        with patch.object(
            scheduled_actions.scheduled_action_approval_worker,
            "approve_scheduled_action",
            side_effect=RuntimeError("token=secret database exploded"),
        ) as approve:
            response = scheduled_actions.approve_scheduled_action(
                15,
                background_tasks,
            )

        body = json.loads(response.body)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["error"], "internal_error")
        self.assertNotIn("secret", response.body.decode())
        approve.assert_called_once()
        self.assertEqual(background_tasks.calls, [])

    def test_approve_endpoint_is_documented_in_openapi(self):
        from app.main import app

        operation = app.openapi()["paths"][
            "/api/scheduled-actions/{scheduled_action_id}/approve"
        ]["post"]

        self.assertEqual(
            operation["responses"]["202"]["content"][
                "application/json"
            ]["schema"]["$ref"],
            "#/components/schemas/ApproveScheduledActionResponse",
        )
        self.assertIn("404", operation["responses"])
        self.assertIn("409", operation["responses"])
        self.assertIn("500", operation["responses"])
        self.assertIn("requestBody", operation)

    def test_reject_endpoint_succeeds_without_executor(self):
        result = {
            "success": True,
            "scheduled_action_id": 15,
            "previous_state": "pending_approval",
            "state": "cancelled",
            "error": None,
        }

        with patch.object(
            scheduled_actions.persistence_service,
            "reject_pending_approval_action",
            return_value=result,
        ) as reject, patch.object(
            scheduled_actions.scheduled_action_executor,
            "execute",
        ) as execute:
            response = scheduled_actions.reject_scheduled_action(
                15,
                scheduled_actions.RejectScheduledActionRequest(
                    note="Not authorized"
                ),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.body), {
            "success": True,
            "scheduled_action_id": 15,
            "previous_state": "pending_approval",
            "state": "cancelled",
            "rejected": True,
        })
        reject.assert_called_once_with(
            15,
            source="dashboard_api",
            note="Not authorized",
        )
        execute.assert_not_called()

    def test_reject_endpoint_maps_not_found_conflict_and_internal_error(self):
        cases = [
            ("scheduled_action_not_found", None, 404),
            ("invalid_state_transition", "cancelled", 409),
            ("database exploded token=secret", None, 500),
        ]

        for error, state, expected_status in cases:
            with self.subTest(error=error), patch.object(
                scheduled_actions.persistence_service,
                "reject_pending_approval_action",
                return_value={
                    "success": False,
                    "scheduled_action_id": 15,
                    "state": state,
                    "error": error,
                },
            ), patch.object(
                scheduled_actions.scheduled_action_executor,
                "execute",
            ) as execute:
                response = scheduled_actions.reject_scheduled_action(15)

            body = json.loads(response.body)
            self.assertEqual(response.status_code, expected_status)
            self.assertEqual(
                body["error"],
                error if expected_status != 500 else "internal_error",
            )
            self.assertNotIn("secret", response.body.decode())
            execute.assert_not_called()

        with patch.object(
            scheduled_actions.persistence_service,
            "reject_pending_approval_action",
            side_effect=RuntimeError("password=secret"),
        ), patch.object(
            scheduled_actions.scheduled_action_executor,
            "execute",
        ) as execute:
            response = scheduled_actions.reject_scheduled_action(15)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(response.body)["error"], "internal_error")
        self.assertNotIn("secret", response.body.decode())
        execute.assert_not_called()

    def test_reject_endpoint_is_documented_and_validates_note(self):
        from fastapi.testclient import TestClient

        from app.main import app

        operation = app.openapi()["paths"][
            "/api/scheduled-actions/{scheduled_action_id}/reject"
        ]["post"]

        self.assertEqual(
            operation["responses"]["200"]["content"][
                "application/json"
            ]["schema"]["$ref"],
            "#/components/schemas/RejectScheduledActionResponse",
        )
        self.assertIn("404", operation["responses"])
        self.assertIn("409", operation["responses"])
        self.assertIn("500", operation["responses"])
        note_schema = app.openapi()["components"]["schemas"][
            "RejectScheduledActionRequest"
        ]["properties"]["note"]
        self.assertIn("maxLength", json.dumps(note_schema))

        with patch.object(
            scheduled_actions.persistence_service,
            "reject_pending_approval_action",
        ) as reject:
            response = TestClient(app).post(
                "/api/scheduled-actions/15/reject",
                json={"note": "x" * 501},
            )

        self.assertEqual(response.status_code, 422)
        reject.assert_not_called()

    def test_routes_are_registered(self):
        from app.main import app

        routes = {
            (route.path, method)
            for route in app.routes
            for method in getattr(route, "methods", set())
        }

        self.assertIn(("/api/scheduled-actions/{scheduled_action_id}/pause", "POST"), routes)
        self.assertIn(("/api/scheduled-actions/{scheduled_action_id}/resume", "POST"), routes)
        self.assertIn(("/api/scheduled-actions/{scheduled_action_id}/approve", "POST"), routes)
        self.assertIn(("/api/scheduled-actions/{scheduled_action_id}/reject", "POST"), routes)
        self.assertIn(("/api/approvals", "GET"), routes)
        self.assertIn(("/api/operations", "GET"), routes)


if __name__ == "__main__":
    unittest.main()
