import requests
import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_NOC")


class ActionDispatcher:

    def __init__(self):

        self.ACTION_MAP = {
            "email": self._action_email,
            "telegram": self._action_telegram,
            "calls": self._action_calls,
            "jira": self._action_jira,
            "teams": self._action_teams,
        }

    def _normalize_status(self, status):

        return {
            "1": "PROBLEM",
            "0": "RECOVERY"
        }.get(str(status), str(status))

    def dispatch(self, event, actions: list, contacts: list):

        print("\n[DISPATCHER] Starting action dispatch...")
        print(
            f"[EVENT] {event.event_id} | "
            f"{event.status} | "
            f"{event.host}"
        )

        for action in actions:

            handler = self.ACTION_MAP.get(action)

            if not handler:
                print(f"[WARNING] Unknown action type: {action}")
                continue

            try:
                self._dispatch_single_action(
                    handler,
                    action,
                    event,
                    contacts
                )

            except Exception as e:
                print(
                    f"[ERROR] Failed executing action "
                    f"'{action}': {e}"
                )

    def _dispatch_single_action(self, handler, action, event, contacts):

        for contact in contacts:
            handler(event, contact)

    # ========================
    # ACTION HANDLERS
    # ========================

    def _action_email(self, event, contact):

        if isinstance(contact, str):
            email = contact
        else:
            email = contact.get("email")

        if not email:
            print("[WARNING] No email defined for contact")
            return

        print(
            f"[DISPATCH][EMAIL] → {email} | "
            f"{event.host} | "
            f"{event.trigger} | "
            f"{event.status}"
        )

    def _action_telegram(self, event, contact):

        chat_id = contact.get("telegram")

        if not chat_id:
            print("[WARNING] No telegram defined for contact")
            return

        status = self._normalize_status(event.status)

        icon = "🚨" if status == "PROBLEM" else "✅"

        message = (
            f"🚨 ALERTA NOC\n"
            f"Host: {event.host}\n"
            f"Trigger: {event.trigger}\n"
            f"Severity: {event.severity}\n"
            f"Status: {status}"
        )

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        try:

            response = requests.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": message
                },
                timeout=3
            )

        except requests.exceptions.RequestException as e:

            print(f"[ERROR] Telegram connection error: {e}")
            return

        if response.status_code != 200:
            print(f"[ERROR] Telegram send failed: {response.text}")
            return

        print(f"[DISPATCH][TELEGRAM] → {chat_id}")

    def _action_calls(self, event, contact):

        phone = contact.get("phone")

        if not phone:
            print("[WARNING] No phone defined for contact")
            return

        print(
            f"[DISPATCH][CALL] → {phone} | "
            f"{event.host} | "
            f"{event.trigger} | "
            f"{event.status}"
        )

    def _action_jira(self, event, contact):

        jira = contact.get("jira")

        if not jira:
            print("[WARNING] No jira contact defined")
            return

        print(
            f"[DISPATCH][JIRA] → {jira} | "
            f"{event.host} | "
            f"{event.trigger} | "
            f"{event.status}"
        )

    def _action_teams(self, event, contact):

        teams = contact.get("teams")

        if not teams:
            print("[WARNING] No teams webhook defined")
            return

        print(
            f"[DISPATCH][TEAMS] → {teams} | "
            f"{event.host} | "
            f"{event.trigger} | "
            f"{event.status}"
        )
