import json
import logging
import os

from datetime import datetime
from typing import cast

from avl2gtfsrt.avl.avlmatcher import AvlMatcher
from avl2gtfsrt.avl.spatialvector import SpatialVectorCollection
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

        # verify that the GNSS timestamp is not older than 60 seconds
        current_timestamp: int = unixtimestamp()    
        if timestamp < current_timestamp - 60:
            logging.warning(f"{self.__class__.__name__}: GNSS data update for vehicle {vehicle_ref} is older than 60 seconds and will be ignored.")

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
            gnss_vector: SpatialVectorCollection = SpatialVectorCollection(vehicle.activity.gnss_positions)

            # matching is only possible if the vehicle is moving
            # remember: we need at sequence of movement coordinates to match the trip!
            if gnss_vector.is_movement():

                # check if the vehicle is not operationally logged on
                # request all possible trip candidates in that case
                # otherwise check whether the vehicle is still on the trip which
                # was logged on before
                if not vehicle.is_operationally_logged_on:
                    logging.debug(f"{self.__class__.__name__} Vehicle {vehicle_ref} is not operationally logged on. Loading nominal trip candidates ...")

                    client: NominalDataClient = NominalDataClient(
                        os.getenv('A2G_NOMINAL_ADAPTER_TYPE'),
                        json.loads(os.getenv('A2G_NOMINAL_ADAPTER_CONFIG'))
                    )

                    trip_candidates: list[Trip] = client.get_trip_candidates(latitude, longitude)

                    matcher: AvlMatcher = AvlMatcher(
                        self._storage,
                        trip_candidates
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
                        [current_trip]
                    )

                    trip_matches: dict[str, bool] = matcher.test(
                        vehicle,
                        vehicle.activity.gnss_positions
                    )

                    # update vehicle activity ...                    
                    # if the trip matches, reset failure counter
                    # otherwise increment the counter
                    if trip_matches[current_trip_id]:
                        vehicle.activity.trip_candidate_failures = 0

                        trip_metrics: dict[TripMetrics] = matcher.predict_trip_metrics(
                            vehicle,
                            vehicle.activity.gnss_positions[-1]
                        )

                        vehicle.activity.trip_metrics = trip_metrics[current_trip_id]
                    else:
                        vehicle.activity.trip_candidate_failures = vehicle.activity.trip_candidate_failures + 1

                    self._storage.update_vehicle(vehicle)
                    
                    # if there're too many failures, perform a log off and delete trip descriptor
                    if vehicle.activity.trip_candidate_failures >= 4:
                        if vehicle.is_operationally_logged_on:
                            logging.info(f"{self.__class__.__name__}: Vehicle does not match its current trip anymore. Performing operational log off ...")
                            
                            vehicle.is_operationally_logged_on = False
                            vehicle.activity.trip_descriptor = None
                            vehicle.activity.trip_metrics = None

                            self._storage.update_vehicle(vehicle)
