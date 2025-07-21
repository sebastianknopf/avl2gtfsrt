import logging
import os

from datetime import datetime, timezone
from typing import cast

from itcs435.avl.avlmatcher import AvlMatcher
from itcs435.avl.spatialvector import SpatialVectorCollection
from itcs435.common.env import is_set
from itcs435.common.mqtt import get_tls_value
from itcs435.nominal.baseadapter import BaseNominalAdapter
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

        # extract data from the message
        timestamp: int = int(datetime.fromisoformat(msg.timestamp_of_measurement).timestamp())
        latitude: float = msg.gnss_physical_position.wgs_84_physical_position.latitude
        longitude: float = msg.gnss_physical_position.wgs_84_physical_position.longitude

        # update vehicle activity data
        vehicle_activity: dict = self._object_storage.get_vehicle_activity(vehicle_ref)
        if vehicle_activity is None:
            vehicle_activity = {
                'vehicle_ref': vehicle_ref,
                'gnss_positions': []
            }

        vehicle_activity['gnss_positions'].append({
            'timestamp': timestamp,
            'latitude': latitude,
            'longitude': longitude
        })

        self._object_storage.update_vehicle_activity(vehicle_ref, vehicle_activity)

        if len(vehicle_activity['gnss_positions']) > 1:
            activity: SpatialVectorCollection = SpatialVectorCollection(vehicle_activity['gnss_positions'])

            # check whether nominal caching is enabled
            # alternative: check whether AVL processing is enabled as AVL processing requires 
            # nominal trips cached
            if is_set('ITCS435_NOMINAL_CACHING_ENABLED') or is_set('ITCS435_AVL_PROCESSING_ENABLED'):
                
                # only proceed if the vehicle is standing at a station actually
                # assumption: the vehicle waits for the departure time
                if activity.is_movement():
                    adapter: BaseNominalAdapter = None
                    
                    adapter_type: str = os.getenv('ITCS435_NOMINAL_ADAPTER_TYPE', 'otp')
                    if adapter_type == 'otp':
                        from itcs435.nominal.otp.adapter import OtpAdapter
                        adapter = OtpAdapter()
                    else:
                        raise ValueError(f"Unknown nominal adapter type {adapter_type}!")
                    
                    try:
                        logging.info(f"Running nominal adapter {adapter_type} ...")
                        adapter.cache_trip_candidates_by_position(latitude, longitude)
                    except Exception as ex:
                        if is_set('ITCS435_DEBUG'):
                            logging.exception(ex)
                        else:
                            logging.error(str(ex))

            # check whether AVL processing is enabled and process position data
            if is_set('ITCS435_AVL_PROCESSING_ENABLED'):
                matcher: AvlMatcher = AvlMatcher(self._object_storage.get_vehicles())
                matcher.process(vehicle, vehicle_activity['gnss_positions'])
