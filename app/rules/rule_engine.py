from app.rules.rule_loader import rule_loader
from app.services.action_dispatcher import ActionDispatcher


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

        print(f"[RULE_ENGINE] Cliente: {client} | Host: {host}")

        # 2) verificar host monitoreado
        if not rule_loader.is_host_monitored(client, host):

            print("[INFO] Host no monitoreado")

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

        # 4) verificar suppressions
        if rule_loader.is_suppressed(client, host, trigger_group):

            print("[INFO] Evento suprimido por regla horaria")

            return

        # 5) buscar acción adicional
        action = rule_loader.get_action(
            client,
            host,
            trigger_group
        )

        if not action:

            print("[INFO] No hay acción adicional definida")

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

        baseline_contact = rule_loader.get_contact(client, "baseline")

        target_contact = rule_loader.get_contact(client, team)

        # inyectar jira_project, jira_issue_type, jira_request_type desde hoja actions
        if target_contact:

            if "jira_project" in action:
                target_contact["jira_project"] = action["jira_project"]

            if "jira_issue_type" in action:
                target_contact["jira_issue_type"] = action["jira_issue_type"]

            if "jira_request_type" in action:
                target_contact["jira_request_type"] = action["jira_request_type"]

        email_recipients = []

        baseline_email = baseline_contact.get(
            "email") if baseline_contact else None
        target_email = target_contact.get("email") if target_contact else None

        # limpiar NaN provenientes de pandas
        if baseline_email and baseline_email == baseline_email:
            email_recipients.append(str(baseline_email))

        if target_email and target_email == target_email:
            email_recipients.append(str(target_email))

        # dispatch EMAIL consolidado
        if email_recipients:

            merged_recipients = ";".join(email_recipients)

            self.dispatcher.dispatch(
                event=event,
                actions=["email"],
                contacts=[merged_recipients]
            )

        # ejecutar otras acciones no-email normalmente
        other_actions = [
            a for a in action["action"]
            if a != "email"
        ]

        if other_actions and target_contact:

            self.dispatcher.dispatch(
                event=event,
                actions=other_actions,
                contacts=[target_contact]
            )

    def close_incident(self, event, duration):

        client, host = rule_loader.extract_client_and_host(event.host)

        print(
            f"[RULE_ENGINE] Incidente cerrado: {host} "
            f"(duración: {duration})"
        )


rule_engine = RuleEngine()
