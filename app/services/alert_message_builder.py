from app.rules.rule_loader import rule_loader


class AlertMessageBuilder:

    def __init__(self, event, context=None):
        self.event = event
        self.context = context or {}
        self.client, self.host = self._event_client_host()

    def _event_client_host(self):

        client = getattr(self.event, "client", None)
        host = getattr(self.event, "parsed_host", None)

        if client and host:

            return client, host

        return rule_loader.extract_client_and_host(self.event.host)

    def _jira(self):

        jira = self.context.get("jira") or {}

        if jira.get("success") and jira.get("issue_key"):

            return jira

        return None

    def _common_lines(self):

        lines = [
            "Alerta crítica NOC",
            "",
            f"Cliente: {self.client}",
            f"Host: {self.host}",
            f"Trigger: {self.event.trigger}",
            f"Severidad: {self.event.severity}",
            "Estado: PROBLEM",
        ]

        if getattr(self.event, "timestamp", None):
            lines.append(f"Fecha/hora evento: {self.event.timestamp}")

        jira = self._jira()

        if jira:
            lines.extend(["", f"Ticket Jira: {jira.get('issue_key')}"])

            if jira.get("project_key"):
                lines.append(f"Proyecto Jira: {jira.get('project_key')}")

            if jira.get("url"):
                lines.append(f"URL: {jira.get('url')}")

        return lines

    def telegram_message(self):

        return "\n".join(self._common_lines())

    def teams_message(self):

        return "\n".join(self._common_lines())

    def call_speech(self):

        parts = [
            "Alerta crítica del NOC.",
            f"Cliente {self.client}.",
            f"Host {self.host}.",
            f"Trigger {self.event.trigger}.",
            f"Severidad {self.event.severity}.",
        ]

        jira = self._jira()

        if jira:
            parts.append(f"Se creó el ticket Jira {jira.get('issue_key')}.")

        return " ".join(parts)

    def email_summary_body(self, action_results):

        lines = [
            "Resumen operativo de alerta NOC",
            "",
            f"Cliente: {self.client}",
            f"Host: {self.host}",
            f"Trigger: {self.event.trigger}",
            f"Severidad: {self.event.severity}",
            "Estado: PROBLEM",
            f"Event ID: {self.event.event_id}",
        ]

        if getattr(self.event, "timestamp", None):
            lines.append(f"Fecha/hora evento: {self.event.timestamp}")

        trigger_group = getattr(self.event, "trigger_group", None)

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
