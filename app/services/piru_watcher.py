import time
from app.services.piru_client import PiruClient


class PiruWatcher:

    def __init__(self, base_url: str, token: str, interval: int = 5):
        self.client = PiruClient(base_url, token)
        self.interval = interval

    def run(self):

        print("Piru watcher iniciado...")

        processed_alerts = set()

        while True:

            alerts = self.client.get_active_alerts()

            print(f"Alertas detectadas: {len(alerts)}")

            for alert in alerts:

                alert_id = alert["id"]

                if alert_id in processed_alerts:
                    continue

                print(f"ACK alerta {alert_id}")

                self.client.ack_alert(alert_id)

                processed_alerts.add(alert_id)

            time.sleep(self.interval)
