import unittest
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.operational import audit_router, configuration_router
from app.main import app as main_app
from app.schemas.operational import (
    AuditLogItem,
    AuditLogListResponse,
    OperationalConfigurationResponse,
    RunbookOperationalConfiguration,
    WorkerOperationalConfiguration,
)
from app.services.operational_query_service import operational_query_service


NOW = datetime(2026, 8, 3, tzinfo=timezone.utc)


class OperationalApiTest(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(audit_router)
        app.include_router(configuration_router)
        self.app = app
        self.client = TestClient(app)

    def test_audit_list_passes_filters_and_returns_envelope(self):
        result = AuditLogListResponse(
            items=[AuditLogItem(
                id=5, event_id="event-1", scheduled_action_id=9,
                level="INFO", component="scheduled_actions",
                message="Scheduled action approved",
                context={"scheduled_action_id": 9}, created_at=NOW,
            )], total=1, limit=10, offset=2, generated_at=NOW,
        )
        with patch.object(
            operational_query_service, "list_audit_logs", return_value=result
        ) as query:
            response = self.client.get("/api/audit-logs", params={
                "limit": 10, "offset": 2, "search": "approved",
                "level": "INFO", "component": "scheduled_actions",
                "event_id": "event-1", "created_from": NOW.isoformat(),
                "created_to": NOW.isoformat(),
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["scheduled_action_id"], 9)
        query.assert_called_once()

    def test_audit_context_is_allowlisted(self):
        item = operational_query_service._audit_item(SimpleNamespace(
            id=1, event_id="event-1", level="ERROR", component="worker",
            message="failed", created_at=NOW,
            details={
                "scheduled_action_id": 3, "reason": "timeout",
                "phone": "+15551234567", "token": "secret",
                "response": {"credential": "secret"},
            },
        ))
        serialized = item.model_dump_json()
        self.assertEqual(item.context, {"scheduled_action_id": 3, "reason": "timeout"})
        self.assertNotIn("15551234567", serialized)
        self.assertNotIn("secret", serialized)

    def test_audit_message_redacts_contact_and_credentials(self):
        item = operational_query_service._audit_item(SimpleNamespace(
            id=2,
            event_id="event-2",
            level="ERROR",
            component="worker",
            message=(
                "token=hunter2 operator@example.com +15551234567 "
                "https://internal.example/path"
            ),
            created_at=NOW,
            details={},
        ))
        serialized = item.model_dump_json()
        for secret in (
            "hunter2",
            "operator@example.com",
            "15551234567",
            "internal.example",
        ):
            self.assertNotIn(secret, serialized)

    def test_configuration_uses_safe_defaults_without_constructing_worker(self):
        invalid = {
            "SCHEDULED_ACTION_POLL_INTERVAL_SECONDS": "invalid",
            "SCHEDULED_ACTION_BATCH_SIZE": "invalid",
            "SCHEDULED_ACTION_PROCESSING_TIMEOUT_MINUTES": "invalid",
            "SCHEDULED_ACTION_MAX_ATTEMPTS": "invalid",
            "SMTP_PORT": "not-an-integer",
        }
        with patch.dict(os.environ, invalid), patch(
            "app.services.operational_query_service.scheduled_action_worker.worker",
            None,
        ), patch(
            "app.services.operational_query_service.scheduled_action_worker.worker_thread",
            None,
        ):
            result = operational_query_service.get_configuration()

        self.assertEqual(result.worker.poll_interval_seconds, 30)
        self.assertEqual(result.worker.batch_size, 20)
        self.assertEqual(result.worker.processing_timeout_minutes, 10)
        self.assertEqual(result.worker.max_attempts, 3)

    def test_configuration_is_read_only_and_safe(self):
        result = OperationalConfigurationResponse(
            generated_at=NOW,
            worker=WorkerOperationalConfiguration(
                enabled=False, running=False, ready=True,
                poll_interval_seconds=30, batch_size=20,
                processing_timeout_minutes=10, max_attempts=3,
            ),
            runbooks=RunbookOperationalConfiguration(
                available=True, count=2, cache_count=1, last_reload=None,
            ),
        )
        with patch.object(
            operational_query_service, "get_configuration", return_value=result
        ):
            response = self.client.get("/api/configuration/operational")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertNotIn("path", str(payload).lower())
        self.assertNotIn("origin", str(payload).lower())
        self.assertNotIn("public_base_url", payload)

    def test_openapi_and_main_app_registration(self):
        schema = self.app.openapi()
        self.assertEqual(
            schema["paths"]["/api/audit-logs"]["get"]["responses"]["200"]
            ["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/AuditLogListResponse",
        )
        paths = {route.path for route in main_app.routes}
        self.assertIn("/api/audit-logs", paths)
        self.assertIn("/api/configuration/operational", paths)


if __name__ == "__main__":
    unittest.main()
