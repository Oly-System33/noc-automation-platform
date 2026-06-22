import unittest
from unittest.mock import patch

from app.models.event_model import ZabbixEvent
from app.services.persistence_service import PersistenceService
from app.services.action_dispatcher import ActionDispatcher
from app.services.scheduled_action_worker import ScheduledActionWorker


class ActionDispatcherResultTest(unittest.TestCase):

    def test_dispatch_returns_success_summary(self):
        dispatcher = ActionDispatcher()
        dispatcher.ACTION_MAP = {
            "ok": lambda event, contact, context=None: True,
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
            "fail": lambda event, contact, context=None: False,
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

    def test_normalize_email_recipients_dedupes_common_separators(self):
        dispatcher = ActionDispatcher()

        recipients = dispatcher.normalize_email_recipients([
            " NOC@example.com;guardia@example.com ",
            "noc@example.com|otro@example.com, Guardia@Example.com",
        ])

        self.assertEqual(
            recipients,
            ["noc@example.com", "guardia@example.com", "otro@example.com"],
        )

    def test_email_summary_body_only_includes_successful_actions(self):
        dispatcher = ActionDispatcher()
        event = ZabbixEvent(
            host="client/host",
            trigger="trigger",
            severity="High",
            status="1",
            event_id="summary-body",
            timestamp="2026-06-21T12:00:00Z",
        )
        event.client = "client"
        event.parsed_host = "host"
        event.trigger_group = "availability"

        body = dispatcher._build_email_summary_body(
            event,
            [
                {
                    "action": "jira",
                    "success": True,
                    "issue_key": "NOC-1",
                    "project_key": "NOC",
                },
                {
                    "action": "telegram",
                    "success": False,
                    "error": "technical failure",
                },
                {
                    "action": "calls",
                    "success": True,
                    "phone": "54911",
                    "attempt_count": 1,
                    "status": "confirmed",
                    "confirmed": True,
                },
            ],
        )

        self.assertIn("NOC-1", body)
        self.assertIn("Llamada confirmada por la guardia", body)
        self.assertIn("Intento confirmado", body)
        self.assertNotIn("technical failure", body)
        self.assertNotIn("Telegram enviado", body)


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

    def test_worker_executes_actions_before_single_email_summary(self):
        calls = []

        class FakeDispatcher:

            def build_dispatch_context(self, event):
                return {"jira": {"success": False}}

            def order_execution_actions(self, actions):
                priority = {"jira": 0, "telegram": 1, "teams": 2, "calls": 3}
                return sorted(actions, key=lambda action: priority.get(action, 100))

            def dispatch(self, event, actions, contacts, context=None):
                calls.append(("dispatch", actions, contacts))
                return {
                    "success": True,
                    "results": [{"action": "jira", "success": True, "issue_key": "NOC-1"}],
                    "context": {"jira": {"success": True, "issue_key": "NOC-1"}},
                }

            def send_email_summary(self, event, recipients, action_results, context=None):
                calls.append(("summary", recipients, action_results))
                return {
                    "action": "email_summary",
                    "success": True,
                    "sent": True,
                    "recipients": recipients,
                }

        worker = ScheduledActionWorker(dispatcher=FakeDispatcher())
        scheduled_action = {
            "event_id": "event-1",
            "client": "Banco X",
            "host": "test-noc",
            "trigger": "Zabbix agent unavailable",
            "severity": "High",
            "trigger_group": "availability",
            "created_at": "2026-06-20T10:00:00",
            "actions": ["email", "telegram", "jira"],
            "contacts_payload": {
                "target_contact": {"jira_project": "NOC"},
                "execution_actions": ["telegram", "jira"],
                "summary_recipients": ["noc@example.com"],
            },
        }

        result = worker._execute_scheduled_action(scheduled_action)

        self.assertTrue(result["success"])
        self.assertEqual(calls[0][0], "dispatch")
        self.assertEqual(calls[0][1], ["jira", "telegram"])
        self.assertEqual(calls[1][0], "summary")
        self.assertEqual(calls[1][1], ["noc@example.com"])
        self.assertEqual(calls[1][2][0]["issue_key"], "NOC-1")

    def test_manual_approval_without_oncall_uses_pre_target_and_blocks_calls(self):
        calls = []

        class FakeDispatcher:

            def normalize_email_recipients(self, values):
                return [value for value in values if value]

            def build_dispatch_context(self, event):
                return {}

            def order_execution_actions(self, actions):
                return actions

            def dispatch(self, event, actions, contacts, context=None):
                calls.append((actions, contacts[0]))
                return {"success": True, "results": [], "context": context}

            def send_email_summary(self, event, recipients, action_results, context=None):
                calls.append(("summary", recipients))
                return {"action": "email_summary", "success": True, "sent": True}

        class FakeRuleLoader:

            def get_contact(self, client, team):
                contacts = {
                    "baseline": {"email": "baseline@example.com"},
                    "noc": {"team": "noc", "email": "noc@example.com", "telegram": "chat"},
                }
                return contacts.get(team)

            def get_oncall_contact(self, client, team):
                return None

            def get_jira_priority(self, client, severity):
                return "High"

        scheduled_action = {
            "event_id": "event-approval",
            "client": "Banco X",
            "host": "test-noc",
            "trigger": "Zabbix agent unavailable",
            "severity": "High",
            "trigger_group": "availability",
            "created_at": "2026-06-20T10:00:00",
            "actions": ["telegram", "calls", "email"],
            "target": "guardia",
            "pre_target": "noc",
            "execution_mode": "manual_approval",
            "contacts_payload": {},
        }

        worker = ScheduledActionWorker(dispatcher=FakeDispatcher())

        with patch("app.services.scheduled_action_worker.rule_loader", FakeRuleLoader()):
            result = worker._execute_scheduled_action(scheduled_action)

        self.assertTrue(result["success"])
        self.assertEqual(calls[0][0], ["telegram", "calls"])
        self.assertEqual(calls[0][1]["team"], "noc")
        self.assertFalse(calls[0][1]["_calls_allowed"])
        self.assertEqual(calls[1], ("summary", ["baseline@example.com", "noc@example.com"]))

    def test_manual_approval_with_oncall_allows_calls(self):
        calls = []

        class FakeDispatcher:

            def normalize_email_recipients(self, values):
                return [value for value in values if value]

            def build_dispatch_context(self, event):
                return {}

            def order_execution_actions(self, actions):
                return actions

            def dispatch(self, event, actions, contacts, context=None):
                calls.append((actions, contacts[0]))
                return {"success": True, "results": [], "context": context}

            def send_email_summary(self, event, recipients, action_results, context=None):
                return {"action": "email_summary", "success": True, "sent": True}

        class FakeRuleLoader:

            def get_contact(self, client, team):
                return {"email": "baseline@example.com"} if team == "baseline" else None

            def get_oncall_contact(self, client, team):
                return {"team": team, "email": "guardia@example.com", "phone": "54911"}

            def get_jira_priority(self, client, severity):
                return "High"

        scheduled_action = {
            "event_id": "event-approval-oncall",
            "client": "Banco X",
            "host": "test-noc",
            "trigger": "Zabbix agent unavailable",
            "severity": "High",
            "trigger_group": "availability",
            "created_at": "2026-06-20T10:00:00",
            "actions": ["calls"],
            "target": "guardia",
            "pre_target": "noc",
            "execution_mode": "manual_approval",
            "contacts_payload": {},
        }

        worker = ScheduledActionWorker(dispatcher=FakeDispatcher())

        with patch("app.services.scheduled_action_worker.rule_loader", FakeRuleLoader()):
            result = worker._execute_scheduled_action(scheduled_action)

        self.assertTrue(result["success"])
        self.assertTrue(calls[0][1]["_calls_allowed"])


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
