from typing import Dict, Optional
from app.models.event_model import ZabbixEvent
from app.rules.rule_loader import rule_loader
from app.services.persistence_service import persistence_service


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

        client, host = rule_loader.extract_client_and_host(event.host)
        event.client = client
        event.parsed_host = host

        persistence_service.record_event(
            event=event,
            client=client,
            host=host,
            raw_payload=getattr(event, "raw_payload", None),
        )

        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="INFO",
            component="event_processor",
            message="Event received",
            details={
                "client": client,
                "host": host,
                "status": event.status,
            },
        )

        if event.event_id is None:
            print("[WARNING] Evento sin event_id, ignorado")
            persistence_service.record_audit_log(
                event_id=None,
                level="WARNING",
                component="event_processor",
                message="Event without event_id ignored",
                details={"host": event.host, "status": event.status},
            )
            return None

        if event.timestamp is None:
            print("[WARNING] Evento sin timestamp, ignorado")
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="WARNING",
                component="event_processor",
                message="Event without timestamp ignored",
                details={"host": event.host, "status": event.status},
            )
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

        persistence_service.open_incident(
            event=event,
            client=getattr(event, "client", None),
            host=getattr(event, "parsed_host", None),
        )

        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="INFO",
            component="event_processor",
            message="Problem event registered",
            details={
                "client": getattr(event, "client", None),
                "host": getattr(event, "parsed_host", None),
            },
        )

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

        incident_closed = persistence_service.close_incident(
            event=event,
            client=getattr(event, "client", None),
            host=getattr(event, "parsed_host", None),
            duration=event.duration or "unknown",
        )

        cancelled_actions = persistence_service.cancel_pending_scheduled_actions(
            event.event_id,
            reason="recovery_received",
        )

        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="INFO" if cancelled_actions.get("success") else "ERROR",
            component="event_processor",
            message="Pending scheduled actions cancelled due to recovery",
            details={
                "event_id": event.event_id,
                "count": cancelled_actions.get("count"),
                "error": cancelled_actions.get("error"),
            },
        )

        if not problem_event:
            print(f"[WARNING] RECOVERY sin PROBLEM previo: {event.event_id}")
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="WARNING",
                component="event_processor",
                message="Recovery without previous problem",
                details={"incident_closed": incident_closed},
            )
            return None

        duration = event.duration or "unknown"

        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="INFO",
            component="event_processor",
            message="Recovery event processed",
            details={"duration": duration, "incident_closed": incident_closed},
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


# instancia global compartida entre requests
processor = EventProcessor()
