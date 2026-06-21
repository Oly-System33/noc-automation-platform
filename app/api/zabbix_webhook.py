from fastapi import APIRouter, Request
from app.models.event_model import ZabbixEvent
from app.services.event_processor import processor
from app.rules.rule_engine import rule_engine
from app.services.console import console
from fastapi import BackgroundTasks

router = APIRouter()


SENSITIVE_KEYS = ("token", "password", "secret", "api_key", "apikey", "key")


def _safe_console_value(key, value):
    key = str(key).lower()

    if any(sensitive_key in key for sensitive_key in SENSITIVE_KEYS):
        return "***redacted***"

    return value


@router.post("/zabbix/webhook")
async def zabbix_webhook(request: Request, background_tasks: BackgroundTasks):

    data = await request.json()

    print("\n" + console.cyan("========== RAW ZABBIX EVENT =========="))
    for k, v in data.items():
        value = _safe_console_value(k, v)

        if k == "status":
            print(f"{k}: {console.status(value)}")
        elif k == "severity":
            print(f"{k}: {console.status(value)}")
        else:
            print(f"{k}: {value}")
    print(console.cyan("======================================") + "\n")

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
