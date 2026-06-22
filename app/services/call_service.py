import os
import time
import threading
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from app.integrations.vonage_voice import VonageVoiceClient
from app.services.alert_message_builder import AlertMessageBuilder
from app.services.console import console
from app.services.persistence_service import persistence_service
from app.rules.rule_loader import rule_loader


class CallService:

    def __init__(self, voice_client=None):
        self.voice_client = voice_client
        self.active_events = {}
        self.active_contexts = {}
        self.active_calls = {}
        self._lock = threading.Lock()

    def _timeout_seconds(self):

        load_dotenv()

        try:
            timeout = int(os.getenv("CALL_RESOLUTION_TIMEOUT_SECONDS", 90))
        except ValueError:
            return 90

        return timeout if timeout > 0 else 90

    def _get_int_env(self, name, default):

        load_dotenv()

        try:
            value = int(os.getenv(name, default))
        except ValueError:
            return default

        return value if value > 0 else default

    def max_attempts(self):

        return self._get_int_env("CALL_MAX_ATTEMPTS", 3)

    def retry_interval_seconds(self):

        return self._get_int_env("CALL_RETRY_INTERVAL_SECONDS", 300)

    def confirmation_timeout_seconds(self):

        return self._get_int_env("CALL_CONFIRMATION_TIMEOUT_SECONDS", 120)

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

    def _create_call_state(self, event, phone, attempt_number=1):

        return {
            "event_id": event.event_id,
            "phone": phone,
            "attempt_count": attempt_number,
            "attempt_number": attempt_number,
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

    def notify_event_by_call(self, event, phone, context=None, attempt_number=1):
        if not event.event_id:
            raise ValueError("Cannot create call for event without event_id")

        self.active_events[event.event_id] = event
        self.active_contexts[event.event_id] = context or {}

        with self._lock:
            self.active_calls[event.event_id] = self._create_call_state(event, phone, attempt_number)

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

    def execute_call_flow(self, event, phone, target=None, context=None, previous_results=None):

        client, host = rule_loader.extract_client_and_host(event.host)
        max_attempts = self.max_attempts()
        retry_interval = self.retry_interval_seconds()
        confirmation_timeout = self.confirmation_timeout_seconds()
        flow = persistence_service.create_call_flow(
            event=event,
            client=client,
            host=host,
            target=target,
            phone=phone,
            max_attempts=max_attempts,
            summary_payload={
                "context": context,
                "action_results": previous_results or [],
            },
        )
        print(
            f"[CALL] Flujo iniciado | event_id={event.event_id} | "
            f"max_attempts={max_attempts} | retry_interval={retry_interval}s"
        )

        last_result = None

        for attempt_number in range(1, max_attempts + 1):

            if persistence_service.get_incident_status(event.event_id) != "open":
                persistence_service.cancel_pending_call_flows(event.event_id)
                return self._call_result(event, phone, "cancelled", attempt_number - 1)

            persistence_service.create_call_attempt(
                call_flow_id=flow["id"],
                event_id=event.event_id,
                attempt_number=attempt_number,
                phone=phone,
            )
            print(f"[CALL] Intento {attempt_number} iniciado | event_id={event.event_id} | phone={phone}")

            try:
                result = self.notify_event_by_call(
                    event,
                    phone,
                    context=context,
                    attempt_number=attempt_number,
                )
                last_result = result
                persistence_service.mark_call_attempt_started(
                    event_id=event.event_id,
                    attempt_number=attempt_number,
                    vonage_uuid=result.get("uuid"),
                )

            except Exception as e:
                persistence_service.mark_call_attempt_no_confirmation(event.event_id, attempt_number)
                print(f"[{console.level('ERROR')}] Vonage call failed: {e}")

            resolved = self.wait_for_resolution(event.event_id, timeout_seconds=confirmation_timeout)

            if resolved and resolved.get("confirmed"):
                confirmed_at = resolved.get("confirmed_at")
                print(
                    f"[CALL] Confirmación recibida | event_id={event.event_id} | "
                    f"attempt={attempt_number} | confirmed_at={confirmed_at}"
                )
                print(f"[CALL] Flujo finalizado | event_id={event.event_id} | state=confirmed")
                return self._call_result(
                    event,
                    phone,
                    "confirmed",
                    attempt_number,
                    confirmed=True,
                    confirmed_at=confirmed_at,
                    confirmed_attempt=attempt_number,
                    call_uuid=(resolved or {}).get("uuid") or (last_result or {}).get("uuid"),
                )

            persistence_service.mark_call_attempt_no_confirmation(event.event_id, attempt_number)
            print(f"[CALL] Intento {attempt_number} sin confirmación | event_id={event.event_id}")

            if attempt_number < max_attempts:
                scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=retry_interval)
                persistence_service.schedule_next_call_attempt(event.event_id, scheduled_at)
                print(
                    f"[CALL] Retry programado | event_id={event.event_id} | "
                    f"next_attempt={attempt_number + 1} | scheduled_at={scheduled_at.isoformat()}"
                )
                time.sleep(retry_interval)

        flow = persistence_service.mark_call_flow_manual_required(event.event_id)
        self._print_manual_required_alert(event, max_attempts)
        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="WARNING",
            component="calls",
            message="Call flow requires manual handling",
            details={"attempts": max_attempts, "state": "manual_required"},
        )
        return self._call_result(
            event,
            phone,
            "manual_required",
            max_attempts,
            manual_required=True,
            manual_required_at=(flow or {}).get("manual_required_at"),
            call_uuid=(last_result or {}).get("uuid"),
        )

    def _call_result(self, event, phone, status, attempt_count, confirmed=False, confirmed_at=None, confirmed_attempt=None, manual_required=False, manual_required_at=None, call_uuid=None):

        return {
            "action": "calls",
            "success": True,
            "attempt_count": attempt_count,
            "phone": phone,
            "call_uuid": call_uuid,
            "status": status,
            "confirmed": confirmed,
            "confirmed_at": confirmed_at,
            "confirmed_attempt": confirmed_attempt,
            "manual_required": manual_required,
            "manual_required_at": manual_required_at,
        }

    def _print_manual_required_alert(self, event, attempts):

        client, host = rule_loader.extract_client_and_host(event.host)
        header = "ATENCIÓN NOC | LLAMADAS SIN CONFIRMACIÓN"
        print("=" * 60)
        print(console.red(header))
        print("=" * 60)
        print(f"Evento: {event.event_id}")
        print(f"Cliente: {client}")
        print(f"Host: {host}")
        print(f"Trigger: {event.trigger}")
        print(f"Severidad: {event.severity}")
        print("")
        print(f"Se realizaron {attempts} intentos de llamada.")
        print("No se recibió confirmación DTMF con opción 1.")
        print("")
        print(f"Estado del flujo de llamadas: {console.orange('MANUAL_REQUIRED')}")
        print("El incidente técnico sigue ABIERTO hasta RECOVERY.")
        print("")
        print("Acción sugerida: contactar manualmente a la guardia o escalar.")
        print("=" * 60)

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
                return persistence_service.mark_call_confirmed(event_id, digit="1")

            state["confirmed"] = True
            state["confirmed_at"] = self._now()
            state["status"] = "confirmed"
            state["final"] = True
            state["final_reason"] = "dtmf_1_confirmed"
            state["updated_at"] = self._now()
            state["event"].set()

            persistence_service.mark_call_confirmed(event_id, digit="1")

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

            persistence_service.mark_call_attempt_event(
                event_id=event_id,
                status=status,
                vonage_uuid=payload.get("uuid"),
                answered_at=payload.get("timestamp"),
            )

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

        context = self.active_contexts.get(event_id)

        return self.build_message(event, context)

    def build_message(self, event, context=None):
        client, host = rule_loader.extract_client_and_host(event.host)

        if context:
            speech = AlertMessageBuilder(event, context).call_speech()
            jira = context.get("jira") or {}
            includes_ticket = bool(jira.get("success") and jira.get("issue_key"))
            print(
                "[CALL] Speech generado | "
                f"incluye_ticket={str(includes_ticket).lower()} | "
                f"issue_key={jira.get('issue_key')}"
            )

            return speech

        return (
            "Alerta crítica del NOC. "
            f"Cliente {client}. "
            f"Host {host}. "
            f"Trigger {event.trigger}. "
            f"Severidad {event.severity}. "
            f"Estado {event.status}."
        )

call_service = CallService()
