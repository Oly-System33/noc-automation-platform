from dataclasses import dataclass
from typing import Optional


@dataclass
class ZabbixEvent:
    host: str
    hostgroup: str
    trigger: str
    severity: str
    event_id: Optional[str] = None
    timestamp: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            host=data.get("host"),
            hostgroup=data.get("hostgroup"),
            trigger=data.get("trigger"),
            severity=data.get("severity"),
            event_id=data.get("event_id"),
            timestamp=data.get("timestamp"),
        )
