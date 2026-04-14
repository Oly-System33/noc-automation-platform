import requests
import os
import smtplib
from email.mime.text import MIMEText
from app.services.incident_service import IncidentService
from app.rules.rule_loader import rule_loader

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_NOC")


class ActionDispatcher:

    def __init__(self):

        self.incident_service = IncidentService()

        self.ACTION_MAP = {
            "email": self._action_email,
            "telegram": self._action_telegram,
            "calls": self._action_calls,
            "jira": self._action_jira,
            "teams": self._action_teams,
        }

        self.smtp_server = "smtp.office365.com"
        self.smtp_port = 587
        self.smtp_user = "sebastian.gomez@cedi.com.ar"
        self.smtp_password = "APP_PASSWORD"

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
            recipient = contact
        else:
            recipient = contact.get("email")

        if not recipient:
            print("[WARNING] No email defined for contact")
            return

        status = self._normalize_status(event.status)

        subject = f"[NOC ALERT] {event.host} - {status}"

        body = (
            f"Host: {event.host}\n"
            f"Trigger: {event.trigger}\n"
            f"Severity: {event.severity}\n"
            f"Status: {status}\n"
            f"Event ID: {event.event_id}"
        )

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = recipient

        try:

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:

                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

        except Exception as e:

            print(f"[ERROR] Email send failed: {e}")
            return

        print(f"[DISPATCH][EMAIL] → {recipient}")

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

        project_key = contact.get("jira_project")

        if not project_key:
            print("[WARNING] No jira_project defined")
            return

        client, host = rule_loader.extract_client_and_host(event.host)

        status = "PROBLEM" if str(event.status) == "1" else "RECOVERY"

        jira_priority = rule_loader.get_jira_priority(
            client,
            event.severity
        )

        print(f"[DEBUG] Creating Jira ticket in project: {project_key}")
        print(f"[DEBUG] Jira priority resolved: {jira_priority}")

        summary = f"{event.trigger} - {host}"

        description = (
            "Alerta detectada automáticamente por NOC Automation Engine\n\n"
            f"Cliente: {client}\n"
            f"Host: {host}\n"
            f"Trigger: {event.trigger}\n"
            f"Severity: {event.severity}\n"
            f"Status: {status}\n"
            f"Event ID: {event.event_id}\n"
        )

        response = self.incident_service.create_incident(
            project_key=project_key,
            summary=summary,
            description=description,
            priority=jira_priority
        )

        print(f"[DISPATCH][JIRA] Ticket creado: {response}")

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
