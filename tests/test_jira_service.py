import os
import unittest
from unittest.mock import Mock, patch

import requests

from app.integrations.jira import JiraService


class JiraServiceTest(unittest.TestCase):

    def service(self):
        return JiraService()

    def jira_env(self):
        return {
            "JIRA_URL": "https://jira.example.com",
            "JIRA_EMAIL": "noc@example.com",
            "JIRA_API_TOKEN": "secret-token",
        }

    def create_ticket(self, service):
        return service.create_ticket(
            project_key="NOC",
            summary="Test summary",
            description="Test description",
            priority="High",
        )

    def response(self, status_code, json_data=None, text=""):
        response = Mock()
        response.status_code = status_code
        response.text = text

        if isinstance(json_data, Exception):
            response.json.side_effect = json_data
        else:
            response.json.return_value = json_data

        return response

    @patch.dict(os.environ, {}, clear=True)
    def test_create_ticket_returns_configuration_error_when_env_is_missing(self):
        result = self.create_ticket(self.service())

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "configuration_error")
        self.assertIn("JIRA_URL", result["error"])
        self.assertIn("JIRA_EMAIL", result["error"])
        self.assertIn("JIRA_API_TOKEN", result["error"])

    @patch.dict(os.environ, {
        "JIRA_URL": "https://jira.example.com",
        "JIRA_EMAIL": "noc@example.com",
        "JIRA_API_TOKEN": "secret-token",
        "JIRA_TIMEOUT_SECONDS": "7",
    }, clear=True)
    @patch("app.integrations.jira.requests.post")
    def test_create_ticket_returns_success_for_created_issue(self, post):
        post.return_value = self.response(
            201,
            {"key": "NOC-123", "id": "10001"},
        )

        result = self.create_ticket(self.service())

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "created")
        self.assertEqual(result["issue_key"], "NOC-123")
        self.assertEqual(result["http_status"], 201)
        self.assertEqual(result["raw_response"], {"key": "NOC-123", "id": "10001"})
        self.assertEqual(post.call_args.kwargs["timeout"], 7)

    @patch.dict(os.environ, {
        "JIRA_URL": "https://jira.example.com",
        "JIRA_EMAIL": "noc@example.com",
        "JIRA_API_TOKEN": "secret-token",
    }, clear=True)
    @patch("app.integrations.jira.requests.post")
    def test_create_ticket_handles_timeout(self, post):
        post.side_effect = requests.exceptions.Timeout()

        result = self.create_ticket(self.service())

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["error"], "Jira request timed out")

    @patch.dict(os.environ, {
        "JIRA_URL": "https://jira.example.com",
        "JIRA_EMAIL": "noc@example.com",
        "JIRA_API_TOKEN": "secret-token",
    }, clear=True)
    @patch("app.integrations.jira.requests.post")
    def test_create_ticket_handles_connection_error(self, post):
        post.side_effect = requests.exceptions.ConnectionError()

        result = self.create_ticket(self.service())

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "connection_error")
        self.assertEqual(result["error"], "Jira connection error")

    @patch.dict(os.environ, {
        "JIRA_URL": "https://jira.example.com",
        "JIRA_EMAIL": "noc@example.com",
        "JIRA_API_TOKEN": "secret-token",
    }, clear=True)
    @patch("app.integrations.jira.requests.post")
    def test_create_ticket_handles_http_error(self, post):
        post.return_value = self.response(
            400,
            {"errorMessages": ["Invalid project"]},
        )

        result = self.create_ticket(self.service())

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "http_error")
        self.assertEqual(result["http_status"], 400)
        self.assertEqual(result["raw_response"], {"errorMessages": ["Invalid project"]})

    @patch.dict(os.environ, {
        "JIRA_URL": "https://jira.example.com",
        "JIRA_EMAIL": "noc@example.com",
        "JIRA_API_TOKEN": "secret-token",
    }, clear=True)
    @patch("app.integrations.jira.requests.post")
    def test_create_ticket_handles_invalid_json(self, post):
        post.return_value = self.response(
            201,
            ValueError("invalid json"),
            text="not json",
        )

        result = self.create_ticket(self.service())

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "invalid_json")
        self.assertEqual(result["http_status"], 201)

    @patch.dict(os.environ, {
        "JIRA_URL": "https://jira.example.com",
        "JIRA_EMAIL": "noc@example.com",
        "JIRA_API_TOKEN": "secret-token",
    }, clear=True)
    @patch("app.integrations.jira.requests.post")
    def test_create_ticket_handles_unexpected_success_response(self, post):
        post.return_value = self.response(201, {"id": "10001"})

        result = self.create_ticket(self.service())

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "unexpected_response")
        self.assertEqual(result["raw_response"], {"id": "10001"})

    @patch.dict(os.environ, {
        "JIRA_URL": "https://jira.example.com",
        "JIRA_EMAIL": "noc@example.com",
        "JIRA_API_TOKEN": "secret-token",
    }, clear=True)
    @patch("app.integrations.jira.requests.post")
    def test_create_ticket_handles_non_object_json_response(self, post):
        post.return_value = self.response(201, ["NOC-123"])

        result = self.create_ticket(self.service())

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "unexpected_response")
        self.assertEqual(result["raw_response"], ["NOC-123"])


if __name__ == "__main__":
    unittest.main()
