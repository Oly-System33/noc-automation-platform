from app.services.conversation_manager import conversation_manager
from app.services.incident_service import IncidentService

incident_service = IncidentService()


PROJECTS = {
    "Banco X": "BX",
    "Banco X SOC": "BXSOC"
}

CATEGORIES = [
    "Soporte",
    "Consultoría",
    "Accesos Jira"
]

PRIORITIES = [
    "🔴 Crítico",
    "🟠 Alto",
    "🟡 Medio",
    "🟢 Bajo"
]


def start_ticket(user_id, send_message):

    conversation_manager.start(user_id)

    keyboard = [[p] for p in PROJECTS.keys()]

    send_message(
        user_id,
        "Selecciona el proyecto",
        keyboard
    )


def handle_message(user_id, text, send_message):

    conv = conversation_manager.get(user_id)

    if not conv:
        return

    state = conv["state"]

    if state == "SELECT_PROJECT":

        if text not in PROJECTS:

            keyboard = [[p] for p in PROJECTS.keys()]

            send_message(
                user_id,
                "Selecciona un proyecto válido",
                keyboard
            )
            return

        conversation_manager.update_data(user_id, "project_name", text)
        conversation_manager.update_data(
            user_id, "project_key", PROJECTS[text])
        conversation_manager.update_state(user_id, "SELECT_CATEGORY")

        keyboard = [[c] for c in CATEGORIES]

        send_message(
            user_id,
            "Selecciona la categoría",
            keyboard
        )

    elif state == "SELECT_CATEGORY":

        if text not in CATEGORIES:

            keyboard = [[c] for c in CATEGORIES]

            send_message(
                user_id,
                "Selecciona una categoría válida",
                keyboard
            )
            return

        conversation_manager.update_data(user_id, "category", text)
        conversation_manager.update_state(user_id, "WRITE_SUMMARY")

        send_message(
            user_id,
            "Describe brevemente el problema"
        )

    elif state == "WRITE_SUMMARY":

        if not text.strip():

            send_message(
                user_id,
                "El título no puede estar vacío. Describe brevemente el problema."
            )
            return

        conversation_manager.update_data(user_id, "summary", text)
        conversation_manager.update_state(user_id, "WRITE_DESCRIPTION")

        send_message(
            user_id,
            "Describe el problema con más detalle"
        )

    elif state == "WRITE_DESCRIPTION":

        if not text.strip():

            send_message(
                user_id,
                "El título no puede estar vacío. Describe brevemente el problema."
            )
            return

        conversation_manager.update_data(user_id, "description", text)
        conversation_manager.update_state(user_id, "SELECT_PRIORITY")

        keyboard = [[p] for p in PRIORITIES]

        send_message(
            user_id,
            "Selecciona prioridad",
            keyboard
        )

    elif state == "SELECT_PRIORITY":

        if text not in PRIORITIES:

            keyboard = [[p] for p in PRIORITIES]

            send_message(
                user_id,
                "Selecciona una prioridad válida",
                keyboard
            )
            return

        conversation_manager.update_data(user_id, "priority", text)

        data = conversation_manager.get(user_id)["data"]

        description = f"""
Cliente: {data['project_name']}
Categoría: {data['category']}
Prioridad: {data['priority']}

Título:
{data['summary']}

Detalle:
{data['description']}
"""

        response = incident_service.create_incident(
            project_key=data["project_key"],
            summary=data["summary"],
            description=description
        )

        if "key" not in response:
            send_message(
                user_id,
                "❌ No se pudo crear el ticket. Intenta nuevamente o contacte al NOC."
            )
            print("Jira error response:", response)
            conversation_manager.end(user_id)
            return

        ticket_key = response["key"]

        send_message(
            user_id,
            f"""✅ Ticket creado correctamente

Cliente: {data['project_name']}
Categoría: {data['category']}
Prioridad: {data['priority']}

Título: {data['summary']}

ID: {ticket_key}"""
        )

        conversation_manager.end(user_id)
