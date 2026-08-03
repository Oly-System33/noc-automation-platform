import logging
from datetime import datetime
from typing import Annotated, Callable

from fastapi import APIRouter, HTTPException, Query

from app.schemas.operational import (
    AuditLogListResponse,
    OperationalConfigurationResponse,
    OperationalErrorResponse,
)
from app.services.operational_query_service import (
    OperationalQueryError,
    operational_query_service,
)


logger = logging.getLogger(__name__)
audit_router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])
configuration_router = APIRouter(prefix="/api/configuration", tags=["configuration"])
ERROR_RESPONSES = {
    503: {"model": OperationalErrorResponse, "description": "Operational data is temporarily unavailable"},
    500: {"model": OperationalErrorResponse, "description": "Unexpected internal error"},
}


def _execute(operation: Callable):
    try:
        return operation()
    except OperationalQueryError:
        raise HTTPException(status_code=503, detail="Operational data is temporarily unavailable") from None
    except Exception as error:
        logger.error("Unexpected operational API error: %s", type(error).__name__)
        raise HTTPException(status_code=500, detail="Internal server error") from None


@audit_router.get("", response_model=AuditLogListResponse, responses=ERROR_RESPONSES, summary="List safe audit logs")
def list_audit_logs(
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(max_length=200)] = None,
    level: Annotated[str | None, Query(max_length=50)] = None,
    component: Annotated[str | None, Query(max_length=100)] = None,
    event_id: Annotated[str | None, Query(max_length=200)] = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
):
    return _execute(lambda: operational_query_service.list_audit_logs(
        limit=limit, offset=offset, search=search, level=level,
        component=component, event_id=event_id, created_from=created_from,
        created_to=created_to,
    ))


@configuration_router.get(
    "/operational", response_model=OperationalConfigurationResponse,
    responses=ERROR_RESPONSES, summary="Get safe operational configuration",
)
def get_operational_configuration():
    return _execute(operational_query_service.get_configuration)
