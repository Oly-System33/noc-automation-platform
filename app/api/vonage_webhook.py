import os

from dotenv import load_dotenv
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.services.call_service import call_service
from app.services.console import console


router = APIRouter()


def _get_public_base_url():
    load_dotenv()

    public_base_url = os.getenv("PUBLIC_BASE_URL")

    if not public_base_url:
        raise ValueError("PUBLIC_BASE_URL is required for Vonage input webhook")

    return public_base_url.rstrip("/")


def _build_answer_ncco(event_id):
    message = call_service.get_message(event_id)
    input_url = f"{_get_public_base_url()}/vonage/input?event_id={event_id}"

    return [
        {
            "action": "talk",
            "text": message,
            "language": "es-MX",
            "bargeIn": True,
        },
        {
            "action": "talk",
            "text": (
                "Presione 1 para confirmar recepción. "
                "Presione 2 para repetir el mensaje."
            ),
            "language": "es-MX",
            "bargeIn": True,
        },
        {
            "action": "input",
            "type": ["dtmf"],
            "dtmf": {
                "maxDigits": 1,
                "timeOut": 10,
            },
            "eventUrl": [input_url],
            "eventMethod": "POST",
        },
    ]


def _build_invalid_option_ncco(event_id):
    return [
        {
            "action": "talk",
            "text": (
                "Opción inválida. Presione 1 para confirmar "
                "o 2 para repetir el mensaje."
            ),
            "language": "es-MX",
            "bargeIn": True,
        },
        *_build_answer_ncco(event_id),
    ]


def _extract_digit(payload):
    dtmf = payload.get("dtmf")

    if isinstance(dtmf, dict):
        digits = dtmf.get("digits")

        if digits:
            return str(digits)

    if payload.get("digits"):
        return str(payload.get("digits"))

    if dtmf:
        return str(dtmf)

    return None


@router.get("/vonage/answer")
async def vonage_answer(event_id: str = Query(...)):
    print(
        f"[CALL] Speech reproducido con barge-in habilitado | "
        f"event_id={event_id}"
    )
    return JSONResponse(content=_build_answer_ncco(event_id))


@router.post("/vonage/input")
async def vonage_input(request: Request, event_id: str = Query(...)):
    payload = await request.json()
    digit = _extract_digit(payload)

    print(f"[CALL] DTMF recibido | event_id={event_id} | opción={digit}")

    if digit == "1":
        call_service.mark_confirmed(event_id)
        print(
            f"[CALL] {console.green('Confirmación recibida')} | "
            f"event_id={event_id} | opción=1"
        )

        return JSONResponse(
            content=[
                {
                    "action": "talk",
                    "text": "Mensaje confirmado. Muchas gracias.",
                    "language": "es-MX",
                }
            ]
        )

    if digit == "2":
        print(
            f"[CALL] {console.cyan('Repetición solicitada')} | "
            f"event_id={event_id} | opción=2"
        )
        return JSONResponse(content=_build_answer_ncco(event_id))

    print(
        f"[CALL] {console.yellow('Opción inválida')} | "
        f"event_id={event_id} | opción={digit}"
    )
    return JSONResponse(content=_build_invalid_option_ncco(event_id))


@router.post("/vonage/event")
async def vonage_event(request: Request, event_id: str = Query(...)):
    payload = await request.json()
    summary_keys = [
        "uuid",
        "conversation_uuid",
        "status",
        "direction",
        "timestamp",
    ]
    summary = {
        key: payload.get(key)
        for key in summary_keys
        if key in payload
    }
    call_service.update_call_event(event_id, payload)

    status = str(summary.get("status", "")).lower()

    if status in ("failed", "busy", "timeout", "rejected", "unanswered"):
        status_text = console.orange(status or "unknown")
    elif status in ("answered", "completed"):
        status_text = console.cyan(status)
    elif status in ("ringing", "started"):
        status_text = console.cyan(status)
    else:
        status_text = status or "unknown"

    print(
        f"[VONAGE][EVENT] event_id={event_id} | "
        f"status={status_text} | payload={summary}"
    )

    return {"status": "ok"}
