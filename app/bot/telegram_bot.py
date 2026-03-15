from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

from app.services.incident_service import IncidentService


incident_service = IncidentService()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hola. Soy el bot de NOC Automation.")


async def ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):

    response = incident_service.create_incident(
        summary="Test Incident from Telegram v 0.5",
        description="This ticket was created from the Telegram bot"
    )

    await update.message.reply_text(f"Ticket creado: {response['key']}")


def main():

    app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ticket", ticket))

    app.run_polling()


if __name__ == "__main__":
    main()
