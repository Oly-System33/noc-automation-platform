import requests
from typing import List, Dict


class PiruClient:

    def __init__(self, base_url: str, token: str):

        self.base_url = base_url

        self.session = requests.Session()

        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })

    def get_active_alerts(self) -> List[Dict]:
        """
        Obtiene alertas activas (EstadoID=0)
        """

        url = f"{self.base_url}/api/Alertas/Search?EstadoID=0"

        response = self.session.get(url)

        response.raise_for_status()

        payload = response.json()

        if payload.get("totalRecords", 0) == 0:
            return []

        return payload.get("data", [])

    def ack_alert(self, alert_id: int):

        url = f"{self.base_url}/api/Alertas/{alert_id}/ack"

        response = self.session.put(url)

        response.raise_for_status()

    def add_action(self, alert_id: int, message: str):

        url = f"{self.base_url}/api/Acciones/Externa"

        body = {
            "alertaID": alert_id,
            "descripcion": message,
            "tiempo": 5,
            "origen": 0,
            "fueraDeHora": True,
            "justificativoSla": None,
            "slaOk": True
        }

        print("[PIRU ACTION PAYLOAD]:", body)

        response = self.session.post(url, json=body)

        response.raise_for_status()

        print(f"[PIRU] Acción registrada correctamente para alerta {alert_id}")
