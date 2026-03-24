from app.rules.rule_loader import rule_loader


class RuleEngine:

    def evaluate_problem(self, event):

        # 1) separar cliente y host
        client, host = rule_loader.extract_client_and_host(event.host)

        print(f"[RULE_ENGINE] Cliente: {client} | Host: {host}")

        # 2) verificar host monitoreado
        if not rule_loader.is_host_monitored(client, host):

            print("[INFO] Host no monitoreado")
            print("[ACTION] Mail enviado al cliente")
            print("[ACTION] Equipo notificado")

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

        # 5) enviar mail baseline (siempre)
        print("[ACTION] Mail enviado al cliente")

        # 6) buscar acción adicional
        action = rule_loader.get_action(
            client,
            host,
            trigger_group
        )

        if not action:

            print("[INFO] No hay acción adicional definida")

            return

        team = action["target"]

        # 7) buscar contacto
        contact = rule_loader.get_contact(client, team)

        if not contact:

            print("[WARNING] No se encontró contacto para el equipo")

            return

        # 8) ejecutar acción (simulada)
        print(f"[ACTION] Ejecutar {action['action']} hacia {team}")
        print(f"[CONTACT INFO] {contact}")

    def close_incident(self, event, duration):

        client, host = rule_loader.extract_client_and_host(event.host)

        print(
            f"[RULE_ENGINE] Incidente cerrado: {host} "
            f"(duración: {duration})"
        )


rule_engine = RuleEngine()
