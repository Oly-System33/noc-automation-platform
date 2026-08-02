import unittest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.api import health
from app.main import (
    DEFAULT_CORS_ALLOWED_ORIGINS,
    app as main_app,
    configure_cors,
    parse_cors_allowed_origins,
)


class CorsOriginParsingTest(unittest.TestCase):

    def test_missing_configuration_uses_only_local_defaults(self):
        self.assertEqual(
            parse_cors_allowed_origins(None),
            [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ],
        )

    def test_comma_separated_origins_remove_spaces_and_empty_values(self):
        self.assertEqual(
            parse_cors_allowed_origins(
                " http://localhost:5173, ,"
                "http://127.0.0.1:5173,, "
            ),
            [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ],
        )

    def test_wildcard_is_not_used(self):
        self.assertNotIn("*", DEFAULT_CORS_ALLOWED_ORIGINS)
        self.assertNotIn("*", parse_cors_allowed_origins(None))
        self.assertEqual(
            parse_cors_allowed_origins(
                "*, http://localhost:5173, *"
            ),
            ["http://localhost:5173"],
        )


class CorsMiddlewareTest(unittest.TestCase):

    def setUp(self):
        app = FastAPI()
        configure_cors(app, list(DEFAULT_CORS_ALLOWED_ORIGINS))

        @app.get("/resource")
        def get_resource():
            return {"status": "ok"}

        @app.post("/resource")
        def post_resource():
            return {"status": "ok"}

        self.client = TestClient(app)

    def test_local_origins_receive_allow_origin_header(self):
        for origin in DEFAULT_CORS_ALLOWED_ORIGINS:
            with self.subTest(origin=origin):
                response = self.client.get(
                    "/resource",
                    headers={"Origin": origin},
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.headers["access-control-allow-origin"],
                    origin,
                )

    def test_unauthorized_origin_does_not_receive_cors_permission(self):
        response = self.client.get(
            "/resource",
            headers={"Origin": "https://sitio-no-autorizado.example"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_valid_preflight_allows_configured_methods_and_headers(self):
        for method in ("GET", "POST"):
            with self.subTest(method=method):
                response = self.client.options(
                    "/resource",
                    headers={
                        "Origin": "http://localhost:5173",
                        "Access-Control-Request-Method": method,
                        "Access-Control-Request-Headers": (
                            "Content-Type, Authorization"
                        ),
                    },
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.headers["access-control-allow-origin"],
                    "http://localhost:5173",
                )
                allowed_methods = {
                    value.strip()
                    for value in response.headers[
                        "access-control-allow-methods"
                    ].split(",")
                }
                self.assertEqual(
                    allowed_methods,
                    {"GET", "POST", "OPTIONS"},
                )

    def test_delete_preflight_is_rejected_and_not_advertised(self):
        response = self.client.options(
            "/resource",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "DELETE",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(
            "DELETE",
            response.headers["access-control-allow-methods"],
        )

    def test_configuration_does_not_use_wildcards_or_credentials(self):
        middleware = next(
            middleware
            for middleware in main_app.user_middleware
            if middleware.cls is CORSMiddleware
        )

        self.assertNotIn("*", middleware.kwargs["allow_origins"])
        self.assertNotIn("*", middleware.kwargs["allow_methods"])
        self.assertNotIn("*", middleware.kwargs["allow_headers"])
        self.assertFalse(middleware.kwargs["allow_credentials"])

    @patch.object(health.engine, "connect")
    def test_health_continues_working(self, connect):
        connection = MagicMock()
        connect.return_value.__enter__.return_value = connection

        response = TestClient(main_app).get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "database": "ok"},
        )

    def test_existing_endpoints_remain_registered(self):
        routes = {
            (method, route.path)
            for route in main_app.routes
            for method in getattr(route, "methods", set())
        }

        expected_routes = {
            ("GET", "/api/dashboard/summary"),
            ("GET", "/api/incidents"),
            ("GET", "/api/operations"),
            ("GET", "/api/approvals"),
            (
                "POST",
                "/api/scheduled-actions/{scheduled_action_id}/pause",
            ),
            (
                "POST",
                "/api/scheduled-actions/{scheduled_action_id}/resume",
            ),
        }

        self.assertTrue(expected_routes.issubset(routes))


if __name__ == "__main__":
    unittest.main()
