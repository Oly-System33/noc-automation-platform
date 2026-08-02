import os
import threading

from dotenv import load_dotenv

from app.services.console import console
from app.services.persistence_service import persistence_service
from app.services.scheduled_action_executor import ScheduledActionExecutor


load_dotenv()


class ScheduledActionWorker:

    def __init__(self, dispatcher=None, executor=None):
        self.executor = executor or ScheduledActionExecutor(dispatcher=dispatcher)
        self.dispatcher = self.executor.dispatcher
        self.poll_interval = self._get_int_env(
            "SCHEDULED_ACTION_POLL_INTERVAL_SECONDS",
            30,
        )
        self.batch_size = self._get_int_env(
            "SCHEDULED_ACTION_BATCH_SIZE",
            20,
        )
        self.processing_timeout_minutes = self._get_int_env(
            "SCHEDULED_ACTION_PROCESSING_TIMEOUT_MINUTES",
            10,
        )
        self.max_attempts = self._get_int_env(
            "SCHEDULED_ACTION_MAX_ATTEMPTS",
            3,
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
            f"[{console.cyan('SCHEDULED_WORKER')}] Started | "
            f"poll_interval={self.poll_interval}s | "
            f"batch_size={self.batch_size}"
        )

        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception as e:
                print(f"[{console.level('ERROR')}] Scheduled worker cycle failed: {e}")

            self._stop_event.wait(self.poll_interval)

        print(f"[{console.cyan('SCHEDULED_WORKER')}] Stopped")

    def run_once(self):

        recovery = persistence_service.recover_stale_scheduled_actions(
            timeout_minutes=self.processing_timeout_minutes,
            max_attempts=self.max_attempts,
        )

        if recovery.get("recovered") or recovery.get("failed"):
            print(
                f"[{console.cyan('SCHEDULED_WORKER')}] "
                f"{console.orange('Recovered stale actions')} | "
                f"recovered={recovery.get('recovered')} | "
                f"failed={recovery.get('failed')}"
            )

        scheduled_actions = persistence_service.get_due_scheduled_actions(
            self.batch_size
        )

        for scheduled_action in scheduled_actions:
            self.process_scheduled_action(scheduled_action)

    def process_scheduled_action(self, scheduled_action):

        scheduled_action_id = scheduled_action["id"]
        event_id = scheduled_action.get("event_id")

        print(
            f"[{console.cyan('SCHEDULED_WORKER')}] "
            f"{console.cyan('Processing scheduled action')} | "
            f"scheduled_action_id={scheduled_action_id} | event_id={event_id}"
        )

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

        self.executor.execute(scheduled_action_id)

    def _cancel_scheduled_action(self, scheduled_action, reason):

        scheduled_action_id = scheduled_action["id"]
        event_id = scheduled_action.get("event_id")

        persistence_service.cancel_scheduled_action(
            scheduled_action_id,
            reason=reason,
        )
        print(
            f"[{console.cyan('SCHEDULED_WORKER')}] "
            f"{console.yellow('Scheduled action cancelled')} | "
            f"scheduled_action_id={scheduled_action_id} | "
            f"event_id={event_id} | reason={reason}"
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

    def _execute_scheduled_action(self, scheduled_action):
        return self.executor.execute_action(scheduled_action)

    def approve_scheduled_action(self, scheduled_action_id):

        if not persistence_service.claim_pending_approval_action(scheduled_action_id):
            return {
                "success": False,
                "error": "pending_approval_not_found_or_already_claimed",
            }

        scheduled_action = persistence_service.get_scheduled_action(scheduled_action_id)

        if not scheduled_action:
            return {"success": False, "error": "scheduled_action_not_found"}

        event_id = scheduled_action.get("event_id")
        incident_status = persistence_service.get_incident_status(event_id)

        if incident_status is None:
            self._cancel_scheduled_action(scheduled_action, "incident_not_found")
            return {"success": False, "error": "incident_not_found"}

        if incident_status != "open":
            self._cancel_scheduled_action(scheduled_action, "incident_not_open")
            return {"success": False, "error": "incident_not_open"}

        result = self.executor.execute(scheduled_action_id)

        if result.get("success"):
            persistence_service.record_audit_log(
                event_id=event_id,
                level="INFO",
                component="scheduled_worker",
                message="Pending action approved",
                details={"scheduled_action_id": scheduled_action_id},
            )
        return result

    def _build_event(self, scheduled_action):
        return self.executor.build_event(scheduled_action)


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
