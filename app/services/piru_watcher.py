import time

from app.services.piru_client import PiruClient
from app.adapters.piru_event_adapter import adapt_piru_alert
from app.services.event_processor import processor
from app.rules.rule_engine import rule_engine


class PiruWatcher:

    def __init__(self, base_url: str, interval: int = 5):

        self.client = PiruClient(base_url)
        self.interval = interval

        # deduplicación en memoria (una sola ejecución por alerta)
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

                        # evitar repetir ACK
                        if alert_id in self.processed_alerts:
                            continue

                        print(
                            f"[PIRU] Nueva alerta detectada: {alert_id}"
                        )

                        event = adapt_piru_alert(alert)

                        result = processor.process(event)

                        if result and result["type"] == "PROBLEM":

                            mensaje = rule_engine.evaluate_problem(
                                result["event"]
                            )

                            # ==========================
                            # ACK inmediato (siempre)
                            # ==========================

                            print(
                                f"[PIRU WATCHER] Ejecutando ACK alerta {alert_id}"
                            )

                            self.client.ack_alert(alert_id)

                            # ==========================
                            # acción externa solo si hay mensaje
                            # ==========================

                            if mensaje:

                                print(
                                    f"[PIRU WATCHER] Registrando acción externa alerta {alert_id}"
                                )

                                self.client.add_action(
                                    alert_id,
                                    mensaje
                                )

                            else:

                                print(
                                    f"[PIRU WATCHER] Sin mensaje runbook alerta {alert_id}"
                                )

                        else:

                            print(
                                f"[PIRU WATCHER] Evento ignorado {alert_id}"
                            )

                        # marcar alerta como procesada
                        self.processed_alerts.add(alert_id)

                except Exception as e:

                    print(f"[ERROR][PIRU WATCHER] {e}")

                time.sleep(self.interval)

        except KeyboardInterrupt:

            print("\n[PIRU] Watcher detenido correctamente.\n")
