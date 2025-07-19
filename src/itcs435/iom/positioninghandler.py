import logging

from datetime import datetime, timezone
from typing import cast

from itcs435.common.mqtt import get_tls_value
from itcs435.vdv.vdv435 import AbstractBasicStructure
from itcs435.vdv.vdv435 import GnssPhysicalPositionDataStructure
from itcs435.iom.basehandler import AbstractHandler

class GnssPhysicalPositionHandler(AbstractHandler):

    def handle(self, topic: str, msg: AbstractBasicStructure) -> None:
        # Cast the message to the specific type if needed
        msg = cast(GnssPhysicalPositionDataStructure, msg)

        # process the physical position data
        vehicle_ref = get_tls_value(topic, 'Vehicle')

        vehicle_position: dict = self._storage.get_vehicle_position(vehicle_ref)
        if vehicle_position is None:
            vehicle_position = {
                'vehicle_ref': vehicle_ref,
                'gnss_positions': []
            }

        timestamp: int = int(datetime.fromisoformat(msg.timestamp_of_measurement).timestamp())
        latitude: float = msg.gnss_physical_position.wgs_84_physical_position.latitude
        longitude: float = msg.gnss_physical_position.wgs_84_physical_position.longitude

        vehicle_position['gnss_positions'].append({
            'timestamp': timestamp,
            'latitude': latitude,
            'longitude': longitude
        })

        self._storage.update_vehicle_position(vehicle_ref, vehicle_position)