from fastapi import FastAPI

from app.api.vonage_webhook import router as vonage_router
from app.api.zabbix_webhook import router as zabbix_router

app = FastAPI()

app.include_router(zabbix_router)
app.include_router(vonage_router)
