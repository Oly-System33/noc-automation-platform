import time

from app.services.piru_client import PiruClient
from app.adapters.piru_event_adapter import adapt_piru_alert
from app.services.event_processor import processor
from app.rules.rule_engine import rule_engine


class PiruWatcher:

    def __init__(self, base_url: str, interval: int = 5):
        self.client = PiruClient(base_url)
        self.interval = interval
        self.processed_alerts = set()

    def run(self):

        print("Piru watcher iniciado... (Ctrl+C para salir)")

        try:

            while True:

                try:

                    alerts = self.client.get_active_alerts()

                    print(f"Alertas detectadas: {len(alerts)}")

                    for alert in alerts:

                        alert_id = alert["id"]

                        if alert_id in self.processed_alerts:
                            continue

                        print(f"[PIRU] Nueva alerta detectada: {alert_id}")

                        event = adapt_piru_alert(alert)

                        result = processor.process(event)

                        if result and result["type"] == "PROBLEM":

                            mensaje = rule_engine.evaluate_problem(
                                result["event"]
                            )

                            if mensaje:

                                self.client.add_action(alert_id, mensaje)

                            else:

                                self.client.ack_alert(alert_id)

                        else:

                            self.client.ack_alert(alert_id)

                        self.processed_alerts.add(alert_id)

                except Exception as e:

                    print(f"[ERROR][PIRU WATCHER] {e}")

                time.sleep(self.interval)

        except KeyboardInterrupt:

            print("\n[PIRU] Watcher detenido correctamente.\n")
