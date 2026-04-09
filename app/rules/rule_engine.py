from app.rules.rule_loader import rule_loader
from app.services.action_dispatcher import ActionDispatcher


class RuleEngine:

    def __init__(self):
        self.dispatcher = ActionDispatcher()
        self.processed_events = set()

    def evaluate_problem(self, event):

        already_processed = event.event_id in self.processed_events

        if already_processed:
            print(
                f"[RULE_ENGINE] Event {event.event_id} already processed "
                "(dispatch skipped)"
            )
        else:
            self.processed_events.add(event.event_id)

        # =============================
        # 1) separar cliente y host
        # =============================

        try:
            client, host = rule_loader.extract_client_and_host(event.host)

        except Exception:

            print(
                f"[RULE_ENGINE] No se pudo parsear cliente/host: {event.host}"
            )

            return None

        print(f"[RULE_ENGINE] Cliente: {client} | Host: {host}")

        # =============================
        # 2) verificar existencia runbook
        # =============================

        try:

            if not rule_loader.is_host_monitored(client, host):

                print(
                    f"[RULE_ENGINE] Host no monitoreado en runbook: {host}"
                )

                return None

        except FileNotFoundError:

            print(
                f"[RULE_ENGINE] Runbook inexistente para cliente: {client}"
            )

            return None

        # =============================
        # 3) clasificar trigger
        # =============================

        trigger_group = rule_loader.get_trigger_group(
            client,
            event.trigger
        )

        if not trigger_group:

            print(
                "[RULE_ENGINE] Trigger group no identificado"
            )

            return None

        print(
            f"[RULE_ENGINE] Trigger group detectado: {trigger_group}"
        )

        # =============================
        # 4) verificar suppressions
        # =============================

        if rule_loader.is_suppressed(
            client,
            host,
            trigger_group
        ):

            print(
                "[RULE_ENGINE] Evento suprimido por regla horaria"
            )

            return None

        # =============================
        # 5) buscar acción definida
        # =============================

        action = rule_loader.get_action(
            client,
            host,
            trigger_group
        )

        if not action:

            print(
                "[RULE_ENGINE] No hay acción definida en runbook"
            )

            return None

        team = action.get("target")

        if not team:

            print(
                "[RULE_ENGINE] Acción sin equipo destino"
            )

            return None

        # =============================
        # 6) buscar contacto
        # =============================

        contact = rule_loader.get_contact(
            client,
            team
        )

        if not contact:

            print(
                f"[RULE_ENGINE] No se encontró contacto para equipo: {team}"
            )

            return None

        # =============================
        # 7) ejecutar dispatch (solo 1 vez)
        # =============================

        if not already_processed:

            self.dispatcher.dispatch(
                event=event,
                actions=action.get("action", []),
                contacts=[contact]
            )

        # =============================
        # 8) devolver mensaje PIRU
        # =============================

        mensaje = action.get("mensaje")

        if not mensaje:

            print(
                "[RULE_ENGINE] Acción sin mensaje operativo → solo ACK"
            )

            return None

        print(
            f"[RULE_ENGINE] Mensaje operativo generado para evento {event.event_id}"
        )

        return mensaje

    def close_incident(self, event, duration):

        try:

            client, host = rule_loader.extract_client_and_host(
                event.host
            )

            print(
                f"[RULE_ENGINE] Incidente cerrado: {host} "
                f"(duración: {duration})"
            )

        except Exception:

            print(
                "[RULE_ENGINE] No se pudo registrar cierre de incidente"
            )


rule_engine = RuleEngine()
