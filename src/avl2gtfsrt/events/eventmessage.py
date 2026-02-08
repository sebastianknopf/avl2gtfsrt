import json

from datetime import datetime, timezone


class EventMessage:

    TECHNICAL_VEHICLE_LOG_ON: int = 0
    TECHNICAL_VEHICLE_LOG_OFF: int = 1
    OPERATIONAL_VEHICLE_LOG_ON: int = 2
    OPERATIONAL_VEHICLE_LOG_OFF: int = 3
    GNSS_PHYSICAL_POSITION_UPDATE: int = 4

    def __init__(self, event_type: int, vehicle_id: str) -> None:
        self.event_type: int = event_type
        self.vehicle_id: str = vehicle_id
        self.timestamp: int = int(datetime.now(timezone.utc).timestamp())

    def __str__(self) -> str:
        event_data: dict = {
            'event_type': self.event_type,
            'vehicle_id': self.vehicle_id,
            'timestamp': self.timestamp
        }

        event_json: str = json.dumps(event_data)

        return event_json