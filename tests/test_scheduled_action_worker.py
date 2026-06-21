import unittest

from app.models.event_model import ZabbixEvent
from app.services.persistence_service import PersistenceService
from app.services.action_dispatcher import ActionDispatcher
from app.services.scheduled_action_worker import ScheduledActionWorker


class ActionDispatcherResultTest(unittest.TestCase):

    def test_dispatch_returns_success_summary(self):
        dispatcher = ActionDispatcher()
        dispatcher.ACTION_MAP = {
            "ok": lambda event, contact: True,
        }
        event = ZabbixEvent(
            host="client/host",
            trigger="trigger",
            severity="High",
            status="1",
            event_id="dispatch-ok",
        )

        result = dispatcher.dispatch(event, ["ok"], ["target"])

        self.assertTrue(result["success"])
        self.assertEqual(result["results"][0]["action"], "ok")

    def test_dispatch_returns_failure_summary(self):
        dispatcher = ActionDispatcher()
        dispatcher.ACTION_MAP = {
            "fail": lambda event, contact: False,
        }
        event = ZabbixEvent(
            host="client/host",
            trigger="trigger",
            severity="High",
            status="1",
            event_id="dispatch-fail",
        )

        result = dispatcher.dispatch(event, ["fail"], ["target"])

        self.assertFalse(result["success"])
        self.assertFalse(result["results"][0]["success"])


class ScheduledActionWorkerTest(unittest.TestCase):

    def test_build_event_from_scheduled_action(self):
        worker = ScheduledActionWorker(dispatcher=object())
        scheduled_action = {
            "event_id": "event-1",
            "client": "Banco X",
            "host": "test-noc",
            "trigger": "Zabbix agent unavailable",
            "severity": "High",
            "trigger_group": "availability",
            "created_at": "2026-06-20T10:00:00",
        }

        event = worker._build_event(scheduled_action)

        self.assertEqual(event.event_id, "event-1")
        self.assertEqual(event.host, "Banco X/test-noc")
        self.assertEqual(event.client, "Banco X")
        self.assertEqual(event.parsed_host, "test-noc")
        self.assertEqual(event.trigger_group, "availability")


class PersistenceIdempotencyHelpersTest(unittest.TestCase):

    def setUp(self):
        self.service = PersistenceService()

    def test_normalize_zabbix_status(self):
        cases = [
            ("1", "PROBLEM"),
            (1, "PROBLEM"),
            ("PROBLEM", "PROBLEM"),
            ("0", "RECOVERY"),
            (0, "RECOVERY"),
            ("RECOVERY", "RECOVERY"),
        ]

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    self.service.normalize_zabbix_status(value),
                    expected,
                )

    def test_scheduled_action_dedupe_key_is_stable(self):
        first = self.service.build_scheduled_action_dedupe_key(
            event_id="event-1",
            trigger_group="availability",
            target="noc",
            actions=["jira", "calls"],
        )
        second = self.service.build_scheduled_action_dedupe_key(
            event_id="event-1",
            trigger_group="availability",
            target="noc",
            actions=["CALLS", "Jira"],
        )

        self.assertEqual(first, second)
        self.assertEqual(first, "event-1|availability|noc|calls,jira")


if __name__ == "__main__":
    unittest.main()
