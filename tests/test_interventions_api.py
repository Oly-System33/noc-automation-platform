import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.interventions import router
from app.main import app as main_app
from app.schemas.interventions import InterventionItem
from app.services.intervention_service import (
    InterventionDataError,
    InterventionNotFound,
    InterventionRetryNotSafe,
    intervention_service,
)


class InterventionsApiTest(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.app = app
        self.client = TestClient(app)

    def test_list_validates_limit_and_returns_typed_rows(self):
        item = InterventionItem(
            intervention_id="processed_event:3",
            source_type="processed_event",
            source_id=3,
            event_id="event-3",
            status="failed",
            detected_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
            runbook_available=False,
            failure_reason="Event processing failed",
        )
        with patch.object(
            intervention_service, "list_interventions", return_value=[item]
        ) as list_interventions:
            response = self.client.get("/api/interventions", params={"limit": 3})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["intervention_id"], "processed_event:3")
        list_interventions.assert_called_once_with(limit=3)

        for limit in (0, 101):
            with self.subTest(limit=limit):
                response = self.client.get(
                    "/api/interventions", params={"limit": limit}
                )
                self.assertEqual(response.status_code, 422)

    def test_retry_maps_not_found_and_safe_conflict(self):
        cases = [
            (InterventionNotFound(), 404, "intervention_not_found"),
            (InterventionRetryNotSafe(), 409, "retry_not_safe"),
        ]
        for error, status, code in cases:
            with self.subTest(status=status), patch.object(
                intervention_service, "reject_retry", side_effect=error
            ):
                response = self.client.post(
                    "/api/interventions/scheduled_action:9/retry"
                )
            self.assertEqual(response.status_code, status)
            self.assertEqual(response.json()["code"], code)
            if status == 409:
                self.assertEqual(response.json()["detail"], "retry_not_safe")

    def test_controlled_and_unexpected_failures_are_generic(self):
        cases = [
            (InterventionDataError("password=secret"), 503, "interventions_unavailable"),
            (RuntimeError("token=secret"), 500, "internal_error"),
        ]
        for error, status, code in cases:
            with self.subTest(status=status), patch.object(
                intervention_service, "list_interventions", side_effect=error
            ):
                response = self.client.get("/api/interventions")
            self.assertEqual(response.status_code, status)
            self.assertEqual(response.json()["code"], code)
            self.assertNotIn("secret", response.text)

    def test_runbook_not_found_is_404(self):
        with patch.object(
            intervention_service,
            "get_runbook",
            side_effect=InterventionNotFound(),
        ):
            response = self.client.get(
                "/api/interventions/processed_event:1/runbook"
            )
        self.assertEqual(response.status_code, 404)

    def test_openapi_and_main_app_register_all_routes(self):
        schema = self.app.openapi()
        listing = schema["paths"]["/api/interventions"]["get"]
        retry = schema["paths"]["/api/interventions/{intervention_id}/retry"]["post"]
        runbook = schema["paths"]["/api/interventions/{intervention_id}/runbook"]["get"]

        self.assertEqual(listing["parameters"][0]["name"], "limit")
        self.assertIn("503", listing["responses"])
        self.assertIn("409", retry["responses"])
        self.assertEqual(
            runbook["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/InterventionRunbook",
        )
        paths = {route.path for route in main_app.routes}
        self.assertIn("/api/interventions", paths)
        self.assertIn("/api/interventions/{intervention_id}/retry", paths)
        self.assertIn("/api/interventions/{intervention_id}/runbook", paths)


if __name__ == "__main__":
    unittest.main()
