from app.services.incident_service import IncidentService


def main():

    incident_service = IncidentService()

    response = incident_service.create_incident(
        summary="Test Incident from NOC Automation",
        description="This ticket was created from the automation platform"
    )

    print(response)


if __name__ == "__main__":
    main()
