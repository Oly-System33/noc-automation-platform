import json
import unittest
from datetime import datetime, timedelta, timezone

from pydantic import ValidationError

from app.schemas.dashboard import (
    DashboardIncidentItem,
    DashboardIncidentListResponse,
    DashboardStatus,
    DashboardStatusCounts,
    DashboardSummaryResponse,
    resolve_dashboard_status,
)


NOW = datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc)


class DashboardStatusResolverTest(unittest.TestCase):

    def test_enum_contains_exact_visible_status_contract(self):
        self.assertEqual(
            [status.value for status in DashboardStatus],
            [
                "active",
                "scheduled",
                "paused",
                "pending_approval",
                "executing",
                "waiting_confirmation",
                "retry_scheduled",
                "manual_required",
                "stuck",
                "failed",
                "cancelled",
                "closed",
            ],
        )

    def test_open_incident_without_operations_is_active(self):
        status = resolve_dashboard_status(
            incident_status="open",
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.ACTIVE)

    def test_pending_action_is_scheduled(self):
        status = resolve_dashboard_status(
            scheduled_action_state="pending",
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.SCHEDULED)

    def test_future_pending_action_is_scheduled_not_paused(self):
        status = resolve_dashboard_status(
            scheduled_action_state="pending",
            scheduled_action_scheduled_at=NOW + timedelta(hours=1),
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.SCHEDULED)
        self.assertNotEqual(status, DashboardStatus.PAUSED)

    def test_paused_action_is_paused(self):
        status = resolve_dashboard_status(
            scheduled_action_state="paused",
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.PAUSED)

    def test_pending_approval_action_is_pending_approval(self):
        status = resolve_dashboard_status(
            scheduled_action_state="pending_approval",
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.PENDING_APPROVAL)

    def test_processing_action_inside_timeout_is_executing(self):
        status = resolve_dashboard_status(
            scheduled_action_state="processing",
            scheduled_action_processing_started_at=NOW - timedelta(minutes=9),
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.EXECUTING)

    def test_processing_action_outside_timeout_is_stuck(self):
        status = resolve_dashboard_status(
            scheduled_action_state="processing",
            scheduled_action_processing_started_at=NOW - timedelta(minutes=11),
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.STUCK)

    def test_processing_event_inside_timeout_is_executing(self):
        status = resolve_dashboard_status(
            processed_event_state="processing",
            processed_event_started_at=NOW - timedelta(minutes=9),
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.EXECUTING)

    def test_processing_event_outside_timeout_is_stuck(self):
        status = resolve_dashboard_status(
            processed_event_state="processing",
            processed_event_started_at=NOW - timedelta(minutes=11),
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.STUCK)

    def test_calling_flow_is_executing(self):
        status = resolve_dashboard_status(
            call_flow_state="calling",
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.EXECUTING)

    def test_waiting_confirmation_flow_is_waiting_confirmation(self):
        status = resolve_dashboard_status(
            call_flow_state="waiting_confirmation",
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.WAITING_CONFIRMATION)

    def test_retry_scheduled_flow_is_retry_scheduled(self):
        status = resolve_dashboard_status(
            call_flow_state="retry_scheduled",
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.RETRY_SCHEDULED)

    def test_manual_required_flow_is_manual_required(self):
        status = resolve_dashboard_status(
            call_flow_state="manual_required",
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.MANUAL_REQUIRED)

    def test_failed_internal_state_is_failed(self):
        for field in ("processed_event_state", "scheduled_action_state"):
            with self.subTest(field=field):
                status = resolve_dashboard_status(
                    **{field: "failed"},
                    now=NOW,
                )

                self.assertEqual(status, DashboardStatus.FAILED)

    def test_cancelled_internal_state_is_cancelled(self):
        for field in ("scheduled_action_state", "call_flow_state"):
            with self.subTest(field=field):
                status = resolve_dashboard_status(
                    **{field: "cancelled"},
                    now=NOW,
                )

                self.assertEqual(status, DashboardStatus.CANCELLED)

    def test_closed_incident_is_closed(self):
        status = resolve_dashboard_status(
            incident_status="closed",
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.CLOSED)

    def test_closed_has_priority_over_stuck(self):
        status = resolve_dashboard_status(
            incident_status="closed",
            scheduled_action_state="processing",
            scheduled_action_processing_started_at=NOW - timedelta(hours=1),
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.CLOSED)

    def test_stuck_has_priority_over_failed(self):
        status = resolve_dashboard_status(
            processed_event_state="processing",
            processed_event_started_at=NOW - timedelta(hours=1),
            scheduled_action_state="failed",
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.STUCK)

    def test_aggregated_stuck_has_priority_over_failed(self):
        status = resolve_dashboard_status(
            scheduled_action_states=["processing", "failed"],
            scheduled_action_processing_started_at=NOW - timedelta(hours=1),
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.STUCK)

    def test_failed_has_priority_over_paused(self):
        status = resolve_dashboard_status(
            processed_event_state="failed",
            scheduled_action_state="paused",
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.FAILED)

    def test_pending_approval_has_priority_over_paused(self):
        status = resolve_dashboard_status(
            scheduled_action_states=["paused", "pending_approval"],
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.PENDING_APPROVAL)

    def test_executing_has_priority_over_paused(self):
        status = resolve_dashboard_status(
            processed_event_state="processing",
            processed_event_started_at=NOW - timedelta(minutes=1),
            scheduled_action_state="paused",
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.EXECUTING)

    def test_paused_has_priority_over_scheduled(self):
        status = resolve_dashboard_status(
            scheduled_action_states=["pending", "paused"],
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.PAUSED)

    def test_scheduled_has_priority_over_cancelled(self):
        status = resolve_dashboard_status(
            scheduled_action_states=["cancelled", "pending"],
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.SCHEDULED)

    def test_unknown_internal_state_is_ignored(self):
        status = resolve_dashboard_status(
            incident_status="unknown",
            processed_event_state="unexpected",
            scheduled_action_state="mystery",
            call_flow_state="other",
            now=NOW,
        )
        failed_status = resolve_dashboard_status(
            scheduled_action_state="failed",
            call_flow_state="unknown",
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.ACTIVE)
        self.assertEqual(failed_status, DashboardStatus.FAILED)

    def test_timezone_aware_values_are_compared_in_utc(self):
        argentina = timezone(timedelta(hours=-3))
        started_at = datetime(2026, 8, 1, 20, 55, tzinfo=argentina)

        status = resolve_dashboard_status(
            scheduled_action_state="processing",
            scheduled_action_processing_started_at=started_at,
            now=NOW,
        )

        self.assertEqual(status, DashboardStatus.EXECUTING)

    def test_timeout_at_exact_boundary_is_stuck(self):
        status = resolve_dashboard_status(
            scheduled_action_state="processing",
            scheduled_action_processing_started_at=NOW - timedelta(minutes=10),
            now=NOW,
            processing_timeout_minutes=10,
        )

        self.assertEqual(status, DashboardStatus.STUCK)


