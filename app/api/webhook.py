from fastapi import FastAPI, Request, BackgroundTasks
from app.services.incident_service import IncidentService
import requests
import os
import time


app = FastAPI()

incident_service = IncidentService()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
session = requests.Session()


def send_message(chat_id, text):

    session.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text
        },
        timeout=5
    )


def process_ticket(chat_id):

    start = time.time()
    print("Starting ticket creation")

    response = incident_service.create_incident(
        summary="Test Incident from Webhook",
        description="Created through webhook"
    )

    print("Jira response time:", time.time() - start)

    ticket_key = response["key"]

    start_msg = time.time()

    send_message(chat_id, f"Ticket creado: {ticket_key}")

    print("Telegram message time:", time.time() - start_msg)


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
