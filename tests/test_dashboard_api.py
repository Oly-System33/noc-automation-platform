import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dashboard import dashboard_router, incidents_router
from app.main import app as main_app
from app.schemas.dashboard import (
    DashboardIncidentItem,
    DashboardIncidentListResponse,
    DashboardStatus,
    DashboardStatusCounts,
    DashboardSummaryResponse,
)
from app.services.dashboard_query_service import (
    DashboardQueryError,
    dashboard_query_service,
)


NOW = datetime(2026, 8, 2, 3, 0, tzinfo=timezone.utc)


class DashboardApiTest(unittest.TestCase):

    def setUp(self):
        app = FastAPI()
        app.include_router(dashboard_router)
        app.include_router(incidents_router)
        self.app = app
        self.client = TestClient(app)

    def test_summary_returns_typed_service_response(self):
        result = DashboardSummaryResponse(
            generated_at=NOW,
            counts=DashboardStatusCounts(active=2, paused=1),
            by_client={"Banco X": 3},
            total=3,
        )

        with patch.object(
            dashboard_query_service,
            "get_summary",
            return_value=result,
        ) as get_summary:
            response = self.client.get("/api/dashboard/summary")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 3)
        self.assertEqual(response.json()["counts"]["paused"], 1)
        self.assertEqual(response.json()["by_client"], {"Banco X": 3})
        get_summary.assert_called_once_with()

    def test_incidents_passes_validated_filters_to_service(self):
        result = DashboardIncidentListResponse(
            items=[
                DashboardIncidentItem(
                    event_id="event-1",
                    client="Banco X",
                    display_status=DashboardStatus.PAUSED,
                )
            ],
            total=1,
            generated_at=NOW,
        )

        with patch.object(
            dashboard_query_service,
            "list_incidents",
            return_value=result,
        ) as list_incidents:
            response = self.client.get(
                "/api/incidents",
                params={
                    "limit": 25,
                    "client": "Banco X",
                    "status": "paused",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["event_id"], "event-1")
        list_incidents.assert_called_once_with(
            limit=25,
            client="Banco X",
            status=DashboardStatus.PAUSED,
        )

    def test_incident_query_validation_returns_422_without_service_call(self):
        invalid_queries = [
            {"limit": 0},
            {"limit": 501},
            {"status": "not-a-status"},
        ]

        for params in invalid_queries:
            with self.subTest(params=params), patch.object(
                dashboard_query_service,
                "list_incidents",
            ) as list_incidents:
                response = self.client.get("/api/incidents", params=params)

                self.assertEqual(response.status_code, 422)
                list_incidents.assert_not_called()

    def test_controlled_query_errors_return_503_without_internal_details(self):
        with patch.object(
            dashboard_query_service,
            "get_summary",
            side_effect=DashboardQueryError("database password=secret"),
        ):
            response = self.client.get("/api/dashboard/summary")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"detail": "Dashboard data is temporarily unavailable"},
        )
        self.assertNotIn("secret", response.text)

    def test_unexpected_errors_return_generic_500(self):
        with patch.object(
            dashboard_query_service,
            "list_incidents",
            side_effect=RuntimeError("token=secret"),
        ):
            response = self.client.get("/api/incidents")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Internal server error"})
        self.assertNotIn("secret", response.text)

    def test_openapi_documents_routes_models_filters_and_errors(self):
        schema = self.app.openapi()
        summary = schema["paths"]["/api/dashboard/summary"]["get"]
        incidents = schema["paths"]["/api/incidents"]["get"]

        self.assertEqual(
            summary["responses"]["200"]["content"]["application/json"][
                "schema"
            ]["$ref"],
            "#/components/schemas/DashboardSummaryResponse",
        )
        self.assertEqual(
            incidents["responses"]["200"]["content"]["application/json"][
                "schema"
            ]["$ref"],
            "#/components/schemas/DashboardIncidentListResponse",
        )
        self.assertEqual(
            {parameter["name"] for parameter in incidents["parameters"]},
            {"limit", "client", "status"},
        )
        self.assertIn("500", incidents["responses"])
        self.assertIn("503", incidents["responses"])

    def test_main_app_keeps_existing_routes_and_registers_dashboard_routes(self):
        paths = {route.path for route in main_app.routes}

        self.assertIn("/health", paths)
        self.assertIn("/zabbix/webhook", paths)
        self.assertIn("/vonage/answer", paths)
        self.assertIn("/api/dashboard/summary", paths)
        self.assertIn("/api/incidents", paths)


if __name__ == "__main__":
    unittest.main()
