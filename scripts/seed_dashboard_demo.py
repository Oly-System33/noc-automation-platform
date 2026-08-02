import argparse
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from app.db.models import (  # noqa: E402
    ActionRecord,
    AuditLogRecord,
    CallAttemptRecord,
    CallFlowRecord,
    EventRecord,
    IncidentRecord,
    ProcessedEventRecord,
    ScheduledActionRecord,
)
from app.db.session import SessionLocal  # noqa: E402
from app.services.dashboard_query_service import (  # noqa: E402
    DashboardQueryService,
)


DEMO_EVENT_PREFIX = "demo-dashboard-"
DEMO_CLIENT = "Banco Demo"
PROCESSING_TIMEOUT_MINUTES = 10
EXPECTED_STATUSES = (
    "active",
    "scheduled",
    "paused",
    "pending_approval",
    "executing",
    "waiting_confirmation",
    "retry_scheduled",
    "manual_required",
    "stuck",
    "failed",
    "cancelled",
    "closed",
)
DEMO_HOST_BY_STATUS = {
    status: f"demo-{status}-host" for status in EXPECTED_STATUSES
}
CLEANUP_MODELS = (
    CallAttemptRecord,
    CallFlowRecord,
    ScheduledActionRecord,
    ActionRecord,
    AuditLogRecord,
    ProcessedEventRecord,
    EventRecord,
    IncidentRecord,
)


def demo_event_id(status):
    return f"{DEMO_EVENT_PREFIX}{status}"


def build_demo_records(now=None):
    now = now or datetime.now(timezone.utc)
    opened_at = now - timedelta(hours=1)
    incidents = []
    events = []

    for index, status in enumerate(EXPECTED_STATUSES):
        event_id = demo_event_id(status)
        current_status = "closed" if status == "closed" else "open"
        created_at = opened_at + timedelta(minutes=index)
        incidents.append(IncidentRecord(
            event_id=event_id,
            client=DEMO_CLIENT,
            host=DEMO_HOST_BY_STATUS[status],
            trigger=f"Dashboard demo {status}",
            trigger_group="dashboard_demo",
            severity="Information",
            opened_at=opened_at.isoformat(),
            closed_at=now.isoformat() if status == "closed" else None,
            duration="1h" if status == "closed" else None,
            current_status=current_status,
            created_at=created_at,
            updated_at=now - timedelta(seconds=index),
        ))
        events.append(EventRecord(
            event_id=event_id,
            client=DEMO_CLIENT,
            host=DEMO_HOST_BY_STATUS[status],
            trigger=f"Dashboard demo {status}",
            trigger_group="dashboard_demo",
            severity="Information",
            status="0" if status == "closed" else "1",
            timestamp=opened_at.isoformat(),
            duration="1h" if status == "closed" else "0s",
            raw_payload=None,
            created_at=created_at,
        ))

    scheduled_actions = [
        _build_scheduled_action(
            "scheduled",
            "pending",
            now,
            scheduled_at=now + timedelta(minutes=30),
        ),
        _build_scheduled_action(
            "paused",
            "paused",
            now,
            scheduled_at=now + timedelta(minutes=20),
            paused_at=now - timedelta(minutes=2),
            pause_reason="demo_manual_pause",
        ),
        _build_scheduled_action(
            "pending_approval",
            "pending_approval",
            now,
            scheduled_at=now + timedelta(minutes=45),
            execution_mode="manual_approval",
            approval_when="always",
        ),
        _build_scheduled_action(
            "executing",
            "processing",
            now,
            scheduled_at=now + timedelta(hours=1),
            processing_started_at=now - timedelta(minutes=1),
            attempt_count=1,
        ),
        _build_scheduled_action(
            "failed",
            "failed",
            now,
            scheduled_at=now - timedelta(minutes=20),
            attempt_count=1,
            last_error="Demo controlled failure",
        ),
        _build_scheduled_action(
            "cancelled",
            "cancelled",
            now,
            scheduled_at=now - timedelta(minutes=15),
            cancelled_at=now - timedelta(minutes=5),
            cancel_reason="demo_manual_cancel",
        ),
    ]
    call_flows = [
        _build_call_flow("waiting_confirmation", now),
        _build_call_flow(
            "retry_scheduled",
            now,
            attempt_count=1,
            next_attempt_at=now + timedelta(minutes=5),
        ),
        _build_call_flow(
            "manual_required",
            now,
            attempt_count=3,
            manual_required_at=now - timedelta(minutes=1),
        ),
    ]
    stuck_started_at = now - timedelta(minutes=30)
    processed_events = [ProcessedEventRecord(
        event_id=demo_event_id("stuck"),
        zabbix_status="PROBLEM",
        client=DEMO_CLIENT,
        host=DEMO_HOST_BY_STATUS["stuck"],
        trigger="Dashboard demo stuck",
        severity="Information",
        state="processing",
        first_seen_at=stuck_started_at,
        last_seen_at=stuck_started_at,
        received_count=1,
        processing_started_at=stuck_started_at,
        processed_at=None,
        error_message="Demo processing exceeded timeout",
        created_at=stuck_started_at,
        updated_at=stuck_started_at,
    )]

    return {
        IncidentRecord: incidents,
        EventRecord: events,
        ScheduledActionRecord: scheduled_actions,
        CallFlowRecord: call_flows,
        ProcessedEventRecord: processed_events,
    }


