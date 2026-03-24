from dataclasses import dataclass
from typing import Optional


@dataclass
class ZabbixEvent:
    host: str
    trigger: str
    severity: str
    status: int
    event_id: Optional[str] = None
    timestamp: Optional[str] = None
    duration: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            host=data.get("host"),
            trigger=data.get("trigger"),
            severity=data.get("severity"),
            status=data.get("status"),
            event_id=data.get("event_id"),
            timestamp=data.get("timestamp"),
            duration=data.get("duration"),
        )
