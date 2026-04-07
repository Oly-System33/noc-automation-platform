from app.rules.rule_loader import rule_loader
from app.services.action_dispatcher import ActionDispatcher


class RuleEngine:

    def __init__(self):
        self.dispatcher = ActionDispatcher()
        self.processed_events = set()

    def evaluate_problem(self, event):

        if event.event_id in self.processed_events:
            print(f"[RULE_ENGINE] Event {event.event_id} already processed")
            return None

        self.processed_events.add(event.event_id)

        # 1) separar cliente y host
        client, host = rule_loader.extract_client_and_host(event.host)

        print(f"[RULE_ENGINE] Cliente: {client} | Host: {host}")

        # 2) verificar host monitoreado
        if not rule_loader.is_host_monitored(client, host):

            print("[INFO] Host no monitoreado")

            self.dispatcher.dispatch(
                event=event,
                actions=["email"],
                contacts=["cliente_default@empresa.com"]
            )

            return None

        # 3) clasificar trigger
        trigger_group = rule_loader.get_trigger_group(
            client,
            event.trigger
        )

        print(f"[INFO] Trigger group detectado: {trigger_group}")

        # 4) verificar suppressions
        if rule_loader.is_suppressed(client, host, trigger_group):

            print("[INFO] Evento suprimido por regla horaria")

            return None

        # 5) enviar mail baseline
        self.dispatcher.dispatch(
            event=event,
            actions=["email"],
            contacts=["cliente_default@empresa.com"]
        )

        # 6) buscar acción adicional
        action = rule_loader.get_action(
            client,
            host,
            trigger_group
        )

        if not action:

            print("[INFO] No hay acción adicional definida")

            return None

        team = action["target"]

        # 7) buscar contacto
        contact = rule_loader.get_contact(client, team)

        if not contact:

            print("[WARNING] No se encontró contacto para el equipo")

            return None

        # 8) ejecutar acción adicional
        self.dispatcher.dispatch(
            event=event,
            actions=action["action"],
            contacts=[contact]
        )

        # 9) devolver mensaje operativo para PIRU
        return action.get("mensaje")

    def close_incident(self, event, duration):

        client, host = rule_loader.extract_client_and_host(event.host)

        print(
            f"[RULE_ENGINE] Incidente cerrado: {host} "
            f"(duración: {duration})"
        )


rule_engine = RuleEngine()
