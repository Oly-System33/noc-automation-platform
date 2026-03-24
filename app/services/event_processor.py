from datetime import datetime, timedelta
from typing import Dict, Optional

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
        """
        Procesa evento entrante desde Zabbix.

        Retorna:
            dict con datos del incidente si requiere acción
            None si no hay acción necesaria
        """

        if not event.event_id:
            print("[WARNING] Evento sin event_id, ignorado")
            return None

        if not event.timestamp:
            print("[WARNING] Evento sin timestamp, ignorado")
            return None

        if event.status == 1:
            return self._handle_problem(event)

        elif event.status == 0:
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
        Cierra incidente activo y calcula duración total.
        """

        problem_event = self.active_events.get(event.event_id)

        if not problem_event:
            print(f"[WARNING] RECOVERY sin PROBLEM previo: {event.event_id}")
            return None

        duration = self._calculate_duration(
            problem_event.timestamp,
            event.timestamp
        )

        print(
            f"[RECOVERY] {event.host} - duración total: {duration}"
        )

        del self.active_events[event.event_id]

        return {
            "type": "RECOVERY",
            "event": event,
            "duration": duration,
        }

    def _calculate_duration(self, start: str, end: str) -> timedelta:
        """
        Calcula duración entre timestamps HH:MM:SS
        Maneja cruce de medianoche automáticamente.
        """

        fmt = "%H:%M:%S"

        start_dt = datetime.strptime(start, fmt)
        end_dt = datetime.strptime(end, fmt)

        if end_dt < start_dt:
            end_dt += timedelta(days=1)

        return end_dt - start_dt


# instancia global compartida entre requests
processor = EventProcessor()
