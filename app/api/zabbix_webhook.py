from fastapi import APIRouter, Request
from app.models.event_model import ZabbixEvent

router = APIRouter()


@router.post("/zabbix/webhook")
async def zabbix_webhook(request: Request):
    data = await request.json()

    event = ZabbixEvent.from_dict(data)

    print("Evento recibido:")
    print(event)

    return {"status": "ok"}
