from datetime import datetime, timedelta
from typing import Optional


def parse_timestamp(value: str) -> Optional[datetime]:
    """
    Convierte timestamp recibido desde Zabbix a datetime.

    Soporta:
    - epoch (int o string)
    - HH:MM:SS
    - ignora macros sin resolver ({EVENT.X})
    """

    if value is None:
        return None

    value = str(value).strip()

    # ignorar macros sin resolver
    if value.startswith("{") and value.endswith("}"):
        return None

    # intentar epoch
    if value.isdigit():
        return datetime.fromtimestamp(int(value))

    # intentar HH:MM:SS
    try:
        return datetime.strptime(value, "%H:%M:%S")
    except ValueError:
        return None
