from app.integrations.jira import JiraService


class IncidentService:

    def __init__(self):
        self.jira_service = JiraService()

    def _error_response(self, status, error, raw_response=None):

        return {
            "success": False,
            "status": status,
            "issue_key": None,
            "http_status": None,
            "error": error,
            "raw_response": raw_response,
        }

    def create_incident(self, project_key: str, summary: str, description: str, priority: str, issue_type: str = None, request_type: str = None):

        try:
            response = self.jira_service.create_ticket(
                project_key=project_key,
                summary=summary,
                description=description,
                priority=priority,
                issue_type=issue_type,
                request_type=request_type
            )
        except Exception as e:
            return self._error_response("unexpected_error", str(e))

        expected_keys = {
            "success",
            "status",
            "issue_key",
            "http_status",
            "error",
            "raw_response",
        }

        if not isinstance(response, dict) or not expected_keys.issubset(response):
            return self._error_response(
                "unexpected_response",
                "Jira service returned an unexpected response",
                response,
            )

        return response

    def process_zabbix_event(self, event):
        print("Evento recibido en IncidentService")
        print(event)
