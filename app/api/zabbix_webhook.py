from fastapi import APIRouter, Request
from app.models.event_model import ZabbixEvent
from app.services.event_processor import processor
from app.rules.rule_engine import rule_engine
from fastapi import BackgroundTasks

router = APIRouter()


@router.post("/zabbix/webhook")
async def zabbix_webhook(request: Request, background_tasks: BackgroundTasks):

    data = await request.json()

    print("\n========== RAW ZABBIX EVENT ==========")
    for k, v in data.items():
        print(f"{k}: {v}")
    print("======================================\n")

    event = ZabbixEvent.from_dict(data)

    result = processor.process(event)

    if result:

        if result["type"] == "PROBLEM":

            background_tasks.add_task(
                rule_engine.evaluate_problem,
                result["event"]
            )

        elif result["type"] == "RECOVERY":
            background_tasks.add_task(
                rule_engine.close_incident,
                result["event"],
                result["duration"]
            )

    return {"status": "ok"}
