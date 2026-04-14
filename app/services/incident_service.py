from app.integrations.jira import JiraService


class IncidentService:

    def __init__(self):
        self.jira_service = JiraService()

    def create_incident(self, project_key: str, summary: str, description: str, priority: str):

        response = self.jira_service.create_ticket(
            project_key=project_key,
            summary=summary,
            description=description,
            priority=priority
        )

        return response

    def process_zabbix_event(self, event):
        print("Evento recibido en IncidentService")
        print(event)
