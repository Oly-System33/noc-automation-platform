from app.models.event_model import ZabbixEvent


def adapt_piru_alert(alert: dict) -> ZabbixEvent:

    host = alert["host"]["nombreVisible"]

    trigger = alert.get("problema", "unknown")

    severity_map = {
        5: "CRITICAL",
        4: "HIGH",
        3: "MEDIUM",
        2: "WARNING",
        1: "INFO"
    }

    severity = severity_map.get(alert.get("gravedad"), "UNKNOWN")

    status_map = {
        0: "PROBLEM",
        3: "PROBLEM"
    }

    status = status_map.get(alert.get("estado"), "PROBLEM")

    return ZabbixEvent(
        host=host,
        trigger=trigger,
        severity=severity,
        status=status,
        event_id=str(alert["id"]),
        timestamp=alert.get("fecha"),
        duration=None
    )
