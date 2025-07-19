import logging

from datetime import datetime, timezone
from typing import cast

from itcs435.common.mqtt import get_tls_value
from itcs435.vdv.vdv435 import AbstractBasicStructure
from itcs435.vdv.vdv435 import GnssPhysicalPositionDataStructure
from itcs435.iom.basehandler import AbstractHandler

class GnssPhysicalPositionHandler(AbstractHandler):

    def handle(self, topic: str, msg: AbstractBasicStructure) -> None:
        msg = cast(GnssPhysicalPositionDataStructure, msg)

        vehicle_ref: str = get_tls_value(topic, 'Vehicle')

        # verify that the vehicle is technically logged on
        vehicle: dict = self._object_storage.get_vehicle(vehicle_ref)
        if vehicle is None or not vehicle.get('is_technically_logged_on', False):
            raise RuntimeError(f"Vehicle {vehicle_ref} is not technically logged on")

        # update vehicle position data
        vehicle_position: dict = self._object_storage.get_vehicle_position(vehicle_ref)
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

        self._object_storage.update_vehicle_position(vehicle_ref, vehicle_position)