import unittest

from app.models.event_model import ZabbixEvent
from app.services.action_dispatcher import ActionDispatcher
from app.services.alert_message_builder import AlertMessageBuilder


class AlertMessageBuilderTest(unittest.TestCase):

    def setUp(self):
        self.event = ZabbixEvent(
            host="Banco X/test-noc",
            trigger="Zabbix agent sin datos por 1 minuto",
            severity="Critical",
            status="1",
            event_id="event-1",
            timestamp="2026-06-21T12:00:00Z",
        )
        self.event.client = "Banco X"
        self.event.parsed_host = "test-noc"

    def jira_context(self, success=True):
        return {
            "jira": {
                "attempted": True,
                "success": success,
                "issue_key": "CAG-123" if success else None,
                "project_key": "CAG" if success else None,
                "url": "https://jira.example/browse/CAG-123" if success else None,
                "error": "technical error" if not success else None,
            }
        }

    def test_telegram_message_includes_successful_jira_ticket(self):
        message = AlertMessageBuilder(self.event, self.jira_context()).telegram_message()

        self.assertIn("Ticket Jira: CAG-123", message)
        self.assertIn("URL: https://jira.example/browse/CAG-123", message)

    def test_teams_message_omits_failed_jira_ticket(self):
        message = AlertMessageBuilder(self.event, self.jira_context(success=False)).teams_message()

        self.assertNotIn("Ticket Jira", message)
        self.assertNotIn("technical error", message)

    def test_call_speech_includes_successful_jira_ticket(self):
        speech = AlertMessageBuilder(self.event, self.jira_context()).call_speech()

        self.assertIn("Se creó el ticket Jira CAG-123", speech)

    def test_action_order_runs_jira_first(self):
        dispatcher = ActionDispatcher()

        actions = dispatcher.order_execution_actions(["telegram", "calls", "jira", "teams"])

        self.assertEqual(actions, ["jira", "telegram", "teams", "calls"])

    def test_email_summary_includes_manual_required_call_result(self):
        body = AlertMessageBuilder(self.event, self.jira_context()).email_summary_body([
            {
                "action": "calls",
                "success": True,
                "attempt_count": 3,
                "manual_required": True,
            }
        ])

        self.assertIn("Se realizaron 3 intentos de llamada", body)
        self.assertIn("No se recibió confirmación telefónica", body)
        self.assertIn("gestión telefónica continuará", body)


if __name__ == "__main__":
    unittest.main()
