import logging

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.services.persistence_service import persistence_service
from app.services.scheduled_action_executor import scheduled_action_executor
from app.services.scheduled_action_worker import ScheduledActionWorker


router = APIRouter(prefix="/api/scheduled-actions")
logger = logging.getLogger(__name__)
scheduled_action_approval_worker = ScheduledActionWorker(
    executor=scheduled_action_executor
)


class PauseScheduledActionRequest(BaseModel):
    reason: str | None = None


class ApproveScheduledActionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class ApproveScheduledActionResponse(BaseModel):
    success: bool
    scheduled_action_id: int
    previous_state: str
    state: str
    approved: bool
    execution_started: bool


class ScheduledActionErrorResponse(BaseModel):
    success: bool
    scheduled_action_id: int
    state: str | None = None
    error: str


def _error_response(result):
    error = result.get("error")

    if error == "scheduled_action_not_found":
        status_code = 404
    elif error in (
        "invalid_state_transition",
        "incident_not_found",
        "incident_not_open",
    ):
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


@router.post(
    "/{scheduled_action_id}/approve",
    status_code=202,
    response_model=ApproveScheduledActionResponse,
    responses={
        404: {
            "model": ScheduledActionErrorResponse,
            "description": "Scheduled action not found",
        },
        409: {
            "model": ScheduledActionErrorResponse,
            "description": "Scheduled action cannot be approved",
        },
        500: {
            "model": ScheduledActionErrorResponse,
            "description": "Unexpected internal error",
        },
    },
    summary="Approve scheduled action",
    description=(
        "Atomically approve a pending action and start its execution."
    ),
)
def approve_scheduled_action(
    scheduled_action_id: int,
    background_tasks: BackgroundTasks,
    payload: ApproveScheduledActionRequest | None = None,
):
    try:
        result = scheduled_action_approval_worker.approve_scheduled_action(
            scheduled_action_id,
            source="dashboard_api",
            note=payload.note if payload else None,
            defer_execution=True,
        )
    except Exception as error:
        logger.error(
            "Unexpected scheduled action approval error: %s",
            type(error).__name__,
        )
        return _error_response({
            "success": False,
            "scheduled_action_id": scheduled_action_id,
            "state": None,
            "error": "internal_error",
        })

    if not result.get("success"):
        return _error_response(result)

    background_tasks.add_task(
        scheduled_action_approval_worker.executor.execute,
        scheduled_action_id,
    )

    return JSONResponse(
        status_code=202,
        content={
            "success": True,
            "scheduled_action_id": scheduled_action_id,
            "previous_state": result.get("previous_state"),
            "state": result.get("state"),
            "approved": True,
            "execution_started": True,
        },
    )
