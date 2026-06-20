import os
import threading
import time

from dotenv import load_dotenv

from app.models.event_model import ZabbixEvent
from app.services.action_dispatcher import ActionDispatcher
from app.services.persistence_service import persistence_service


load_dotenv()


class ScheduledActionWorker:

    def __init__(self, dispatcher=None):
        self.dispatcher = dispatcher or ActionDispatcher()
        self.poll_interval = self._get_int_env(
            "SCHEDULED_ACTION_POLL_INTERVAL_SECONDS",
            30,
        )
        self.batch_size = self._get_int_env(
            "SCHEDULED_ACTION_BATCH_SIZE",
            20,
        )
        self._stop_event = threading.Event()

    def _get_int_env(self, name, default):

        try:
            value = int(os.getenv(name, default))
        except ValueError:
            return default

        return value if value > 0 else default

    def stop(self):
        self._stop_event.set()

    def run_forever(self):

        print(
            "[SCHEDULED_WORKER] Started | "
            f"poll_interval={self.poll_interval}s | "
            f"batch_size={self.batch_size}"
        )

        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception as e:
                print(f"[ERROR] Scheduled worker cycle failed: {e}")

            self._stop_event.wait(self.poll_interval)

        print("[SCHEDULED_WORKER] Stopped")

    def run_once(self):

        scheduled_actions = persistence_service.get_due_scheduled_actions(
            self.batch_size
        )

        for scheduled_action in scheduled_actions:
            self.process_scheduled_action(scheduled_action)

    def process_scheduled_action(self, scheduled_action):

        scheduled_action_id = scheduled_action["id"]
        event_id = scheduled_action.get("event_id")

        persistence_service.record_audit_log(
            event_id=event_id,
            level="INFO",
            component="scheduled_worker",
            message="Processing scheduled action",
            details={
                "scheduled_action_id": scheduled_action_id,
                "event_id": event_id,
            },
        )

        if not persistence_service.claim_scheduled_action(scheduled_action_id):
            return

        incident_status = persistence_service.get_incident_status(event_id)

        if incident_status is None:
            self._cancel_scheduled_action(
                scheduled_action,
                reason="incident_not_found",
            )
            return

        if incident_status != "open":
            self._cancel_scheduled_action(
                scheduled_action,
                reason="incident_not_open",
            )
            return

        try:
            dispatch_result = self._execute_scheduled_action(scheduled_action)

            if not dispatch_result.get("success"):
                error = str(dispatch_result.get("results"))
                self._fail_scheduled_action(scheduled_action, error)
                return

            persistence_service.mark_scheduled_action_executed(
                scheduled_action_id
            )
            persistence_service.record_audit_log(
                event_id=event_id,
                level="INFO",
                component="scheduled_worker",
                message="Scheduled action executed",
                details={
                    "scheduled_action_id": scheduled_action_id,
                    "event_id": event_id,
                },
            )

        except Exception as e:
            self._fail_scheduled_action(scheduled_action, str(e))

    def _cancel_scheduled_action(self, scheduled_action, reason):

        scheduled_action_id = scheduled_action["id"]
        event_id = scheduled_action.get("event_id")

        persistence_service.cancel_scheduled_action(
            scheduled_action_id,
            reason=reason,
        )
        persistence_service.record_audit_log(
            event_id=event_id,
            level="INFO",
            component="scheduled_worker",
            message="Scheduled action cancelled because incident is not open",
            details={
                "scheduled_action_id": scheduled_action_id,
                "event_id": event_id,
                "reason": reason,
            },
        )

    def _fail_scheduled_action(self, scheduled_action, error):

        scheduled_action_id = scheduled_action["id"]
        event_id = scheduled_action.get("event_id")

        persistence_service.mark_scheduled_action_failed(
            scheduled_action_id,
            error,
        )
        persistence_service.record_audit_log(
            event_id=event_id,
            level="ERROR",
            component="scheduled_worker",
            message="Scheduled action failed",
            details={
                "scheduled_action_id": scheduled_action_id,
                "event_id": event_id,
                "error": error,
            },
        )

    def _execute_scheduled_action(self, scheduled_action):

        event = self._build_event(scheduled_action)
        actions = scheduled_action.get("actions") or []
        contacts_payload = scheduled_action.get("contacts_payload") or {}
        merged_email_recipients = contacts_payload.get("merged_email_recipients")
        target_contact = contacts_payload.get("target_contact")
        results = []

        if "email" in actions and merged_email_recipients:
            email_result = self.dispatcher.dispatch(
                event=event,
                actions=["email"],
                contacts=[merged_email_recipients],
            )
            results.extend(email_result.get("results", []))

        other_actions = [action for action in actions if action != "email"]

        if other_actions and target_contact:
            other_result = self.dispatcher.dispatch(
                event=event,
                actions=other_actions,
                contacts=[target_contact],
            )
            results.extend(other_result.get("results", []))

        return {
            "success": all(result["success"] for result in results) if results else True,
            "results": results,
        }

    def _build_event(self, scheduled_action):

        client = scheduled_action.get("client") or "unknown"
        host = scheduled_action.get("host") or "unknown"

        event = ZabbixEvent(
            host=f"{client}/{host}",
            trigger=scheduled_action.get("trigger"),
            severity=scheduled_action.get("severity"),
            status="1",
            event_id=scheduled_action.get("event_id"),
            timestamp=str(scheduled_action.get("created_at")),
        )
        event.client = client
        event.parsed_host = host
        event.trigger_group = scheduled_action.get("trigger_group")

        return event


worker = None
worker_thread = None


def is_worker_enabled():
    return os.getenv("SCHEDULED_ACTION_WORKER_ENABLED", "false").lower() == "true"


def start_background_worker():

    global worker, worker_thread

    if worker_thread and worker_thread.is_alive():
        return

    worker = ScheduledActionWorker()
    worker_thread = threading.Thread(
        target=worker.run_forever,
        daemon=True,
    )
    worker_thread.start()


def stop_background_worker():

    if worker:
        worker.stop()


if __name__ == "__main__":
    worker = ScheduledActionWorker()

    try:
        worker.run_forever()
    except KeyboardInterrupt:
        worker.stop()
