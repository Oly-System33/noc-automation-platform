import time

from app.services.piru_client import PiruClient
from app.adapters.piru_event_adapter import adapt_piru_alert
from app.services.event_processor import processor
from app.rules.rule_engine import rule_engine


class PiruWatcher:

    def __init__(self, base_url: str, token: str, interval: int = 5):
        self.client = PiruClient(base_url, token)
        self.interval = interval
        self.processed_alerts = set()

    def run(self):

        print("Piru watcher iniciado...")

        while True:

            try:

                alerts = self.client.get_active_alerts()

                print(f"Alertas detectadas: {len(alerts)}")

                for alert in alerts:

                    alert_id = alert["id"]

                    # deduplicación
                    if alert_id in self.processed_alerts:
                        continue

                    print(f"[PIRU] Nueva alerta detectada: {alert_id}")

                    # adaptar alerta PIRU → ZabbixEvent
                    event = adapt_piru_alert(alert)

                    # pasar por correlador interno
                    result = processor.process(event)

                    if result and result["type"] == "PROBLEM":

                        print(
                            f"[PIRU] Evaluando reglas para evento {alert_id}"
                        )

                        mensaje = rule_engine.evaluate_problem(
                            result["event"]
                        )

                        print("MENSAJE RUNBOOK:", mensaje)

                        # si hay mensaje → acción externa (cierra alerta)
                        if mensaje:

                            self.client.add_action(alert_id, mensaje)

                        # si no hay mensaje → solo ACK
                        else:

                            print(f"[PIRU] ACK alerta {alert_id}")

                            self.client.ack_alert(alert_id)

                    # marcar como procesada
                    self.processed_alerts.add(alert_id)

            except Exception as e:

                print(f"[ERROR][PIRU WATCHER] {e}")

            time.sleep(self.interval)
