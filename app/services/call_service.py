from app.integrations.vonage_voice import VonageVoiceClient


class CallService:

    def __init__(self, voice_client=None):
        self.voice_client = voice_client
        self.active_events = {}

    def notify_event_by_call(self, event, phone):
        if not event.event_id:
            raise ValueError("Cannot create call for event without event_id")

        self.active_events[event.event_id] = event

        voice_client = self.voice_client or VonageVoiceClient()

        result = voice_client.create_call(
            phone=phone,
            event_id=event.event_id
        )
        result["phone"] = phone

        return result

    def get_message(self, event_id):
        event = self.active_events.get(event_id)

        if not event:
            return "Alerta del NOC no encontrada."

        return self.build_message(event)

    def build_message(self, event):
        client, host = self._extract_client_and_host(event.host)

        return (
            "Alerta crítica del NOC. "
            f"Cliente {client}. "
            f"Host {host}. "
            f"Trigger {event.trigger}. "
            f"Severidad {event.severity}. "
            f"Estado {event.status}."
        )

    def _extract_client_and_host(self, full_host):
        host_value = str(full_host or "unknown")

        if "/" not in host_value:
            return "unknown", host_value

        client, host = host_value.split("/", 1)

        return client.strip() or "unknown", host.strip() or host_value


call_service = CallService()
