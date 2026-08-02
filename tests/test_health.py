import json
import unittest
from unittest.mock import MagicMock, patch

from app.api import health


class HealthEndpointTest(unittest.TestCase):

    @patch.object(health.engine, "connect")
    def test_health_returns_ok_when_database_is_available(self, connect):
        connection = MagicMock()
        connect.return_value.__enter__.return_value = connection

        response = health.health_check()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.body),
            {"status": "ok", "database": "ok"},
        )
        connection.execute.assert_called_once()

    @patch.object(health.engine, "connect", side_effect=Exception("database error"))
    def test_health_returns_unavailable_when_database_fails(self, connect):
        response = health.health_check()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            json.loads(response.body),
            {"status": "error", "database": "unavailable"},
        )
        connect.assert_called_once()


if __name__ == "__main__":
    unittest.main()
