import os
import threading

from dotenv import load_dotenv

from app.models.event_model import ZabbixEvent
from app.rules.rule_loader import rule_loader
from app.services.action_dispatcher import ActionDispatcher
from app.services.console import console
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

        try:
            dispatch_result = self._execute_scheduled_action(scheduled_action)

            if not dispatch_result.get("success"):
                error = str(dispatch_result.get("results"))
                self._fail_scheduled_action(scheduled_action, error)
                return

            persistence_service.mark_scheduled_action_executed(
                scheduled_action_id
            )
            print(
                f"[{console.cyan('SCHEDULED_WORKER')}] "
                f"{console.green('Scheduled action executed')} | "
                f"scheduled_action_id={scheduled_action_id} | event_id={event_id}"
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

    def _fail_scheduled_action(self, scheduled_action, error):

        scheduled_action_id = scheduled_action["id"]
        event_id = scheduled_action.get("event_id")

        persistence_service.mark_scheduled_action_failed(
            scheduled_action_id,
            error,
        )
        print(
            f"[{console.cyan('SCHEDULED_WORKER')}] "
            f"{console.orange('Scheduled action failed')} | "
            f"scheduled_action_id={scheduled_action_id} | "
            f"event_id={event_id} | error={error}"
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

        if scheduled_action.get("execution_mode") == "manual_approval":

            return self._execute_manual_approval_action(scheduled_action)

        event = self._build_event(scheduled_action)
        actions = scheduled_action.get("actions") or []
        contacts_payload = scheduled_action.get("contacts_payload") or {}
        target_contact = contacts_payload.get("target_contact")
        execution_actions = contacts_payload.get("execution_actions")
        summary_recipients = contacts_payload.get("summary_recipients") or []
        results = []
        context = self.dispatcher.build_dispatch_context(event)

        if not summary_recipients and contacts_payload.get("merged_email_recipients"):
            summary_recipients = self.dispatcher.normalize_email_recipients([
                contacts_payload.get("merged_email_recipients")
            ])

        if execution_actions is None:
            execution_actions = [action for action in actions if action != "email"]

        execution_actions = self.dispatcher.order_execution_actions(execution_actions)

        if execution_actions and not target_contact and "email" not in actions:
            print(
                f"[{console.level('WARNING')}] "
                "No se envía resumen: no hay contacto destino para ejecutar acciones"
            )
            return {"success": True, "results": []}

        if execution_actions and target_contact:
            other_result = self.dispatcher.dispatch(
                event=event,
                actions=execution_actions,
                contacts=[target_contact],
                context=context,
            )
            results.extend(other_result.get("results", []))
            context = other_result.get("context", context)

        email_result = self.dispatcher.send_email_summary(
            event=event,
            recipients=summary_recipients,
            action_results=results,
            context=context,
        )
        results.append(email_result)

        return {
            "success": all(result["success"] for result in results) if results else True,
            "results": results,
        }

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

        try:
            dispatch_result = self._execute_scheduled_action(scheduled_action)

            if not dispatch_result.get("success"):
                error = str(dispatch_result.get("results"))
                self._fail_scheduled_action(scheduled_action, error)
                return {"success": False, "error": error, "results": dispatch_result.get("results")}

            persistence_service.mark_scheduled_action_executed(scheduled_action_id)
            persistence_service.record_audit_log(
                event_id=event_id,
                level="INFO",
                component="scheduled_worker",
                message="Pending action approved",
                details={"scheduled_action_id": scheduled_action_id},
            )
            return {"success": True, "results": dispatch_result.get("results", [])}

        except Exception as e:
            self._fail_scheduled_action(scheduled_action, str(e))
            return {"success": False, "error": str(e)}

    def _execute_manual_approval_action(self, scheduled_action):

        event = self._build_event(scheduled_action)
        actions = scheduled_action.get("actions") or []
        contacts_payload = scheduled_action.get("contacts_payload") or {}
        client = scheduled_action.get("client")
        target = scheduled_action.get("target")
        pre_target = scheduled_action.get("pre_target") or contacts_payload.get("pre_target")
        action_metadata = contacts_payload.get("action_metadata") or {}
        baseline_contact = rule_loader.get_contact(client, "baseline") or contacts_payload.get("baseline_contact")
        oncall_contact = rule_loader.get_oncall_contact(client, target)
        target_contact_source = "oncall" if oncall_contact else "contact"
        target_contact = oncall_contact

        if not target_contact and pre_target:
            target_contact = rule_loader.get_contact(client, pre_target)

        if not target_contact:
            target_contact = {}

        self._apply_action_metadata(target_contact, action_metadata, event)
        target_contact["_calls_allowed"] = target_contact_source == "oncall"

        email_requested = "email" in actions
        summary_recipients = self.dispatcher.normalize_email_recipients([
            (baseline_contact or {}).get("email"),
            target_contact.get("email") if email_requested or target_contact_source == "oncall" else None,
        ])
        execution_actions = self.dispatcher.order_execution_actions([
            action for action in actions
            if action != "email"
        ])
        results = []
        context = self.dispatcher.build_dispatch_context(event)

        if execution_actions:
            other_result = self.dispatcher.dispatch(
                event=event,
                actions=execution_actions,
                contacts=[target_contact],
                context=context,
            )
            results.extend(other_result.get("results", []))
            context = other_result.get("context", context)

        email_result = self.dispatcher.send_email_summary(
            event=event,
            recipients=summary_recipients,
            action_results=results,
            context=context,
        )
        results.append(email_result)

        return {
            "success": all(result["success"] for result in results) if results else True,
            "results": results,
        }

    def _apply_action_metadata(self, contact, action_metadata, event):

        if contact is None:

            return

        if action_metadata.get("jira_project"):
            contact["jira_project"] = action_metadata.get("jira_project")

        if action_metadata.get("jira_issue_type"):
            contact["jira_issue_type"] = action_metadata.get("jira_issue_type")

        if action_metadata.get("jira_request_type"):
            contact["jira_request_type"] = action_metadata.get("jira_request_type")

        contact["jira_priority"] = rule_loader.get_jira_priority(
            getattr(event, "client", None),
            event.severity,
        )

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
