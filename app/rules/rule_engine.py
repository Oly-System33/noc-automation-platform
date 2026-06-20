from datetime import datetime, timedelta, timezone

from app.rules.rule_loader import rule_loader
from app.services.action_dispatcher import ActionDispatcher
from app.services.persistence_service import persistence_service


class RuleEngine:

    def __init__(self):
        self.dispatcher = ActionDispatcher()
        self.processed_events = set()

    def evaluate_problem(self, event):

        if event.event_id in self.processed_events:
            print(f"[RULE_ENGINE] Event {event.event_id} already processed")
            return

        self.processed_events.add(event.event_id)

        # 1) separar cliente y host
        client, host = rule_loader.extract_client_and_host(event.host)
        event.client = client
        event.parsed_host = host

        print(f"[RULE_ENGINE] Cliente: {client} | Host: {host}")
        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="INFO",
            component="rule_engine",
            message="Client and host detected",
            details={"client": client, "host": host},
        )

        try:
            self._evaluate_problem_with_runbook(event, client, host)
        except FileNotFoundError:
            event.unprocessable_event = True
            print(f"[WARNING] Runbook not found for client: {client}")
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="WARNING",
                component="rule_engine",
                message=f"Runbook not found for client: {client}",
                details={"client": client, "host": host},
            )

    def _evaluate_problem_with_runbook(self, event, client, host):

        # 2) verificar host monitoreado
        if not rule_loader.is_host_monitored(client, host):

            print("[INFO] Host no monitoreado")
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="INFO",
                component="rule_engine",
                message="Host not monitored",
                details={"client": client, "host": host},
            )

            event.unmanaged_host = True

            baseline_contact = rule_loader.get_contact(client, "baseline")

            if baseline_contact and baseline_contact.get("email"):

                self.dispatcher.dispatch(
                    event=event,
                    actions=["email"],
                    contacts=[baseline_contact.get("email")]
                )

            else:

                print("[WARNING] No baseline contact definido")

            return

        # 3) clasificar trigger
        trigger_group = rule_loader.get_trigger_group(
            client,
            event.trigger
        )

        print(f"[INFO] Trigger group detectado: {trigger_group}")
        event.trigger_group = trigger_group
        persistence_service.update_event_context(
            event_id=event.event_id,
            client=client,
            host=host,
            trigger_group=trigger_group,
        )
        persistence_service.open_incident(
            event=event,
            client=client,
            host=host,
            trigger_group=trigger_group,
        )
        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="INFO",
            component="rule_engine",
            message="Trigger group detected",
            details={"trigger_group": trigger_group},
        )

        # 4) verificar suppressions
        if rule_loader.is_suppressed(client, host, trigger_group):

            print("[INFO] Evento suprimido por regla horaria")
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="INFO",
                component="rule_engine",
                message="Event suppressed by schedule rule",
                details={"trigger_group": trigger_group},
            )

            return

        # 5) buscar acción adicional
        action = rule_loader.get_action(
            client,
            host,
            trigger_group
        )

        if not action:

            print("[INFO] No hay acción adicional definida")
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="INFO",
                component="rule_engine",
                message="No additional action defined",
                details={"trigger_group": trigger_group},
            )

            baseline_contact = rule_loader.get_contact(client, "baseline")

            if baseline_contact and baseline_contact.get("email"):

                self.dispatcher.dispatch(
                    event=event,
                    actions=["email"],
                    contacts=[baseline_contact.get("email")]
                )

            else:

                print("[WARNING] No baseline contact definido")

            return

        team = action["target"]
        delay_minutes = action.get("delay_minutes", 0)

        if action.get("delay_minutes_invalid"):
            print("[WARNING] Invalid delay_minutes, using 0")
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="WARNING",
                component="rule_engine",
                message="Invalid delay_minutes, using 0",
                details={"value": action.get("delay_minutes_raw")},
            )

        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="INFO",
            component="rule_engine",
            message="Action found",
            details={
                "actions": action.get("action"),
                "target": team,
                "trigger_group": trigger_group,
                "delay_minutes": delay_minutes,
            },
        )

        baseline_contact = rule_loader.get_contact(client, "baseline")

        target_contact = rule_loader.get_oncall_contact(client, team)

        if not target_contact:
            target_contact = rule_loader.get_contact(client, team)

        # inyectar jira_project, jira_issue_type, jira_request_type desde hoja actions
        if target_contact:

            if "jira" in action.get("action", []):
                target_contact["jira_priority"] = rule_loader.get_jira_priority(
                    client,
                    event.severity,
                )

            if "jira_project" in action:
                target_contact["jira_project"] = action["jira_project"]

            if "jira_issue_type" in action:
                target_contact["jira_issue_type"] = action["jira_issue_type"]

            if "jira_request_type" in action:
                target_contact["jira_request_type"] = action["jira_request_type"]

        action_plan = self._build_action_plan(
            event=event,
            client=client,
            host=host,
            trigger_group=trigger_group,
            action=action,
            target=team,
            baseline_contact=baseline_contact,
            target_contact=target_contact,
            delay_minutes=delay_minutes,
        )

        if delay_minutes > 0:
            self._schedule_action_plan(action_plan)
            return

        self._execute_action_plan(action_plan)

    def _build_action_plan(self, event, client, host, trigger_group, action, target, baseline_contact, target_contact, delay_minutes):

        email_recipients = []

        baseline_email = baseline_contact.get(
            "email") if baseline_contact else None
        target_email = target_contact.get("email") if target_contact else None

        # limpiar NaN provenientes de pandas
        if baseline_email and baseline_email == baseline_email:
            email_recipients.append(str(baseline_email))

        if target_email and target_email == target_email:
            email_recipients.append(str(target_email))

        merged_recipients = ";".join(email_recipients) if email_recipients else None
        other_actions = [
            a for a in action["action"]
            if a != "email"
        ]

        return {
            "event": event,
            "client": client,
            "host": host,
            "trigger_group": trigger_group,
            "actions": action["action"],
            "target": target,
            "contacts": {
                "baseline_contact": baseline_contact,
                "target_contact": target_contact,
                "email_recipients": email_recipients,
                "merged_email_recipients": merged_recipients,
                "other_actions": other_actions,
            },
            "delay_minutes": delay_minutes,
        }

    def _execute_action_plan(self, action_plan):

        event = action_plan["event"]
        contacts = action_plan["contacts"]
        merged_recipients = contacts["merged_email_recipients"]
        other_actions = contacts["other_actions"]
        target_contact = contacts["target_contact"]

        # dispatch EMAIL consolidado
        if merged_recipients:

            self.dispatcher.dispatch(
                event=event,
                actions=["email"],
                contacts=[merged_recipients]
            )

        # ejecutar otras acciones no-email normalmente
        if other_actions and target_contact:

            self.dispatcher.dispatch(
                event=event,
                actions=other_actions,
                contacts=[target_contact]
            )

    def _schedule_action_plan(self, action_plan):

        event = action_plan["event"]
        delay_minutes = action_plan["delay_minutes"]
        scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
        contacts = action_plan["contacts"]

        contacts_payload = {
            "baseline_contact": contacts["baseline_contact"],
            "target_contact": contacts["target_contact"],
            "email_recipients": contacts["email_recipients"],
            "merged_email_recipients": contacts["merged_email_recipients"],
            "dispatch_contacts": {
                "email": [contacts["merged_email_recipients"]]
                if contacts["merged_email_recipients"] else [],
                "other": [contacts["target_contact"]]
                if contacts["target_contact"] else [],
            },
            "worker_note": "Plan is pre-resolved; worker should not need to reload Excel.",
        }

        result = persistence_service.create_scheduled_action(
            event=event,
            client=action_plan["client"],
            host=action_plan["host"],
            trigger_group=action_plan["trigger_group"],
            actions=action_plan["actions"],
            target=action_plan["target"],
            contacts_payload=contacts_payload,
            scheduled_at=scheduled_at,
        )

        if result.get("success"):
            print(
                "[RULE_ENGINE] Action scheduled | "
                f"event_id={event.event_id} | "
                f"delay_minutes={delay_minutes} | "
                f"scheduled_at={result.get('scheduled_at')}"
            )
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="INFO",
                component="rule_engine",
                message="Action scheduled",
                details={
                    "event_id": event.event_id,
                    "delay_minutes": delay_minutes,
                    "scheduled_at": result.get("scheduled_at"),
                    "actions": action_plan["actions"],
                    "target": action_plan["target"],
                    "scheduled_action_id": result.get("scheduled_action_id"),
                },
            )
            return

        print(
            "[ERROR] Failed to schedule action | "
            f"event_id={event.event_id} | "
            f"error={result.get('error')}"
        )
        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="ERROR",
            component="database",
            message="Failed to schedule action",
            details={
                "event_id": event.event_id,
                "error": result.get("error"),
            },
        )

    def close_incident(self, event, duration):

        client, host = rule_loader.extract_client_and_host(event.host)
        event.client = client
        event.parsed_host = host

        print(
            f"[RULE_ENGINE] Incidente cerrado: {host} "
            f"(duración: {duration})"
        )
        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="INFO",
            component="rule_engine",
            message="Incident closed",
            details={"client": client, "host": host, "duration": duration},
        )


rule_engine = RuleEngine()
