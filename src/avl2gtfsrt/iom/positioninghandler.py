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
from avl2gtfsrt.iom.basehandler import AbstractHandler
from avl2gtfsrt.model.types import Trip, GnssPosition, Vehicle, TripMetrics
from avl2gtfsrt.nominal.dataclient import NominalDataClient
from avl2gtfsrt.vdv.vdv435 import AbstractBasicStructure
from avl2gtfsrt.vdv.vdv435 import GnssPhysicalPositionDataStructure


class GnssPhysicalPositionHandler(AbstractHandler):

    def handle(self, topic: str, msg: AbstractBasicStructure) -> None:
        msg = cast(GnssPhysicalPositionDataStructure, msg)

        vehicle_ref: str = get_tls_value(topic, 'Vehicle')

        # verify that the vehicle is technically logged on
        vehicle: Vehicle = self._storage.get_vehicle(vehicle_ref)
        if vehicle is None or not vehicle.is_technically_logged_on:
            logging.error(f"Vehicle {vehicle_ref} is not technically logged on.")
            return

        # extract data from the message
        timestamp: int = int(datetime.fromisoformat(msg.timestamp_of_measurement).timestamp())
        latitude: float = msg.gnss_physical_position.wgs_84_physical_position.latitude
        longitude: float = msg.gnss_physical_position.wgs_84_physical_position.longitude

        # verify that the GNSS timestamp is not older than 150 seconds (2,5 minutes)
        current_timestamp: int = unixtimestamp()    
        if timestamp < current_timestamp - 150:
            logging.warning(f"{self.__class__.__name__}: GNSS data update for vehicle {vehicle_ref} is older than 150 seconds and will be ignored.")

            return

        # update vehicle activity data
        vehicle.activity.gnss_positions.append(GnssPosition(
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude
        ))

        self._storage.update_vehicle(vehicle)

        logging.info(f"{self.__class__.__name__}: Processed GNSS data update for vehicle {vehicle_ref} successfully.")

        # run all other processing steps
        
        # check whether AVL processing is enabled
        if len(vehicle.activity.gnss_positions) > 1:

            # matching is only possible if the vehicle is moving
            # remember: we need at sequence of movement coordinates to match the trip!
            # see #10: there's also a minimum interval for seconds required between each considered position
            # this is to prevent a system overload, when a device e.g. sends its position every second
            max_matching_interval: int = int(os.getenv('A2G_MATCHING_MAX_INTERVAL', '5'))
            if max_matching_interval > 0:
                matching_enabled: bool = False

                latest_gnss_timestamp: int = vehicle.activity.gnss_positions[-1].timestamp
                for p in reversed(vehicle.activity.gnss_positions):
                    current_gnss_timestamp: int = p.timestamp
                    if latest_gnss_timestamp - current_gnss_timestamp >= max_matching_interval:
                        matching_enabled = True
                        break
            else:
                matching_enabled: bool = True
            
            # run matching here ...
            gnss_vector: SpatialVectorCollection = SpatialVectorCollection(vehicle.activity.gnss_positions)
            if matching_enabled and gnss_vector.is_movement():

                # check if the vehicle is not operationally logged on
                # request all possible trip candidates in that case
                # otherwise check whether the vehicle is still on the trip which
                # was logged on before
                if not vehicle.is_operationally_logged_on:
                    logging.debug(f"{self.__class__.__name__} Vehicle {vehicle_ref} is not operationally logged on. Loading nominal trip candidates ...")

                    # load configured adapter and fetch trip candidates ...
                    adapter_type: str = os.getenv('A2G_NOMINAL_ADAPTER_TYPE', 'otp')
                    adapter_config: str = os.getenv('A2G_NOMINAL_ADAPTER_CONFIG', None)

                    if adapter_type not in ['otp']:
                        raise RuntimeError(f"Invalid nominal adapter type {adapter_type}. Please configure a valid adapter type.")

                    if adapter_config is None:
                        raise RuntimeError('Nominal adapter configuration is not set. Please set a valid adapter configuration.')
                    
                    client: NominalDataClient = NominalDataClient(
                        adapter_type,
                        json.loads(adapter_config)
                    )

                    trip_candidates: list[Trip]|None = client.get_trip_candidates(latitude, longitude)

                    # if trip candidates could not be loaded or list was empty, try to use cached trip candidates
                    if trip_candidates is None or len(trip_candidates) == 0:
                        trip_candidates = vehicle.cache.trip_candidates

                    # rund AVL matcher
                    matcher: AvlMatcher = AvlMatcher(
                        self._storage,
                        trip_candidates,
                        False
                    )
                    
                    result: tuple[bool, dict] = matcher.match(
                        vehicle, 
                        vehicle.activity.gnss_positions,
                        vehicle.activity.trip_candidate_probabilities
                    )

                    trip_candidate_convergence: bool = result[0]
                    trip_candidate_probabilities: dict = result[1]

                    # save trip candidate scores to vehicle activity
                    vehicle.activity.trip_candidate_convergence = trip_candidate_convergence
                    vehicle.activity.trip_candidate_probabilities = trip_candidate_probabilities

                    # save considered trip candidates to vehicle cache
                    vehicle.cache.trip_candidates = list()
                    for trip_candidate in trip_candidates:
                        if trip_candidate.descriptor.trip_id in trip_candidate_probabilities:
                            vehicle.cache.trip_candidates.append(trip_candidate)

                    # finally update all vehicle data
                    self._storage.update_vehicle(vehicle)

                    # return result
                    # (bool, (bool, object)) <--- (Success/Failure of the Handler, (TripConvergence, TripObject))
                    if trip_candidate_convergence:
                        trip_candidate_id: str = max(trip_candidate_probabilities, key=trip_candidate_probabilities.get)
                        trip_candidate: Trip|None = next((t for t in trip_candidates if t.descriptor.trip_id == trip_candidate_id), None)

                        if not vehicle.is_operationally_logged_on:
                            logging.info(f"{self.__class__.__name__}: Vehicle matched to trip {trip_candidate.descriptor.trip_id}. Performing operational log on ...")
                            
                            # update vehicle status and trip descriptor
                            vehicle.is_operationally_logged_on = True

                            vehicle.activity.trip_descriptor = trip_candidate.descriptor
                            
                            # predict trip metrics
                            trip_metrics: dict[TripMetrics] = matcher.predict_trip_metrics(
                                vehicle,
                                vehicle.activity.gnss_positions[-1]
                            )

                            vehicle.activity.trip_metrics = trip_metrics[trip_candidate_id]

                            # finally update vehicle data
                            self._storage.update_vehicle(vehicle)

                            self._storage.update_trip(trip_candidate)
                            
                else:
                    logging.debug(f"{self.__class__.__name__} Vehicle {vehicle_ref} is operationally logged on. Verifying current trip ...")
                    
                    current_trip_id: str = vehicle.activity.trip_descriptor.trip_id
                    current_trip: Trip = self._storage.get_trip(current_trip_id)

                    matcher: AvlMatcher = AvlMatcher(
                        self._storage,
                        [current_trip],
                        is_set('A2G_SHAPE_FILTER_ENABLED'),
                        int(os.getenv('A2G_SHAPE_FILTER_DISTANCE_METERS', '50'))
                    )

                    trip_matches: bool = matcher.test(
                        vehicle,
                        vehicle.activity.gnss_positions
                    )

                    # update vehicle activity ...                    
                    # if the trip matches, reset failure counter
                    # otherwise increment the counter
                    if trip_matches:
                        vehicle.activity.trip_candidate_failures = 0

                        trip_metrics: dict[TripMetrics] = matcher.predict_trip_metrics(
                            vehicle,
                            vehicle.activity.gnss_positions[-1]
                        )

                        vehicle.activity.trip_metrics = trip_metrics[current_trip_id]

                    else:
                        vehicle.activity.trip_candidate_failures = vehicle.activity.trip_candidate_failures + 1

                    # udpated GNSS position with filtered positon if shape filtering is enabled
                    if is_set('A2G_SHAPE_FILTER_ENABLED') and matcher.matched_vehicle_position is not None:
                        vehicle.activity.gnss_positions[-1] = matcher.matched_vehicle_position
                    
                    # if the vehicle arrived at the last stop of the journey, 
                    # perform a log off and delete trip descriptor
                    if vehicle.activity.trip_metrics.current_stop_is_final == True:
                        if vehicle.is_operationally_logged_on:
                            logging.info(f"{self.__class__.__name__}: Vehicle arrived at last stop. Performing operational log off ...")
                            
                            vehicle.is_operationally_logged_on = False
                            vehicle.activity.trip_descriptor = None
                            vehicle.activity.trip_metrics = None

                            # delete also GNSS position history in order to avoid a 
                            # re-assignment to the last trip with the next GNSS update, 
                            # when it has reached the final stop as indicated above
                            vehicle.activity.gnss_positions = []

                    # if there're too many failures, perform a log off and delete trip descriptor
                    max_failures: int = int(os.getenv('A2G_MATCHING_MAX_FAILURES', '5'))
                    if vehicle.activity.trip_candidate_failures >= max_failures:
                        if vehicle.is_operationally_logged_on:
                            logging.info(f"{self.__class__.__name__}: Vehicle does not match its current trip anymore. Performing operational log off ...")
                            
                            vehicle.is_operationally_logged_on = False
                            vehicle.activity.trip_descriptor = None
                            vehicle.activity.trip_metrics = None

                    # finally store updated vehicle data into the object storage
                    self._storage.update_vehicle(vehicle)
