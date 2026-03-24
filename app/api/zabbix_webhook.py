from fastapi import APIRouter, Request
from app.models.event_model import ZabbixEvent
from app.services.event_processor import processor

router = APIRouter()


@router.post("/zabbix/webhook")
async def zabbix_webhook(request: Request):
    data = await request.json()

    event = ZabbixEvent.from_dict(data)

    result = processor.process(event)

    if result:
        print("Evento procesado:", result["type"])

    return {"status": "ok"}
