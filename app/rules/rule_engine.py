from datetime import datetime, timedelta, timezone

from app.rules.rule_loader import rule_loader
from app.services.action_dispatcher import ActionDispatcher
from app.services.console import console
from app.services.persistence_service import persistence_service


class RuleEngine:

    def __init__(self):
        self.dispatcher = ActionDispatcher()

    def evaluate_problem(self, event):

        # 1) separar cliente y host
        client, host = rule_loader.extract_client_and_host(event.host)
        event.client = client
        event.parsed_host = host

        print(f"[{console.cyan('RULE_ENGINE')}] Cliente: {client} | Host: {host}")
        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="INFO",
            component="rule_engine",
            message="Client and host detected",
            details={"client": client, "host": host},
        )

        try:
            self._evaluate_problem_with_runbook(event, client, host)
        except FileNotFoundError:
            event.unprocessable_event = True
            print(f"[{console.level('WARNING')}] Runbook not found for client: {client}")
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="WARNING",
                component="rule_engine",
                message=f"Runbook not found for client: {client}",
                details={"client": client, "host": host},
            )
            persistence_service.mark_event_processed(event.event_id, "PROBLEM")
            return

        except Exception as e:
            print(f"[{console.level('ERROR')}] RuleEngine problem evaluation failed: {e}")
            persistence_service.mark_event_failed(
                event.event_id,
                "PROBLEM",
                str(e),
            )
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="ERROR",
                component="rule_engine",
                message="Problem evaluation failed",
                details={"error": str(e)},
            )
            return

        persistence_service.mark_event_processed(event.event_id, "PROBLEM")

    def _evaluate_problem_with_runbook(self, event, client, host):

        # 2) verificar host monitoreado
        if not rule_loader.is_host_monitored(client, host):

            print(f"[{console.level('INFO')}] Host no monitoreado")
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="INFO",
                component="rule_engine",
                message="Host not monitored",
                details={"client": client, "host": host},
            )

            event.unmanaged_host = True
            return

        # 3) clasificar trigger
        trigger_group = rule_loader.get_trigger_group(
            client,
            event.trigger
        )

        print(f"[{console.level('INFO')}] Trigger group detectado: {trigger_group}")
        event.trigger_group = trigger_group
        persistence_service.update_event_context(
            event_id=event.event_id,
            client=client,
            host=host,
            trigger_group=trigger_group,
        )
        persistence_service.open_incident(
            event=event,
            client=client,
            host=host,
            trigger_group=trigger_group,
        )
        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="INFO",
            component="rule_engine",
            message="Trigger group detected",
            details={"trigger_group": trigger_group},
        )

        # 4) verificar suppressions
        if rule_loader.is_suppressed(client, host, trigger_group):

            print(f"[{console.level('INFO')}] {console.yellow('Evento suprimido por regla horaria')}")
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="INFO",
                component="rule_engine",
                message="Event suppressed by schedule rule",
                details={"trigger_group": trigger_group},
            )

            return

        # 5) buscar acción adicional
        action = rule_loader.get_action(
            client,
            host,
            trigger_group
        )

        if not action:

            print(f"[{console.level('INFO')}] No hay acción adicional definida")
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="INFO",
                component="rule_engine",
                message="No additional action defined",
                details={"trigger_group": trigger_group},
            )

            return

        team = action["target"]
        delay_minutes = action.get("delay_minutes", 0)

        if action.get("invalid_actions"):
            print(
                f"[{console.level('WARNING')}] Invalid runbook actions ignored | "
                f"actions={action.get('invalid_actions')}"
            )
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="WARNING",
                component="rule_engine",
                message="Invalid runbook actions ignored",
                details={
                    "invalid_actions": action.get("invalid_actions"),
                    "raw_action": action.get("action_raw"),
                    "client": client,
                    "host": host,
                    "trigger_group": trigger_group,
                    "target": team,
                },
            )

        if not action.get("action"):
            print(f"[{console.level('WARNING')}] No valid runbook actions found")
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="WARNING",
                component="rule_engine",
                message="No valid runbook actions found",
                details={
                    "raw_action": action.get("action_raw"),
                    "invalid_actions": action.get("invalid_actions"),
                    "client": client,
                    "host": host,
                    "trigger_group": trigger_group,
                    "target": team,
                },
            )
            return

        if action.get("delay_minutes_invalid"):
            print(f"[{console.level('WARNING')}] Invalid delay_minutes, using 0")
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="WARNING",
                component="rule_engine",
                message="Invalid delay_minutes, using 0",
                details={"value": action.get("delay_minutes_raw")},
            )

        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="INFO",
            component="rule_engine",
            message="Action found",
            details={
                "actions": action.get("action"),
                "target": team,
                "trigger_group": trigger_group,
                "delay_minutes": delay_minutes,
            },
        )

        baseline_contact = rule_loader.get_contact(client, "baseline")

        oncall_contact = rule_loader.get_oncall_contact(client, team)
        target_contact_source = "oncall" if oncall_contact else "contact"
        target_contact = oncall_contact

        if not target_contact:
            target_contact = rule_loader.get_contact(client, team)

        self._apply_action_metadata(target_contact, action, event)

        approval_when = action.get("approval_when") or "never"
        requires_approval = (
            approval_when == "always"
            or (approval_when == "no_oncall" and not oncall_contact)
        )

        if action.get("invalid_pre_actions"):
            print(
                f"[{console.level('WARNING')}] Invalid runbook pre-actions ignored | "
                f"actions={action.get('invalid_pre_actions')}"
            )
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="WARNING",
                component="rule_engine",
                message="Invalid runbook pre-actions ignored",
                details={
                    "invalid_pre_actions": action.get("invalid_pre_actions"),
                    "raw_pre_actions": action.get("pre_actions_raw"),
                    "client": client,
                    "host": host,
                    "trigger_group": trigger_group,
                    "target": team,
                },
            )

        if requires_approval:
            self._handle_manual_approval_required(
                event=event,
                client=client,
                host=host,
                trigger_group=trigger_group,
                action=action,
                target=team,
                baseline_contact=baseline_contact,
                approval_when=approval_when,
            )
            return

        action_plan = self._build_action_plan(
            event=event,
            client=client,
            host=host,
            trigger_group=trigger_group,
            action=action,
            target=team,
            baseline_contact=baseline_contact,
            target_contact=target_contact,
            target_contact_source=target_contact_source,
            delay_minutes=delay_minutes,
        )

        if delay_minutes > 0:
            self._schedule_action_plan(action_plan)
            return

        self._execute_action_plan(action_plan)

    def _apply_action_metadata(self, contact, action, event):

        if not contact:

            return

        if "jira" in action.get("action", []) or "jira" in action.get("pre_actions", []):
            contact["jira_priority"] = rule_loader.get_jira_priority(
                getattr(event, "client", None),
                event.severity,
            )

        if "jira_project" in action:
            contact["jira_project"] = action["jira_project"]

        if "jira_issue_type" in action:
            contact["jira_issue_type"] = action["jira_issue_type"]

        if "jira_request_type" in action:
            contact["jira_request_type"] = action["jira_request_type"]

    def _handle_manual_approval_required(self, event, client, host, trigger_group, action, target, baseline_contact, approval_when):

        print(
            f"[{console.cyan('RULE_ENGINE')}] "
            f"{console.yellow('Action requires manual approval')} | "
            f"event_id={event.event_id} | approval_when={approval_when}"
        )
        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="INFO",
            component="rule_engine",
            message="Action requires manual approval",
            details={
                "actions": action.get("action"),
                "target": target,
                "approval_when": approval_when,
                "pre_actions": action.get("pre_actions"),
                "pre_target": action.get("pre_target"),
            },
        )

        self._execute_pre_actions(
            event=event,
            client=client,
            host=host,
            trigger_group=trigger_group,
            action=action,
            baseline_contact=baseline_contact,
        )
        self._create_pending_approval(
            event=event,
            client=client,
            host=host,
            trigger_group=trigger_group,
            action=action,
            target=target,
            baseline_contact=baseline_contact,
            approval_when=approval_when,
        )

    def _execute_pre_actions(self, event, client, host, trigger_group, action, baseline_contact):

        pre_actions = [
            pre_action for pre_action in action.get("pre_actions") or []
            if pre_action != "calls"
        ]

        if not pre_actions:

            return

        pre_target = action.get("pre_target")
        pre_contact = rule_loader.get_contact(client, pre_target) if pre_target else None

        if not pre_contact:
            print(
                f"[{console.level('WARNING')}] "
                "Pre-actions skipped: pre_target contact not found"
            )
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="WARNING",
                component="rule_engine",
                message="Pre-actions skipped because pre_target contact was not found",
                details={"pre_target": pre_target, "pre_actions": pre_actions},
            )
            return

        pre_action = dict(action)
        pre_action["action"] = pre_actions
        self._apply_action_metadata(pre_contact, pre_action, event)
        pre_plan = self._build_action_plan(
            event=event,
            client=client,
            host=host,
            trigger_group=trigger_group,
            action=pre_action,
            target=pre_target,
            baseline_contact=baseline_contact,
            target_contact=pre_contact,
            target_contact_source="contact",
            delay_minutes=0,
        )
        self._execute_action_plan(pre_plan)
        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="INFO",
            component="rule_engine",
            message="Pre-actions executed",
            details={"pre_target": pre_target, "pre_actions": pre_actions},
        )

    def _create_pending_approval(self, event, client, host, trigger_group, action, target, baseline_contact, approval_when):

        contacts_payload = {
            "baseline_contact": baseline_contact,
            "pre_target": action.get("pre_target"),
            "action_metadata": {
                "jira_project": action.get("jira_project"),
                "jira_issue_type": action.get("jira_issue_type"),
                "jira_request_type": action.get("jira_request_type"),
            },
            "worker_note": "Manual approval action; contacts must be re-resolved at approval time.",
        }

        result = persistence_service.create_scheduled_action(
            event=event,
            client=client,
            host=host,
            trigger_group=trigger_group,
            actions=action.get("action"),
            target=target,
            contacts_payload=contacts_payload,
            scheduled_at=datetime.now(timezone.utc),
            state="pending_approval",
            execution_mode="manual_approval",
            approval_when=approval_when,
            pre_actions=action.get("pre_actions"),
            pre_target=action.get("pre_target"),
        )

        if result.get("success"):
            scheduled_action_id = result.get("scheduled_action_id")
            status_text = (
                "PENDING MANUAL APPROVAL ALREADY EXISTS"
                if result.get("duplicate")
                else "ACTION PENDING MANUAL APPROVAL"
            )
            approve_command = (
                f".venv/bin/python -m app.cli.approve_action "
                f"{scheduled_action_id}"
            )
            cancel_command = (
                f".venv/bin/python -m app.cli.cancel_action "
                f"{scheduled_action_id}"
            )
            print(
                f"[{console.cyan('RULE_ENGINE')}] "
                f"{console.yellow(status_text)} | "
                f"event_id={console.cyan(event.event_id)} | "
                f"approval_id={console.orange(scheduled_action_id)} | "
                f"target={target} | pre_target={action.get('pre_target')}"
            )
            print(
                f"[{console.cyan('RULE_ENGINE')}] "
                f"Approve: {console.orange(approve_command)}"
            )
            print(
                f"[{console.cyan('RULE_ENGINE')}] "
                f"Cancel pending action only: {console.orange(cancel_command)}"
            )

        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="INFO" if result.get("success") else "ERROR",
            component="rule_engine",
            message="Pending approval action created" if result.get("success") else "Failed to create pending approval action",
            details={
                "scheduled_action_id": result.get("scheduled_action_id"),
                "duplicate": result.get("duplicate"),
                "error": result.get("error"),
                "target": target,
                "actions": action.get("action"),
            },
        )

    def _build_action_plan(self, event, client, host, trigger_group, action, target, baseline_contact, target_contact, target_contact_source, delay_minutes):

        email_requested = "email" in action["action"]
        summary_recipients = self._resolve_summary_recipients(
            baseline_contact=baseline_contact,
            target_contact=target_contact,
            include_target_email=email_requested or target_contact_source == "oncall",
        )
        execution_actions = self.dispatcher.order_execution_actions([
            a for a in action["action"]
            if a != "email"
        ])

        if target_contact:
            target_contact["_calls_allowed"] = target_contact_source == "oncall"

        return {
            "event": event,
            "client": client,
            "host": host,
            "trigger_group": trigger_group,
            "actions": action["action"],
            "target": target,
            "contacts": {
                "baseline_contact": baseline_contact,
                "target_contact": target_contact,
                "target_contact_source": target_contact_source,
                "summary_recipients": summary_recipients,
                "email_requested": email_requested,
                "execution_actions": execution_actions,
            },
            "delay_minutes": delay_minutes,
        }

    def _resolve_summary_recipients(self, baseline_contact, target_contact, include_target_email):

        recipient_values = []

        if baseline_contact and baseline_contact.get("email") == baseline_contact.get("email"):
            recipient_values.append(baseline_contact.get("email"))

        if include_target_email and target_contact and target_contact.get("email") == target_contact.get("email"):
            recipient_values.append(target_contact.get("email"))

        return self.dispatcher.normalize_email_recipients(recipient_values)

    def _execute_action_plan(self, action_plan):

        event = action_plan["event"]
        contacts = action_plan["contacts"]
        execution_actions = contacts["execution_actions"]
        target_contact = contacts["target_contact"]
        results = []
        context = self.dispatcher.build_dispatch_context(event)

        if execution_actions and not target_contact and not contacts["email_requested"]:
            print(
                f"[{console.level('WARNING')}] "
                "No se envía resumen: no hay contacto destino para ejecutar acciones"
            )
            return {"success": True, "results": []}

        if execution_actions and target_contact:

            dispatch_result = self.dispatcher.dispatch(
                event=event,
                actions=execution_actions,
                contacts=[target_contact],
                context=context,
            )
            results.extend(dispatch_result.get("results", []))
            context = dispatch_result.get("context", context)

        if str(event.status) in ("1", "PROBLEM"):
            email_result = self.dispatcher.send_email_summary(
                event=event,
                recipients=contacts["summary_recipients"],
                action_results=results,
                context=context,
            )
            results.append(email_result)

        return {
            "success": all(result.get("success") for result in results) if results else True,
            "results": results,
        }

    def _schedule_action_plan(self, action_plan):

        event = action_plan["event"]
        delay_minutes = action_plan["delay_minutes"]
        scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
        contacts = action_plan["contacts"]

        contacts_payload = {
            "baseline_contact": contacts["baseline_contact"],
            "target_contact": contacts["target_contact"],
            "target_contact_source": contacts["target_contact_source"],
            "summary_recipients": contacts["summary_recipients"],
            "email_requested": contacts["email_requested"],
            "execution_actions": contacts["execution_actions"],
            "dispatch_contacts": {
                "other": [contacts["target_contact"]]
                if contacts["target_contact"] else [],
            },
            "worker_note": "Plan is pre-resolved; worker should not need to reload Excel.",
        }

        result = persistence_service.create_scheduled_action(
            event=event,
            client=action_plan["client"],
            host=action_plan["host"],
            trigger_group=action_plan["trigger_group"],
            actions=action_plan["actions"],
            target=action_plan["target"],
            contacts_payload=contacts_payload,
            scheduled_at=scheduled_at,
        )

        if result.get("success") and result.get("duplicate"):
            print(
                f"[{console.cyan('RULE_ENGINE')}] "
                f"{console.yellow('Scheduled action already exists')} | "
                f"event_id={event.event_id} | "
                f"dedupe_key={result.get('dedupe_key')}"
            )
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="INFO",
                component="rule_engine",
                message="Scheduled action already exists",
                details={
                    "event_id": event.event_id,
                    "scheduled_action_id": result.get("scheduled_action_id"),
                    "dedupe_key": result.get("dedupe_key"),
                },
            )
            return

        if result.get("success"):
            print(
                f"[{console.cyan('RULE_ENGINE')}] "
                f"{console.cyan('Action scheduled')} | "
                f"event_id={event.event_id} | "
                f"delay_minutes={delay_minutes} | "
                f"scheduled_at={result.get('scheduled_at')}"
            )
            persistence_service.record_audit_log(
                event_id=event.event_id,
                level="INFO",
                component="rule_engine",
                message="Action scheduled",
                details={
                    "event_id": event.event_id,
                    "delay_minutes": delay_minutes,
                    "scheduled_at": result.get("scheduled_at"),
                    "actions": action_plan["actions"],
                    "target": action_plan["target"],
                    "scheduled_action_id": result.get("scheduled_action_id"),
                },
            )
            return

        print(
            f"[{console.level('ERROR')}] Failed to schedule action | "
            f"event_id={event.event_id} | "
            f"error={result.get('error')}"
        )
        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="ERROR",
            component="database",
            message="Failed to schedule action",
            details={
                "event_id": event.event_id,
                "error": result.get("error"),
            },
        )

    def close_incident(self, event, duration):

        client, host = rule_loader.extract_client_and_host(event.host)
        event.client = client
        event.parsed_host = host

        print(
            f"[{console.cyan('RULE_ENGINE')}] "
            f"{console.green('Incidente cerrado')}: {host} "
            f"(duración: {duration})"
        )
        persistence_service.record_audit_log(
            event_id=event.event_id,
            level="INFO",
            component="rule_engine",
            message="Incident closed",
            details={"client": client, "host": host, "duration": duration},
        )


rule_engine = RuleEngine()
