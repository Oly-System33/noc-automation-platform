import logging
from typing import Annotated, Callable

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas.interventions import (
    InterventionErrorResponse,
    InterventionItem,
    InterventionListResponse,
    InterventionSourceType,
    InterventionStatus,
    InterventionRunbook,
)
from app.services.intervention_service import (
    InterventionDataError,
    InterventionNotFound,
    InterventionRetryNotSafe,
    intervention_service,
)


router = APIRouter(prefix="/api/interventions", tags=["interventions"])
logger = logging.getLogger(__name__)

ERROR_RESPONSES = {
    404: {"model": InterventionErrorResponse, "description": "Intervention or runbook not found"},
    503: {"model": InterventionErrorResponse, "description": "Intervention data is temporarily unavailable"},
    500: {"model": InterventionErrorResponse, "description": "Unexpected internal error"},
}


def _error(status_code, detail, code):
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "code": code},
    )


def _execute(operation: Callable):
    try:
        return operation()
    except InterventionNotFound:
        return _error(404, "Intervention not found", "intervention_not_found")
    except InterventionRetryNotSafe:
        return _error(409, "retry_not_safe", "retry_not_safe")
    except InterventionDataError:
        logger.warning("Intervention data is unavailable")
        return _error(503, "Intervention data is temporarily unavailable", "interventions_unavailable")
    except Exception as error:
        logger.error("Unexpected interventions API error: %s", type(error).__name__)
        return _error(500, "Internal server error", "internal_error")


@router.get(
    "",
    response_model=InterventionListResponse,
    responses={503: ERROR_RESPONSES[503], 500: ERROR_RESPONSES[500]},
    summary="List interventions",
)
def list_interventions(
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(max_length=200)] = None,
    source_type: Annotated[InterventionSourceType | None, Query()] = None,
    status: Annotated[InterventionStatus | None, Query()] = None,
):
    return _execute(lambda: intervention_service.list_interventions(
        limit=limit, offset=offset, search=search, source_type=source_type,
        status=status,
    ))


@router.post(
    "/{intervention_id}/retry",
    response_model=None,
    responses={
        **ERROR_RESPONSES,
        409: {"model": InterventionErrorResponse, "description": "Retry is not safe"},
    },
    summary="Reject an unsafe intervention retry",
)
def retry_intervention(intervention_id: str):
    return _execute(lambda: intervention_service.reject_retry(intervention_id))


@router.get(
    "/{intervention_id}/runbook",
    response_model=InterventionRunbook,
    responses=ERROR_RESPONSES,
    summary="Get a safe intervention runbook",
)
def get_intervention_runbook(intervention_id: str):
    return _execute(lambda: intervention_service.get_runbook(intervention_id))