def _build_scheduled_action(status, state, now, **overrides):
    event_id = demo_event_id(status)
    values = {
        "event_id": event_id,
        "client": DEMO_CLIENT,
        "host": DEMO_HOST_BY_STATUS[status],
        "trigger": f"Dashboard demo {status}",
        "trigger_group": "dashboard_demo",
        "severity": "Information",
        "actions": ["demo_action"],
        "target": "demo-target",
        "dedupe_key": f"{event_id}|dashboard_demo|demo-target|demo_action",
        "contacts_payload": None,
        "execution_mode": "dashboard_demo",
        "approval_when": "never",
        "pre_actions": None,
        "pre_target": None,
        "scheduled_at": now + timedelta(hours=1),
        "state": state,
        "created_at": now - timedelta(minutes=5),
        "paused_at": None,
        "resumed_at": None,
        "pause_reason": None,
        "processing_started_at": None,
        "attempt_count": 0,
        "executed_at": None,
        "cancelled_at": None,
        "cancel_reason": None,
        "error_message": None,
        "last_error": None,
    }
    values.update(overrides)
    return ScheduledActionRecord(**values)


def _build_call_flow(status, now, **overrides):
    event_id = demo_event_id(status)
    values = {
        "event_id": event_id,
        "client": DEMO_CLIENT,
        "host": DEMO_HOST_BY_STATUS[status],
        "trigger": f"Dashboard demo {status}",
        "severity": "Information",
        "target": "demo-target",
        "phone": None,
        "state": status,
        "max_attempts": 3,
        "attempt_count": 0,
        "confirmed": "false",
        "confirmed_at": None,
        "confirmed_attempt": None,
        "manual_required_at": None,
        "next_attempt_at": None,
        "summary_payload": None,
        "created_at": now - timedelta(minutes=5),
        "updated_at": now - timedelta(minutes=1),
    }
    values.update(overrides)
    return CallFlowRecord(**values)


def clean_demo_data(session):
    removed = {}

    for model in CLEANUP_MODELS:
        removed[model.__tablename__] = (
            session.query(model)
            .filter(model.event_id.like(f"{DEMO_EVENT_PREFIX}%"))
            .delete(synchronize_session=False)
        )

    return removed


def seed_demo_data(session_factory=SessionLocal, now=None):
    session = session_factory()

    try:
        removed = clean_demo_data(session)
        records_by_model = build_demo_records(now=now)

        for records in records_by_model.values():
            session.add_all(records)

        session.commit()
        return {
            "removed": removed,
            "incidents_created": len(records_by_model[IncidentRecord]),
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def clean_demo_records(session_factory=SessionLocal):
    session = session_factory()

    try:
        removed = clean_demo_data(session)
        session.commit()
        return removed
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def verify_demo_data(query_service=None, output=print):
    service = query_service or DashboardQueryService()
    response = service.list_incidents(
        limit=100,
        client=DEMO_CLIENT,
    )
    items = [
        item for item in response.items
        if item.event_id.startswith(DEMO_EVENT_PREFIX)
    ]
    counts = Counter(item.display_status.value for item in items)
    missing = [status for status in EXPECTED_STATUSES if counts[status] == 0]
    invalid_counts = {
        status: counts[status]
        for status in EXPECTED_STATUSES
        if counts[status] != 1
    }
    unexpected = sorted(set(counts) - set(EXPECTED_STATUSES))
    success = not missing and not invalid_counts and not unexpected

    if output is not None:
        output("Dashboard demo verification")
        output(f"Client: {DEMO_CLIENT}")
        output(f"Incidents found: {len(items)}")

        for item in sorted(items, key=lambda value: value.event_id):
            output(f"{item.event_id}: {item.display_status.value}")

        for status in EXPECTED_STATUSES:
            output(f"{status}: {counts[status]}")

        if missing:
            output(f"Missing states: {', '.join(missing)}")
        if unexpected:
            output(f"Unexpected states: {', '.join(unexpected)}")

    return {
        "success": success,
        "items": items,
        "counts": dict(counts),
        "missing": missing,
        "invalid_counts": invalid_counts,
        "unexpected": unexpected,
    }


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Manage synthetic dashboard demonstration data."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--clean",
        action="store_true",
        help="Delete dashboard demo records without recreating them.",
    )
    mode.add_argument(
        "--verify",
        action="store_true",
        help="Verify dashboard demo states without modifying the database.",
    )
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)

    try:
        if args.clean:
            removed = clean_demo_records()
            print("Dashboard demo data removed")
            print(f"Records removed: {sum(removed.values())}")
            return 0

        if args.verify:
            verification = verify_demo_data()
            return 0 if verification["success"] else 1

        seed_demo_data()
        verification = verify_demo_data(output=None)
        print("Dashboard demo data created")
        print(f"Client: {DEMO_CLIENT}")
        print(f"Incidents created: {len(verification['items'])}")

        for status in EXPECTED_STATUSES:
            print(f"{status}: {verification['counts'].get(status, 0)}")

        return 0 if verification["success"] else 1
    except Exception as error:
        print(f"Dashboard demo operation failed: {type(error).__name__}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
