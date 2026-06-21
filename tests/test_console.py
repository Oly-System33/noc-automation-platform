import os
import unittest
from unittest.mock import patch

from app.services.console import Console


class FakeStdout:

    def __init__(self, is_tty):
        self.is_tty = is_tty

    def isatty(self):
        return self.is_tty


class ConsoleColorTest(unittest.TestCase):

    def test_never_disables_ansi_codes(self):
        console = Console(stdout=FakeStdout(True))

        with patch.dict(os.environ, {"CONSOLE_COLORS": "never"}, clear=False):
            value = console.red("PROBLEM")

        self.assertEqual(value, "PROBLEM")
        self.assertNotIn("\033[", value)

    def test_always_forces_ansi_codes_without_tty(self):
        console = Console(stdout=FakeStdout(False))

        with patch.dict(os.environ, {"CONSOLE_COLORS": "always"}, clear=False):
            value = console.red("PROBLEM")

        self.assertIn("\033[", value)
        self.assertIn("PROBLEM", value)

    def test_auto_uses_tty_detection(self):
        tty_console = Console(stdout=FakeStdout(True))
        pipe_console = Console(stdout=FakeStdout(False))

        with patch.dict(os.environ, {"CONSOLE_COLORS": "auto"}, clear=False):
            self.assertIn("\033[", tty_console.green("RECOVERY"))
            self.assertNotIn("\033[", pipe_console.green("RECOVERY"))

    def test_status_colors_keep_original_text(self):
        console = Console(stdout=FakeStdout(False))

        with patch.dict(os.environ, {"CONSOLE_COLORS": "always"}, clear=False):
            problem = console.status("PROBLEM")
            recovery = console.status("RECOVERY")
            warning = console.status("WARNING")
            critical = console.status("Crítica")

        self.assertIn("PROBLEM", problem)
        self.assertIn("RECOVERY", recovery)
        self.assertIn("WARNING", warning)
        self.assertIn("Crítica", critical)
        self.assertIn("\033[31m", problem)
        self.assertIn("\033[32m", recovery)
        self.assertIn("\033[33m", warning)
        self.assertIn("\033[31m", critical)

    def test_error_uses_orange_when_256_colors_are_available(self):
        console = Console(stdout=FakeStdout(False))

        with patch.dict(
            os.environ,
            {"CONSOLE_COLORS": "always", "TERM": "xterm-256color"},
            clear=False,
        ):
            value = console.orange("ERROR")

        self.assertIn("\033[38;5;208m", value)
        self.assertIn("ERROR", value)


if __name__ == "__main__":
    unittest.main()
