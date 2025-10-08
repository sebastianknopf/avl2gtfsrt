import json
import logging
import os

from datetime import datetime
from typing import cast

from avl2gtfsrt.avl.avlmatcher import AvlMatcher
from avl2gtfsrt.avl.spatialvector import SpatialVectorCollection
from avl2gtfsrt.common.env import is_set
from avl2gtfsrt.common.mqtt import get_tls_value
from avl2gtfsrt.common.shared import unixtimestamp
from avl2gtfsrt.vdv.vdv435 import AbstractBasicStructure
from avl2gtfsrt.vdv.vdv435 import GnssPhysicalPositionDataStructure
from avl2gtfsrt.iom.basehandler import AbstractHandler
from avl2gtfsrt.nominal.dataclient import NominalDataClient

class GnssPhysicalPositionHandler(AbstractHandler):

    def handle(self, topic: str, msg: AbstractBasicStructure) -> None:
        msg = cast(GnssPhysicalPositionDataStructure, msg)

        vehicle_ref: str = get_tls_value(topic, 'Vehicle')

        # verify that the vehicle is technically logged on
        vehicle: dict = self._object_storage.get_vehicle(vehicle_ref)
        if vehicle is None or not vehicle.get('is_technically_logged_on', False):
            logging.error(f"Vehicle {vehicle_ref} is not technically logged on.")
            return

        # extract data from the message
        timestamp: int = int(datetime.fromisoformat(msg.timestamp_of_measurement).timestamp())
        latitude: float = msg.gnss_physical_position.wgs_84_physical_position.latitude
        longitude: float = msg.gnss_physical_position.wgs_84_physical_position.longitude

        # verify that the GNSS timestamp is not older than 60 seconds
        current_timestamp: int = unixtimestamp()    
        if timestamp < current_timestamp - 60:
            logging.warning(f"{self.__class__.__name__}: GNSS data update for vehicle {vehicle_ref} is older than 60 seconds and will be ignored.")

            return

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

        logging.info(f"{self.__class__.__name__}: Processed GNSS data update for vehicle {vehicle_ref} successfully.")

        # run all other processing steps
        
        # check whether AVL processing is enabled
        if len(vehicle_activity['gnss_positions']) > 1:
            activity: SpatialVectorCollection = SpatialVectorCollection(vehicle_activity['gnss_positions'])

            # matching is only possible if the vehicle is moving
            # remember: we need at sequence of movement coordinates to match the trip!
            if activity.is_movement():

                # check if the vehicle is not operationally logged on
                # request all possible trip candidates in that case
                # otherwise use the cached trip candidates
                if not vehicle.get('is_operationally_logged_on', False):
                    logging.debug(f"{self.__class__.__name__} Vehicle {vehicle_ref} is not operationally logged on. Loading nominal trip candidates ...")

                    client: NominalDataClient = NominalDataClient(
                        os.getenv('A2G_NOMINAL_ADAPTER_TYPE'),
                        json.loads(os.getenv('A2G_NOMINAL_ADAPTER_CONFIG'))
                    )

                    trip_candidates: list[dict] = client.get_trip_candidates(latitude, longitude)
                else:
                    trip_candidates: list[dict]|None = None

                matcher: AvlMatcher = AvlMatcher(
                    self._object_storage.get_vehicles(),
                    trip_candidates
                )
                
                result: tuple[bool, dict] = matcher.process(
                    vehicle, 
                    vehicle_activity['gnss_positions'],
                    vehicle_activity.get('trip_candidate_probabilities', None)
                )

                trip_candidate_found: bool = result[0]
                trip_candidate_probabilities: dict = result[1]

                # save trip candidate scores to vehicle activity
                vehicle_activity['trip_candidate_probabilities'] = trip_candidate_probabilities
                self._object_storage.update_vehicle_activity(vehicle_ref, vehicle_activity)
