from fastapi import FastAPI, Request, BackgroundTasks
from app.services.incident_service import IncidentService
import requests
import os

app = FastAPI()

incident_service = IncidentService()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def process_ticket(chat_id):

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": "hola prueba"
        }
    )


@app.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):

    data = await request.json()

    message = data.get("message", {})
    text = message.get("text", "")
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if text == "/ticket":
        background_tasks.add_task(process_ticket, chat_id)

    return {"status": "ok"}
