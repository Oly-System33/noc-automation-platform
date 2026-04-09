import requests
import json
from typing import List, Dict
from playwright.sync_api import sync_playwright
import os
from app.services.save_piru_session import main as save_session


class PiruClient:

    def __init__(self, base_url: str, storage_path: str = "piru_storage.json"):

        self.base_url = base_url
        self.storage_path = storage_path

        self.session = requests.Session()
        if not os.path.exists(self.storage_path):

            print("[PIRU] storage_state no encontrado. Iniciando login inicial...")

            save_session()
        # cargar cookies + capturar token backend
        self._bootstrap_session()

    # ==============================
    # SESSION BOOTSTRAP
    # ==============================

    def _bootstrap_session(self):

        print("[PIRU] Inicializando sesión desde storage_state...")

        token_holder = {"token": None}

        def capture_request(request):

            if "/api/" not in request.url:
                return

            auth = request.headers.get("authorization")

            if auth and "Bearer " in auth:

                token_holder["token"] = auth.split("Bearer ")[1]

        with sync_playwright() as p:

            browser = p.chromium.launch(headless=True)

            context = browser.new_context(
                storage_state=self.storage_path
            )

            page = context.new_page()

            page.on("request", capture_request)

            page.goto(self.base_url)

            page.wait_for_timeout(6000)

            browser.close()

        token = token_holder["token"]

        if not token:
            raise Exception("No se pudo capturar token backend PIRU")

        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })

        print("[PIRU] Token backend capturado correctamente")

    # ==============================
    # API METHODS
    # ==============================

    def get_active_alerts(self) -> List[Dict]:

        url = f"{self.base_url}/api/Alertas/Search?EstadoID=0"

        response = self.session.get(url)

        if response.status_code == 401:
            raise Exception("Sesión PIRU expirada")

        response.raise_for_status()

        payload = response.json()

        if payload.get("totalRecords", 0) == 0:
            return []

        return payload.get("data", [])

    def ack_alert(self, alert_id: int):

        url = f"{self.base_url}/api/Alertas/{alert_id}/ack"

        response = self.session.put(url)

        if response.status_code == 204:

            print(f"[PIRU] ACK exitoso alerta {alert_id}")

        elif response.status_code == 400:

            print(
                f"[PIRU] ACK ignorado (ya estaba confirmado) alerta {alert_id}"
            )

        elif response.status_code == 401:

            raise Exception("Sesión PIRU expirada")

        else:

            print(
                f"[PIRU] ACK error inesperado {response.status_code}: "
                f"{response.text}"
            )

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

        response = self.session.post(url, json=body)

        if response.status_code == 401:
            raise Exception("Sesión PIRU expirada")

        response.raise_for_status()

        print(f"[PIRU] Acción registrada correctamente para alerta {alert_id}")
