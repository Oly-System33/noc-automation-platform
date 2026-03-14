from app.services.jira_service import JiraService


class IncidentService:

    def __init__(self):
        self.jira_service = JiraService()

    def create_incident(self, summary: str, description: str):

        response = self.jira_service.create_ticket(
            summary=summary,
            description=description
        )

        return response
