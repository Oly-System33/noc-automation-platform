import os
import requests
from dotenv import load_dotenv

load_dotenv()


class JiraService:

    def __init__(self):
        self.base_url = os.getenv("JIRA_URL")
        self.email = os.getenv("JIRA_EMAIL")
        self.api_token = os.getenv("JIRA_API_TOKEN")
        self.issue_type = os.getenv("JIRA_ISSUE_TYPE", "Task")
        self.timeout = self._get_timeout()

    def _get_timeout(self):

        try:
            return int(os.getenv("JIRA_TIMEOUT_SECONDS", 5))
        except ValueError:
            return 5

    def _build_response(self, success, status, issue_key=None, http_status=None, error=None, raw_response=None):

        return {
            "success": success,
            "status": status,
            "issue_key": issue_key,
            "http_status": http_status,
            "error": error,
            "raw_response": raw_response,
        }

    def _missing_configuration(self):

        required_values = {
            "JIRA_URL": self.base_url,
            "JIRA_EMAIL": self.email,
            "JIRA_API_TOKEN": self.api_token,
        }

        return [
            name
            for name, value in required_values.items()
            if not value
        ]

    def _safe_json(self, response):

        try:
            return response.json(), None
        except ValueError:
            return None, response.text

    def create_ticket(self, project_key, summary, description, priority, issue_type=None, request_type=None):

        missing_config = self._missing_configuration()

        if missing_config:
            missing = ", ".join(missing_config)
            return self._build_response(
                success=False,
                status="configuration_error",
                error=f"Missing Jira configuration: {missing}",
            )

        url = f"{self.base_url}/rest/api/3/issue"

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        auth = (self.email, self.api_token)

        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": description
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {"name": issue_type or self.issue_type},
                "priority": {"name": priority}
            }
        }

        if request_type:
            payload["fields"]["requestType"] = request_type

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                auth=auth,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout:
            return self._build_response(
                success=False,
                status="timeout",
                error="Jira request timed out",
            )
        except requests.exceptions.ConnectionError:
            return self._build_response(
                success=False,
                status="connection_error",
                error="Jira connection error",
            )
        except requests.exceptions.RequestException as e:
            return self._build_response(
                success=False,
                status="request_error",
                error=str(e),
            )

        raw_response, response_text = self._safe_json(response)

        if response.status_code < 200 or response.status_code >= 300:
            return self._build_response(
                success=False,
                status="http_error",
                http_status=response.status_code,
                error=response_text or str(raw_response),
                raw_response=raw_response,
            )

        if raw_response is None:
            return self._build_response(
                success=False,
                status="invalid_json",
                http_status=response.status_code,
                error="Jira returned invalid JSON",
            )

        if not isinstance(raw_response, dict):
            return self._build_response(
                success=False,
                status="unexpected_response",
                http_status=response.status_code,
                error="Jira response was not a JSON object",
                raw_response=raw_response,
            )

        issue_key = raw_response.get("key")

        if not issue_key:
            return self._build_response(
                success=False,
                status="unexpected_response",
                http_status=response.status_code,
                error="Jira response did not include issue key",
                raw_response=raw_response,
            )

        return self._build_response(
            success=True,
            status="created",
            issue_key=issue_key,
            http_status=response.status_code,
            raw_response=raw_response,
        )
