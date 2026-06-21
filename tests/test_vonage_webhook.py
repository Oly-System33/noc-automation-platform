import os
import unittest
from unittest.mock import patch

from app.api import vonage_webhook


class VonageWebhookNccoTest(unittest.TestCase):

    def test_answer_ncco_enables_barge_in_and_dtmf_input(self):
        with patch.dict(os.environ, {"PUBLIC_BASE_URL": "https://example.com"}, clear=False):
            with patch.object(vonage_webhook.call_service, "get_message", return_value="Mensaje"):
                ncco = vonage_webhook._build_answer_ncco("event-1")

        talk_actions = [action for action in ncco if action.get("action") == "talk"]
        input_actions = [action for action in ncco if action.get("action") == "input"]

        self.assertTrue(talk_actions)
        self.assertTrue(all(action.get("bargeIn") is True for action in talk_actions))
        self.assertEqual(len(input_actions), 1)
        self.assertEqual(input_actions[0].get("type"), ["dtmf"])
        self.assertEqual(input_actions[0].get("dtmf", {}).get("maxDigits"), 1)
        self.assertNotIn("submitOnHash", input_actions[0])

    def test_invalid_option_ncco_keeps_barge_in_on_replay(self):
        with patch.dict(os.environ, {"PUBLIC_BASE_URL": "https://example.com"}, clear=False):
            with patch.object(vonage_webhook.call_service, "get_message", return_value="Mensaje"):
                ncco = vonage_webhook._build_invalid_option_ncco("event-1")

        talk_actions = [action for action in ncco if action.get("action") == "talk"]

        self.assertIn("Opción inválida", talk_actions[0].get("text"))
        self.assertTrue(all(action.get("bargeIn") is True for action in talk_actions))


if __name__ == "__main__":
    unittest.main()
