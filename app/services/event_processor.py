from typing import Dict, Optional
from datetime import timedelta
from app.models.event_model import ZabbixEvent


class EventProcessor:
    """
    Correlaciona eventos PROBLEM y RECOVERY usando event_id.
    Mantiene estado en memoria de incidentes activos.
    Devuelve información estructurada para el RuleEngine.
    """

    def __init__(self):
        # event_id -> ZabbixEvent
        self.active_events: Dict[str, ZabbixEvent] = {}

    def process(self, event: ZabbixEvent) -> Optional[dict]:

        if event.event_id is None:
            print("[WARNING] Evento sin event_id, ignorado")
            return None

        if event.timestamp is None:
            print("[WARNING] Evento sin timestamp, ignorado")
            return None

        status = str(event.status)

        if status in ("1", "PROBLEM"):
            return self._handle_problem(event)

        elif status in ("0", "RECOVERY"):
            return self._handle_recovery(event)

        return None

    def _handle_problem(self, event: ZabbixEvent) -> dict:
        """
        Registra incidente activo y devuelve evento listo
        para evaluación del RuleEngine.
        """

        self.active_events[event.event_id] = event

        print(f"[PROBLEM] {event.host} - {event.trigger}")

        return {
            "type": "PROBLEM",
            "event": event,
        }

    def _handle_recovery(self, event: ZabbixEvent) -> Optional[dict]:
        """
        Cierra incidente activo usando duración enviada por Zabbix.
        """

        problem_event = self.active_events.get(event.event_id)

        if not problem_event:
            print(f"[WARNING] RECOVERY sin PROBLEM previo: {event.event_id}")
            return None

        duration = event.duration or "unknown"

        print(
            f"[RECOVERY] {event.host} - duración total: {duration}"
        )

        del self.active_events[event.event_id]

        return {
            "type": "RECOVERY",
            "event": event,
            "duration": duration,
        }


# instancia global compartida entre requests
processor = EventProcessor()