class DashboardModelsTest(unittest.TestCase):

    def test_incident_item_accepts_valid_data(self):
        item = DashboardIncidentItem(
            event_id="event-1",
            client="Banco X",
            display_status=DashboardStatus.ACTIVE,
            attempt_count=0,
        )

        self.assertEqual(item.event_id, "event-1")
        self.assertEqual(item.display_status, DashboardStatus.ACTIVE)

    def test_incident_item_serializes_enum_as_string(self):
        item = DashboardIncidentItem(
            event_id="event-1",
            display_status=DashboardStatus.PAUSED,
        )

        payload = json.loads(item.model_dump_json())

        self.assertEqual(payload["display_status"], "paused")

    def test_status_counts_default_to_zero(self):
        counts = DashboardStatusCounts()

        self.assertEqual(
            counts.model_dump(),
            {status.value: 0 for status in DashboardStatus},
        )

    def test_summary_response_accepts_valid_data(self):
        response = DashboardSummaryResponse(
            generated_at=NOW,
            counts=DashboardStatusCounts(active=2, paused=1),
            by_client={"Banco X": 3},
            total=3,
        )

        self.assertEqual(response.total, 3)
        self.assertEqual(response.counts.paused, 1)

    def test_incident_list_response_accepts_valid_list(self):
        item = DashboardIncidentItem(
            event_id="event-1",
            display_status=DashboardStatus.SCHEDULED,
        )
        response = DashboardIncidentListResponse(
            items=[item],
            total=1,
            generated_at=NOW,
        )

        self.assertEqual(response.total, 1)
        self.assertEqual(response.items, [item])

    def test_dates_serialize_as_iso_8601(self):
        item = DashboardIncidentItem(
            event_id="event-1",
            display_status=DashboardStatus.EXECUTING,
            opened_at=NOW,
            updated_at=NOW,
        )

        payload = json.loads(item.model_dump_json())

        self.assertEqual(payload["opened_at"], "2026-08-02T00:00:00Z")
        self.assertEqual(payload["updated_at"], "2026-08-02T00:00:00Z")

    def test_missing_event_id_is_rejected(self):
        with self.assertRaises(ValidationError):
            DashboardIncidentItem(display_status=DashboardStatus.ACTIVE)

    def test_invalid_display_status_is_rejected(self):
        with self.assertRaises(ValidationError):
            DashboardIncidentItem(
                event_id="event-1",
                display_status="unknown",
            )


if __name__ == "__main__":
    unittest.main()
