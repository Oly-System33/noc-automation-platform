import requests
from typing import List, Dict


class PiruClient:

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def get_active_alerts(self) -> List[Dict]:
        """
        Obtiene alertas activas (EstadoID=0)
        """

        url = f"{self.base_url}/api/Alertas/Search?EstadoID=0"

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        payload = response.json()

        if payload.get("totalRecords", 0) == 0:
            return []

        return payload.get("data", [])

    def ack_alert(self, alert_id: int):

        url = f"{self.base_url}/api/Alertas/{alert_id}/ack"

        response = requests.put(
            url,
            headers=self.headers,
            json={"id": alert_id}
        )

        response.raise_for_status()

    def add_action(self, alert_id: int, message: str) -> None:
        """
        Registra acción externa (comentario operativo)
        """

        url = f"{self.base_url}/api/Acciones/Externa"

        body = {
            "alertaID": alert_id,
            "descripcion": message,
            "justificativoSla": None,
            "slaOk": "true"
        }

        response = requests.post(
            url,
            json=body,
            headers=self.headers
        )

        response.raise_for_status()
