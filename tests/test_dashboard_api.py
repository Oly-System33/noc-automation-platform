import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dashboard import (
    approvals_router,
    dashboard_router,
    incidents_router,
    operations_router,
)
from app.main import app as main_app
from app.schemas.dashboard import (
    DashboardApprovalListResponse,
    DashboardIncidentItem,
    DashboardIncidentListResponse,
    DashboardOperationItem,
    DashboardOperationListResponse,
    DashboardOperationStatus,
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
        app.include_router(operations_router)
        app.include_router(approvals_router)
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

    def test_operations_default_parameters_return_200(self):
        result = DashboardOperationListResponse(
            items=[],
            total=0,
            generated_at=NOW,
        )

        with patch.object(
            dashboard_query_service,
            "list_operations",
            return_value=result,
        ) as list_operations:
            response = self.client.get("/api/operations")

        self.assertEqual(response.status_code, 200)
        list_operations.assert_called_once_with(
            limit=100,
            client=None,
            status=None,
        )

    def test_operations_accept_boundaries_and_pass_filters(self):
        result = DashboardOperationListResponse(
            items=[
                DashboardOperationItem(
                    scheduled_action_id=42,
                    event_id="event-1",
                    action="jira",
                    internal_state="paused",
                    display_status=DashboardOperationStatus.PAUSED,
                )
            ],
            total=1,
            generated_at=NOW,
        )
        cases = [
            (1, "paused", DashboardOperationStatus.PAUSED),
            (500, "executed", DashboardOperationStatus.EXECUTED),
        ]

        for limit, status, expected_status in cases:
            with self.subTest(limit=limit, status=status), patch.object(
                dashboard_query_service,
                "list_operations",
                return_value=result,
            ) as list_operations:
                response = self.client.get(
                    "/api/operations",
                    params={
                        "limit": limit,
                        "client": "Banco X",
                        "status": status,
                    },
                )

                self.assertEqual(response.status_code, 200)
                list_operations.assert_called_once_with(
                    limit=limit,
                    client="Banco X",
                    status=expected_status,
                )

    def test_operations_reject_invalid_limit_and_status(self):
        invalid_queries = [
            {"limit": 0},
            {"limit": 501},
            {"status": "invalid"},
        ]

        for params in invalid_queries:
            with self.subTest(params=params), patch.object(
                dashboard_query_service,
                "list_operations",
            ) as list_operations:
                response = self.client.get("/api/operations", params=params)

                self.assertEqual(response.status_code, 422)
                list_operations.assert_not_called()

    def test_operations_map_controlled_and_unexpected_errors(self):
        cases = [
            (
                DashboardQueryError("database password=secret"),
                503,
                "Dashboard data is temporarily unavailable",
            ),
            (
                RuntimeError("token=secret"),
                500,
                "Unable to retrieve dashboard data",
            ),
        ]

        for error, status_code, detail in cases:
            with self.subTest(status_code=status_code), patch.object(
                dashboard_query_service,
                "list_operations",
                side_effect=error,
            ):
                response = self.client.get("/api/operations")

                self.assertEqual(response.status_code, status_code)
                self.assertEqual(response.json(), {"detail": detail})
                self.assertNotIn("secret", response.text)

    def test_approvals_defaults_client_and_limit_boundaries(self):
        result = DashboardApprovalListResponse(
            items=[],
            total=0,
            generated_at=NOW,
        )
        cases = [
            ({}, 100, None),
            ({"limit": 1, "client": "Banco X"}, 1, "Banco X"),
            ({"limit": 500}, 500, None),
        ]

        for params, expected_limit, expected_client in cases:
            with self.subTest(params=params), patch.object(
                dashboard_query_service,
                "list_approvals",
                return_value=result,
            ) as list_approvals:
                response = self.client.get("/api/approvals", params=params)

                self.assertEqual(response.status_code, 200)
                list_approvals.assert_called_once_with(
                    limit=expected_limit,
                    client=expected_client,
                )

    def test_approvals_validate_limits_and_map_errors(self):
        for limit in (0, 501):
            with self.subTest(limit=limit), patch.object(
                dashboard_query_service,
                "list_approvals",
            ) as list_approvals:
                response = self.client.get(
                    "/api/approvals",
                    params={"limit": limit},
                )
                self.assertEqual(response.status_code, 422)
                list_approvals.assert_not_called()

        errors = [
            (DashboardQueryError("database error"), 503),
            (RuntimeError("internal secret"), 500),
        ]

        for error, status_code in errors:
            with self.subTest(status_code=status_code), patch.object(
                dashboard_query_service,
                "list_approvals",
                side_effect=error,
            ):
                response = self.client.get("/api/approvals")
                self.assertEqual(response.status_code, status_code)

    def test_openapi_documents_operations_and_approvals(self):
        schema = self.app.openapi()
        operations = schema["paths"]["/api/operations"]["get"]
        approvals = schema["paths"]["/api/approvals"]["get"]

        self.assertEqual(
            operations["responses"]["200"]["content"][
                "application/json"
            ]["schema"]["$ref"],
            "#/components/schemas/DashboardOperationListResponse",
        )
        self.assertEqual(
            approvals["responses"]["200"]["content"][
                "application/json"
            ]["schema"]["$ref"],
            "#/components/schemas/DashboardApprovalListResponse",
        )
        self.assertEqual(
            {parameter["name"] for parameter in operations["parameters"]},
            {"limit", "client", "status"},
        )
        self.assertEqual(
            {parameter["name"] for parameter in approvals["parameters"]},
            {"limit", "client"},
        )

        for endpoint in (operations, approvals):
            self.assertIn("422", endpoint["responses"])
            self.assertIn("500", endpoint["responses"])
            self.assertIn("503", endpoint["responses"])

    def test_main_app_keeps_existing_routes_and_registers_dashboard_routes(self):
        paths = {route.path for route in main_app.routes}

        self.assertIn("/health", paths)
        self.assertIn("/zabbix/webhook", paths)
        self.assertIn("/vonage/answer", paths)
        self.assertIn("/api/dashboard/summary", paths)
        self.assertIn("/api/incidents", paths)
        self.assertIn("/api/operations", paths)
        self.assertIn("/api/approvals", paths)
        self.assertIn("/api/scheduled-actions/{scheduled_action_id}/pause", paths)
        self.assertIn("/api/scheduled-actions/{scheduled_action_id}/resume", paths)


if __name__ == "__main__":
    unittest.main()
