from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.persistence_service import persistence_service
from app.services.scheduled_action_executor import scheduled_action_executor


router = APIRouter(prefix="/api/scheduled-actions")


class PauseScheduledActionRequest(BaseModel):
    reason: str | None = None


def _error_response(result):
    error = result.get("error")

    if error == "scheduled_action_not_found":
        status_code = 404
    elif error in ("invalid_state_transition", "incident_not_open"):
        status_code = 409
    else:
        status_code = 500

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "scheduled_action_id": result.get("scheduled_action_id"),
            "state": result.get("state"),
            "error": error if status_code != 500 else "internal_error",
        },
    )


@router.post("/{scheduled_action_id}/pause")
def pause_scheduled_action(
    scheduled_action_id: int,
    payload: PauseScheduledActionRequest | None = None,
):
    result = persistence_service.pause_scheduled_action(
        scheduled_action_id,
        reason=payload.reason if payload else "manual_pause",
    )

    if not result.get("success"):
        return _error_response(result)

    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "scheduled_action_id": scheduled_action_id,
            "state": "paused",
        },
    )


@router.post("/{scheduled_action_id}/resume")
def resume_scheduled_action(
    scheduled_action_id: int,
    background_tasks: BackgroundTasks,
):
    result = (
        persistence_service.claim_paused_action_for_immediate_execution(
            scheduled_action_id
        )
    )

    if not result.get("success"):
        return _error_response(result)

    background_tasks.add_task(
        scheduled_action_executor.execute,
        scheduled_action_id,
    )

    return JSONResponse(
        status_code=202,
        content={
            "success": True,
            "scheduled_action_id": scheduled_action_id,
            "state": "processing",
            "execution_started": True,
        },
    )
