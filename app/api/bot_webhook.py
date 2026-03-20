from fastapi import APIRouter, Request
from app.bot.ticket_flow import start_ticket, handle_message
from app.services.conversation_manager import conversation_manager
import requests
import os

router = APIRouter()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

session = requests.Session()


def send_message(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        payload["reply_markup"] = {
            "keyboard": keyboard,
            "resize_keyboard": True,
            "one_time_keyboard": True
        }

    session.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json=payload,
        timeout=5
    )


@router.post("/bot/webhook")
async def telegram_webhook(request: Request):

    data = await request.json()

    message = data.get("message", {})
    text = message.get("text", "")
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if text == "/ticket":
        start_ticket(chat_id, send_message)

    elif text == "/cancel":
        conversation_manager.end(chat_id)
        send_message(chat_id, "❌ Operación cancelada.")

    else:
        handle_message(chat_id, text, send_message)

    return {"status": "ok"}
