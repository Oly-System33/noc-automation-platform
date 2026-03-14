from app.services.jira_service import JiraService


def main():

    jira = JiraService()

    response = jira.create_ticket(
        summary="Test Incident from NOC Automation",
        description="This ticket was created from the automation platform"
    )

    print(response)


if __name__ == "__main__":
    main()
