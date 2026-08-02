import logging
from typing import Annotated, Callable

from fastapi import APIRouter, HTTPException, Query

from app.schemas.dashboard import (
    DashboardIncidentListResponse,
    DashboardStatus,
    DashboardSummaryResponse,
)
from app.services.dashboard_query_service import (
    DashboardQueryError,
    dashboard_query_service,
)


logger = logging.getLogger(__name__)

dashboard_router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
)
incidents_router = APIRouter(
    prefix="/api/incidents",
    tags=["incidents"],
)

ERROR_RESPONSES = {
    503: {"description": "Dashboard data is temporarily unavailable"},
    500: {"description": "Unexpected internal error"},
}


def _execute_query(operation: Callable):
    try:
        return operation()
    except DashboardQueryError:
        logger.warning("Dashboard data is unavailable")
        raise HTTPException(
            status_code=503,
            detail="Dashboard data is temporarily unavailable",
        ) from None
    except Exception as error:
        logger.error(
            "Unexpected dashboard API error: %s",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        ) from None


@dashboard_router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Get dashboard summary",
    description="Return incident counts by visible status and client.",
    responses=ERROR_RESPONSES,
)
def get_dashboard_summary():
    return _execute_query(dashboard_query_service.get_summary)


@incidents_router.get(
    "",
    response_model=DashboardIncidentListResponse,
    summary="List dashboard incidents",
    description=(
        "Return incidents ordered by recent activity, optionally filtered "
        "by client and visible dashboard status."
    ),
    responses=ERROR_RESPONSES,
)
def list_dashboard_incidents(
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=500,
            description="Maximum number of incidents to return.",
        ),
    ] = 100,
    client: Annotated[
        str | None,
        Query(
            description="Exact client name, matched case-insensitively.",
        ),
    ] = None,
    status: Annotated[
        DashboardStatus | None,
        Query(description="Visible dashboard status."),
    ] = None,
):
    return _execute_query(
        lambda: dashboard_query_service.list_incidents(
            limit=limit,
            client=client,
            status=status,
        )
    )
