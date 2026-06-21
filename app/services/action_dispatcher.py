import requests
import os
import re
import smtplib
from email.mime.text import MIMEText
from app.services.incident_service import IncidentService
from app.services.call_service import call_service
from app.services.console import console
from app.services.persistence_service import persistence_service
from app.rules.rule_loader import rule_loader
from dotenv import load_dotenv


class ActionDispatcher:

    def __init__(self):

        self.incident_service = IncidentService()
        self.call_service = call_service

        self.ACTION_MAP = {
            "email": self._action_email,
            "telegram": self._action_telegram,
            "calls": self._action_calls,
            "jira": self._action_jira,
            "teams": self._action_teams,
        }

        load_dotenv()

        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN_NOC")
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")

    def _normalize_status(self, status):

        return {
            "1": "PROBLEM",
            "0": "RECOVERY"
        }.get(str(status), str(status))

    def _normalize_phone_number(self, phone):

        if isinstance(phone, float) and phone.is_integer():
            phone = int(phone)

        phone = str(phone).strip()

        if phone.endswith(".0"):
            phone = phone[:-2]

        phone = phone.replace(" ", "").replace("-", "")

        return phone.replace("+", "")

    def normalize_email_recipients(self, values):

        recipients = []
        seen = set()

        for value in values or []:

            if not value or value != value:

                continue

            for recipient in re.split(r"[,;|]", str(value)):
                normalized = recipient.strip().lower()

                if normalized and normalized not in seen:
                    recipients.append(normalized)
                    seen.add(normalized)

        return recipients

    def _event_context(self, event):

        client = getattr(event, "client", None)
        host = getattr(event, "parsed_host", None)

        if not client or not host:
            client, host = rule_loader.extract_client_and_host(event.host)

        return client, host, getattr(event, "trigger_group", None)

    def _record_action(self, event, action_type, target, status, response=None, error_message=None):

        client, host, trigger_group = self._event_context(event)

        persistence_service.record_action(
            event=event,
            action_type=action_type,
            target=target,
            status=status,
            response=response,
            error_message=error_message,
            client=client,
            host=host,
            trigger_group=trigger_group,
        )

        persistence_service.record_audit_log(
            event_id=event.event_id,
            level={
                "success": "INFO",
                "skipped": "WARNING",
                "failed": "ERROR",
            }.get(status, "INFO"),
            component="dispatcher",
            message=f"Action {action_type} {status}",
            details={
                "action_type": action_type,
                "target": target,
                "status": status,
                "error_message": error_message,
            },
        )

    def dispatch(self, event, actions: list, contacts: list):

        print(f"\n[{console.cyan('DISPATCHER')}] Starting action dispatch...")
        print(
            f"[{console.cyan('EVENT')}] {event.event_id} | "
            f"{console.status(event.status)} | "
            f"{event.host}"
        )

        results = []

        for action in actions:

            handler = self.ACTION_MAP.get(action)

            if not handler:
                print(f"[{console.level('WARNING')}] Unknown action type: {action}")
                results.append({
                    "action": action,
                    "success": False,
                    "error": "Unknown action type",
                })
                continue

            try:
                action_results = self._dispatch_single_action(
                    handler,
                    action,
                    event,
                    contacts
                )
                results.extend(action_results)

            except Exception as e:
                print(
                    f"[{console.level('ERROR')}] Failed executing action "
                    f"'{action}': {e}"
                )
                self._record_action(
                    event=event,
                    action_type=action,
                    target=None,
                    status="failed",
                    error_message=str(e),
                )
                results.append({
                    "action": action,
                    "success": False,
                    "error": str(e),
                })

        return {
            "success": all(result["success"] for result in results) if results else True,
            "results": results,
        }

    def _dispatch_single_action(self, handler, action, event, contacts):

        results = []

        for contact in contacts:
            result = handler(event, contact)

            if isinstance(result, dict):
                result.setdefault("action", action)
                result.setdefault("success", False)
                result.setdefault("contact", contact)
                results.append(result)
                continue

            results.append({
                "action": action,
                "success": bool(result),
                "contact": contact,
            })

        return results

    def _send_email_message(self, recipients, subject, body):

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = ", ".join(recipients)

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:

            server.starttls()
            server.login(self.smtp_user, self.smtp_password)

            server.sendmail(
                self.smtp_user,
                recipients,
                msg.as_string()
            )

    def send_email_summary(self, event, recipients, action_results):

        recipients = self.normalize_email_recipients(recipients)

        if not recipients:
            print("[EMAIL] No se envía resumen: no hay destinatarios disponibles")
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="INFO",
                component="dispatcher",
                message="Email summary skipped because no recipients are available",
                details={"event_id": event.event_id},
            )
            return {
                "action": "email_summary",
                "success": True,
                "sent": False,
                "recipients": [],
            }

        subject = f"[NOC RESUMEN] {event.host} - PROBLEM"
        body = self._build_email_summary_body(event, action_results)

        try:
            self._send_email_message(recipients, subject, body)

        except Exception as e:
            print(f"[{console.level('ERROR')}] Error SMTP / Email summary failed: {e}")
            self._record_action(
                event,
                "email_summary",
                recipients,
                "failed",
                error_message=str(e),
            )
            return {
                "action": "email_summary",
                "success": False,
                "sent": False,
                "recipients": recipients,
                "error": str(e),
            }

        print(f"[EMAIL] {console.green('Resumen enviado correctamente')} -> {recipients}")
        self._record_action(event, "email_summary", recipients, "success")
        return {
            "action": "email_summary",
            "success": True,
            "sent": True,
            "recipients": recipients,
        }

    def _build_email_summary_body(self, event, action_results):

        client, host, trigger_group = self._event_context(event)
        lines = [
            "Resumen operativo de alerta NOC",
            "",
            f"Cliente: {client}",
            f"Host: {host}",
            f"Trigger: {event.trigger}",
            f"Severidad: {event.severity}",
            "Estado: PROBLEM",
            f"Event ID: {event.event_id}",
        ]

        if getattr(event, "timestamp", None):
            lines.append(f"Fecha/hora evento: {event.timestamp}")

        if trigger_group:
            lines.append(f"Grupo de trigger: {trigger_group}")

        lines.extend(["", "Acciones realizadas:"])
        added_action = False

        for result in action_results or []:

            if not result.get("success"):

                continue

            action = result.get("action")

            if action == "jira" and result.get("issue_key"):
                line = f"- Ticket Jira creado: {result.get('issue_key')}"

                if result.get("project_key"):
                    line += f" | Proyecto: {result.get('project_key')}"

                if result.get("url"):
                    line += f" | URL: {result.get('url')}"

                lines.append(line)
                added_action = True

            elif action == "calls":
                lines.append(
                    "- Llamada realizada: "
                    f"telefono={result.get('phone')} | "
                    f"intentos={result.get('attempt_count', 1)} | "
                    f"estado={result.get('status') or 'desconocido'} | "
                    f"confirmada={'si' if result.get('confirmed') else 'no'}"
                )

                if result.get("confirmed_at"):
                    lines.append(f"  Confirmada en: {result.get('confirmed_at')}")

                if result.get("answered_at"):
                    lines.append(f"  Atendida en: {result.get('answered_at')}")

                if result.get("call_uuid"):
                    lines.append(f"  Call UUID: {result.get('call_uuid')}")

                added_action = True

            elif action == "telegram":
                lines.append("- Telegram enviado correctamente")
                added_action = True

            elif action == "teams":
                lines.append("- Teams enviado correctamente")
                added_action = True

        if not added_action:
            lines.append("- No se registraron acciones operativas exitosas para informar.")

        return "\n".join(lines)

    # ========================
    # ACTION HANDLERS
    # ========================

    def _action_email(self, event, contact):

        if isinstance(contact, str):
            recipient = contact
        else:
            recipient = contact.get("email")

        if not recipient:
            print(f"[{console.level('WARNING')}] No email defined for contact")
            self._record_action(event, "email", contact, "skipped", error_message="No email defined for contact")
            return {"action": "email", "success": False, "status": "skipped"}

        recipients = self.normalize_email_recipients([recipient])

        if not recipients:
            print(f"[{console.level('WARNING')}] No valid email recipients defined")
            self._record_action(event, "email", recipient, "skipped", error_message="No valid email recipients defined")
            return {"action": "email", "success": False, "status": "skipped"}

        status = self._normalize_status(event.status)

        subject = f"[NOC ALERT] {event.host} - {status}"

        body = (
            f"Host: {event.host}\n"
            f"Trigger: {event.trigger}\n"
            f"Severity: {event.severity}\n"
            f"Status: {status}\n"
            f"Event ID: {event.event_id}"
        )

        if getattr(event, "unmanaged_host", False):

            body += (
                "\n\n"
                "Este host no se encuentra registrado en el runbook del cliente.\n"
                "Si corresponde su monitoreo, por favor solicitar su incorporación.\n"
                "Ante dudas o consultas comunicarse con el equipo NOC."
            )

        try:
            self._send_email_message(recipients, subject, body)

        except Exception as e:

            print(f"[{console.level('ERROR')}] Error SMTP / Email send failed: {e}")
            self._record_action(event, "email", recipient, "failed", error_message=str(e))
            return {"action": "email", "success": False, "status": "failed"}

        print(f"[DISPATCH][EMAIL] {console.green('enviado correctamente')} -> {recipients}")
        self._record_action(event, "email", recipients, "success")
        return {
            "action": "email",
            "success": True,
            "status": "sent",
            "recipients": recipients,
        }

    def _action_telegram(self, event, contact):

        chat_id = contact.get("telegram")

        if not chat_id:
            print(f"[{console.level('WARNING')}] No telegram defined for contact")
            self._record_action(event, "telegram", contact, "skipped", error_message="No telegram defined for contact")
            return {"action": "telegram", "success": False, "status": "skipped"}

        status = self._normalize_status(event.status)

        message = (
            f"🚨 ALERTA NOC\n"
            f"Host: {event.host}\n"
            f"Trigger: {event.trigger}\n"
            f"Severity: {event.severity}\n"
            f"Status: {status}"
        )

        if not self.telegram_bot_token:
            print(f"[{console.level('WARNING')}] No TELEGRAM_BOT_TOKEN_NOC defined")
            self._record_action(event, "telegram", chat_id, "skipped", error_message="No TELEGRAM_BOT_TOKEN_NOC defined")
            return {"action": "telegram", "success": False, "status": "skipped"}

        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"

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

            print(f"[{console.level('ERROR')}] Telegram connection error: {e}")
            self._record_action(event, "telegram", chat_id, "failed", error_message=str(e))
            return {"action": "telegram", "success": False, "status": "failed"}

        if response.status_code != 200:
            print(f"[{console.level('ERROR')}] Telegram send failed: {response.text}")
            self._record_action(
                event,
                "telegram",
                chat_id,
                "failed",
                response={"http_status": response.status_code, "body": response.text},
                error_message=response.text,
            )
            return {"action": "telegram", "success": False, "status": "failed"}

        print(f"[DISPATCH][TELEGRAM] {console.green('enviado correctamente')} -> {chat_id}")
        self._record_action(event, "telegram", chat_id, "success", response={"http_status": response.status_code})
        return {
            "action": "telegram",
            "success": True,
            "status": "sent",
            "target": chat_id,
        }

    def _action_calls(self, event, contact):

        phone = contact.get("phone")

        if not phone or phone != phone:
            print(f"[{console.level('WARNING')}] No phone defined for contact")
            self._record_action(event, "calls", contact, "skipped", error_message="No phone defined for contact")
            return {"action": "calls", "success": False, "status": "skipped"}

        phone = self._normalize_phone_number(phone)

        print(
            f"[DISPATCH][CALL] "
            f"{console.cyan('Iniciando llamada Vonage')} | phone={phone}"
        )

        try:
            result = self.call_service.notify_event_by_call(event, phone)

        except Exception as e:
            print(f"[{console.level('ERROR')}] Vonage call failed: {e}")
            self._record_action(event, "calls", phone, "failed", error_message=str(e))
            return {"action": "calls", "success": False, "status": "failed"}

        resolved = self.call_service.wait_for_resolution(event.event_id)
        call_status = (resolved or {}).get("status") or result.get("status")
        confirmed = bool((resolved or {}).get("confirmed"))

        print(
            f"[DISPATCH][CALL] {console.cyan('Vonage call created')} -> "
            f"phone={phone} | "
            f"uuid={result.get('uuid')} | "
            f"status={call_status} | "
            f"confirmed={confirmed}"
        )
        response = {
            **result,
            "resolution": resolved,
        }
        self._record_action(event, "calls", phone, "success", response=response)
        return {
            "action": "calls",
            "success": True,
            "attempt_count": (resolved or {}).get("attempt_count", 1),
            "phone": phone,
            "call_uuid": (resolved or {}).get("uuid") or result.get("uuid"),
            "status": call_status,
            "confirmed": confirmed,
            "confirmed_at": (resolved or {}).get("confirmed_at"),
            "answered_at": (resolved or {}).get("answered_at"),
            "final_reason": (resolved or {}).get("final_reason"),
        }

    def _action_jira(self, event, contact):

        project_key = contact.get("jira_project")

        if not project_key:
            print(f"[{console.level('WARNING')}] No jira_project defined")
            self._record_action(event, "jira", contact, "skipped", error_message="No jira_project defined")
            return {"action": "jira", "success": False, "status": "skipped"}

        client, host = rule_loader.extract_client_and_host(event.host)

        status = "PROBLEM" if str(event.status) == "1" else "RECOVERY"

        jira_priority = contact.get("jira_priority")

        if not jira_priority:
            jira_priority = rule_loader.get_jira_priority(
                client,
                event.severity
            )

        console.log(
            "DEBUG",
            f"[{console.level('DEBUG')}] Creating Jira ticket in project: {project_key}",
        )
        console.log(
            "DEBUG",
            f"[{console.level('DEBUG')}] Jira priority resolved: {jira_priority}",
        )

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

        issue_type = contact.get("jira_issue_type")
        request_type = contact.get("jira_request_type")

        # limpiar NaN provenientes de pandas
        if issue_type != issue_type:
            issue_type = None

        if request_type != request_type:
            request_type = None

        print(
            f"[DISPATCH][JIRA] "
            f"{console.cyan('Creando ticket')} | project={project_key}"
        )

        response = self.incident_service.create_incident(
            project_key=project_key,
            summary=summary,
            description=description,
            priority=jira_priority,
            issue_type=issue_type,
            request_type=request_type
        )

        if response.get("success"):
            print(
                f"[DISPATCH][JIRA] "
                f"{console.green('Ticket creado correctamente')}: "
                f"{response.get('issue_key')}"
            )
            self._record_action(event, "jira", project_key, "success", response=response)
            jira_url = None

            if self.incident_service.jira_service.base_url:
                jira_url = (
                    f"{self.incident_service.jira_service.base_url.rstrip('/')}"
                    f"/browse/{response.get('issue_key')}"
                )

            return {
                "action": "jira",
                "success": True,
                "status": response.get("status"),
                "issue_key": response.get("issue_key"),
                "project_key": project_key,
                "url": jira_url,
            }

        print(
            f"[{console.level('ERROR')}] Error Jira / ticket creation failed | "
            f"status={response.get('status')} | "
            f"error={response.get('error')}"
        )
        self._record_action(
            event,
            "jira",
            project_key,
            "failed",
            response=response,
            error_message=response.get("error"),
        )
        return {"action": "jira", "success": False, "status": "failed"}

    def _action_teams(self, event, contact):

        teams_destination = contact.get("teams")

        if not teams_destination:
            print(f"[{console.level('WARNING')}] No teams destination defined")
            self._record_action(event, "teams", contact, "skipped", error_message="No teams destination defined")
            return {"action": "teams", "success": False, "status": "skipped"}

        print(f"[DISPATCH][TEAMS->EMAIL] {console.cyan('enviando')} -> {teams_destination}")

        status = self._normalize_status(event.status)
        subject = f"[NOC ALERT][TEAMS] {event.host} - {status}"
        body = (
            f"Host: {event.host}\n"
            f"Trigger: {event.trigger}\n"
            f"Severity: {event.severity}\n"
            f"Status: {status}\n"
            f"Event ID: {event.event_id}"
        )
        recipients = self.normalize_email_recipients([teams_destination])

        if not recipients:
            print(f"[{console.level('WARNING')}] No valid teams destination defined")
            self._record_action(event, "teams", teams_destination, "skipped", error_message="No valid teams destination defined")
            return {"action": "teams", "success": False, "status": "skipped"}

        try:
            self._send_email_message(recipients, subject, body)

        except Exception as e:
            print(f"[{console.level('ERROR')}] Teams email transport failed: {e}")
            self._record_action(event, "teams", teams_destination, "failed", error_message=str(e))
            return {"action": "teams", "success": False, "status": "failed"}

        if recipients:
            self._record_action(event, "teams", teams_destination, "success")
            return {
                "action": "teams",
                "success": True,
                "status": "sent",
                "target": teams_destination,
            }

        self._record_action(event, "teams", teams_destination, "failed", error_message="Teams email transport failed")
        return {"action": "teams", "success": False, "status": "failed"}
