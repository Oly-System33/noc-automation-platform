from fastapi import FastAPI

from app.api.vonage_webhook import router as vonage_router
from app.api.zabbix_webhook import router as zabbix_router
from app.services.scheduled_action_worker import (
    is_worker_enabled,
    start_background_worker,
    stop_background_worker,
)

app = FastAPI()

app.include_router(zabbix_router)
app.include_router(vonage_router)


@app.on_event("startup")
def start_scheduled_action_worker():
    if is_worker_enabled():
        start_background_worker()


@app.on_event("shutdown")
def stop_scheduled_action_worker():
    stop_background_worker()
