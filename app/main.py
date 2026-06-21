import os

from fastapi import FastAPI

from app.api.vonage_webhook import router as vonage_router
from app.api.zabbix_webhook import router as zabbix_router
from app.services.console import console
from app.services.persistence_service import persistence_service
from app.services.scheduled_action_worker import (
    is_worker_enabled,
    start_background_worker,
    stop_background_worker,
)

app = FastAPI()

app.include_router(zabbix_router)
app.include_router(vonage_router)


def _get_int_env(name, default):
    try:
        value = int(os.getenv(name, default))
    except ValueError:
        return default

    return value if value > 0 else default


def print_startup_summary():
    timeout_minutes = _get_int_env(
        "SCHEDULED_ACTION_PROCESSING_TIMEOUT_MINUTES",
        10,
    )
    summary = persistence_service.get_startup_summary(
        scheduled_timeout_minutes=timeout_minutes,
        event_timeout_minutes=timeout_minutes,
    )

    if not summary:
        print(f"[{console.cyan('STARTUP')}] Database summary unavailable")
        return

    print(
        f"[{console.cyan('STARTUP')}] "
        f"open_incidents={summary['open_incidents']} | "
        f"pending_scheduled={summary['pending_scheduled']} | "
        f"due_scheduled={console.yellow(summary['due_scheduled']) if summary['due_scheduled'] else summary['due_scheduled']} | "
        f"stuck_scheduled={console.orange(summary['stuck_scheduled']) if summary['stuck_scheduled'] else summary['stuck_scheduled']} | "
        f"stuck_events={console.orange(summary['stuck_events']) if summary['stuck_events'] else summary['stuck_events']}"
    )


@app.on_event("startup")
def start_scheduled_action_worker():
    print_startup_summary()
    recovery = persistence_service.recover_stale_scheduled_actions(
        timeout_minutes=_get_int_env("SCHEDULED_ACTION_PROCESSING_TIMEOUT_MINUTES", 10),
        max_attempts=_get_int_env("SCHEDULED_ACTION_MAX_ATTEMPTS", 3),
    )
    if recovery.get("recovered") or recovery.get("failed"):
        print(
            f"[{console.cyan('STARTUP')}] "
            f"{console.orange('Recovered stale scheduled actions')} | "
            f"recovered={recovery.get('recovered')} | "
            f"failed={recovery.get('failed')}"
        )

    if is_worker_enabled():
        start_background_worker()


@app.on_event("shutdown")
def stop_scheduled_action_worker():
    stop_background_worker()
