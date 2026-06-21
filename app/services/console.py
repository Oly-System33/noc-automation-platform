import os
import sys


RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
GRAY = "\033[90m"
BRIGHT_YELLOW = "\033[93m"
ORANGE_256 = "\033[38;5;208m"


class Console:

    LEVELS = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
    }

    def __init__(self, stdout=None):
        self.stdout = stdout or sys.stdout

    def colors_mode(self):
        mode = os.getenv("CONSOLE_COLORS", "auto").strip().lower()

        if mode not in ("auto", "always", "never"):
            return "auto"

        return mode

    def log_mode(self):
        mode = os.getenv("CONSOLE_LOG_MODE", "demo").strip().lower()

        if mode not in ("demo", "technical"):
            return "demo"

        return mode

    def log_level(self):
        level = os.getenv("CONSOLE_LOG_LEVEL", "INFO").strip().upper()

        if level not in self.LEVELS:
            return "INFO"

        return level

    def should_color(self):
        mode = self.colors_mode()

        if mode == "always":
            return True

        if mode == "never":
            return False

        return bool(getattr(self.stdout, "isatty", lambda: False)())

    def supports_256_colors(self):
        term = os.getenv("TERM", "")
        colorterm = os.getenv("COLORTERM", "")

        return "256color" in term or colorterm in ("truecolor", "24bit")

    def should_log(self, level):
        level_value = self.LEVELS.get(str(level).upper(), self.LEVELS["INFO"])
        configured_value = self.LEVELS[self.log_level()]

        return level_value >= configured_value

    def color(self, text, color_name):
        text = str(text)

        if not self.should_color():
            return text

        colors = {
            "bold": BOLD,
            "red": RED,
            "green": GREEN,
            "yellow": YELLOW,
            "bright_yellow": BRIGHT_YELLOW,
            "cyan": CYAN,
            "gray": GRAY,
            "orange": ORANGE_256 if self.supports_256_colors() else BRIGHT_YELLOW,
        }
        code = colors.get(color_name)

        if not code:
            return text

        return f"{code}{text}{RESET}"

    def bold(self, text):
        return self.color(text, "bold")

    def red(self, text):
        return self.color(text, "red")

    def green(self, text):
        return self.color(text, "green")

    def yellow(self, text):
        return self.color(text, "yellow")

    def orange(self, text):
        return self.color(text, "orange")

    def cyan(self, text):
        return self.color(text, "cyan")

    def gray(self, text):
        return self.color(text, "gray")

    def level(self, level):
        level = str(level).upper()

        if level == "ERROR":
            return self.orange(level)

        if level == "WARNING":
            return self.yellow(level)

        if level == "SUCCESS":
            return self.green(level)

        if level == "DEBUG":
            return self.gray(level)

        if level == "INFO":
            return self.cyan(level)

        return level

    def status(self, status):
        status_text = str(status)
        normalized = status_text.strip().lower()

        if normalized in ("problem", "critical", "critica", "crítica", "disaster"):
            return self.red(status_text)

        if normalized in ("recovery", "resolved", "ok", "closed"):
            return self.green(status_text)

        if normalized in ("warning", "warn"):
            return self.yellow(status_text)

        if normalized in ("error", "failed", "failure"):
            return self.orange(status_text)

        if normalized in ("success", "created", "confirmed"):
            return self.green(status_text)

        if normalized == "debug":
            return self.gray(status_text)

        if normalized == "info":
            return self.cyan(status_text)

        return status_text

    def log(self, level, message):
        if self.should_log(level):
            print(message)


console = Console()
