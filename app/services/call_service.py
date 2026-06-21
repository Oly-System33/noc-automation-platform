import os
import threading
from datetime import datetime, timezone

from dotenv import load_dotenv

from app.integrations.vonage_voice import VonageVoiceClient
from app.rules.rule_loader import rule_loader


class CallService:

    def __init__(self, voice_client=None):
        self.voice_client = voice_client
        self.active_events = {}
        self.active_calls = {}
        self._lock = threading.Lock()

    def _timeout_seconds(self):

        load_dotenv()

        try:
            timeout = int(os.getenv("CALL_RESOLUTION_TIMEOUT_SECONDS", 90))
        except ValueError:
            return 90

        return timeout if timeout > 0 else 90

    def _now(self):

        return datetime.now(timezone.utc).isoformat()

    def _final_statuses(self):

        return {
            "completed",
            "busy",
            "failed",
            "rejected",
            "timeout",
            "unanswered",
            "cancelled",
        }

    def _create_call_state(self, event, phone):

        return {
            "event_id": event.event_id,
            "phone": phone,
            "attempt_count": 1,
            "uuid": None,
            "status": "created",
            "confirmed": False,
            "confirmed_at": None,
            "answered_at": None,
            "final": False,
            "final_reason": None,
            "created_at": self._now(),
            "updated_at": self._now(),
            "event": threading.Event(),
        }

    def _public_call_state(self, state):

        if not state:

            return None

        return {
            key: value
            for key, value in state.items()
            if key != "event"
        }

    def notify_event_by_call(self, event, phone):
        if not event.event_id:
            raise ValueError("Cannot create call for event without event_id")

        self.active_events[event.event_id] = event

        with self._lock:
            self.active_calls[event.event_id] = self._create_call_state(event, phone)

        voice_client = self.voice_client or VonageVoiceClient()

        result = voice_client.create_call(
            phone=phone,
            event_id=event.event_id
        )
        result["phone"] = phone

        with self._lock:
            state = self.active_calls.get(event.event_id)

            if state:
                state["uuid"] = result.get("uuid")
                state["status"] = result.get("status") or "started"
                state["updated_at"] = self._now()

        return result

    def wait_for_resolution(self, event_id, timeout_seconds=None):

        with self._lock:
            state = self.active_calls.get(event_id)
            event = state.get("event") if state else None

        if not state or not event:

            return None

        event.wait(timeout_seconds or self._timeout_seconds())

        with self._lock:
            state = self.active_calls.get(event_id)

            if state and not state.get("final"):
                state["status"] = state.get("status") or "timeout"
                state["final"] = True
                state["final_reason"] = "resolution_timeout"
                state["updated_at"] = self._now()
                state["event"].set()

            return self._public_call_state(state)

    def mark_confirmed(self, event_id):

        with self._lock:
            state = self.active_calls.get(event_id)

            if not state:

                return None

            state["confirmed"] = True
            state["confirmed_at"] = self._now()
            state["status"] = "confirmed"
            state["final"] = True
            state["final_reason"] = "dtmf_1_confirmed"
            state["updated_at"] = self._now()
            state["event"].set()

            return self._public_call_state(state)

    def update_call_event(self, event_id, payload):

        status = str(payload.get("status") or "").lower()

        with self._lock:
            state = self.active_calls.get(event_id)

            if not state:

                return None

            if payload.get("uuid") and not state.get("uuid"):
                state["uuid"] = payload.get("uuid")

            if status:
                state["status"] = status

            if status == "answered" and not state.get("answered_at"):
                state["answered_at"] = payload.get("timestamp") or self._now()

            if status in self._final_statuses():
                state["final"] = True
                state["final_reason"] = status
                state["event"].set()

            state["updated_at"] = self._now()

            return self._public_call_state(state)

    def get_message(self, event_id):
        event = self.active_events.get(event_id)

        if not event:
            return "Alerta del NOC no encontrada."

        return self.build_message(event)

    def build_message(self, event):
        client, host = rule_loader.extract_client_and_host(event.host)

        return (
            "Alerta crítica del NOC. "
            f"Cliente {client}. "
            f"Host {host}. "
            f"Trigger {event.trigger}. "
            f"Severidad {event.severity}. "
            f"Estado {event.status}."
        )

call_service = CallService()
