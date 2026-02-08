import logging
import polyline

from shapely.geometry import LineString, Point, Polygon
from time import time

from avl2gtfsrt.avl.spatialmatch import SpatialMatch
from avl2gtfsrt.avl.temporalmatch import TemporalMatch
from avl2gtfsrt.avl.spatialvector import SpatialVectorCollection
from avl2gtfsrt.common.shared import web_mercator, wgs_84
from avl2gtfsrt.common.statistics import bayesian_update
from avl2gtfsrt.model.types import Vehicle, GnssPosition, Trip, TripMetrics
from avl2gtfsrt.objectstorage import ObjectStorage

class AvlMatcher:

    def __init__(self, object_storage: ObjectStorage, trip_candidates: list[Trip], shape_filter_enabled: bool = True, shape_filter_distance_meters: int = 50) -> None:
        self._storage = object_storage
        self._trip_candidates = trip_candidates

        self._shape_filter_enabled = shape_filter_enabled
        self._shape_filter_distance_meters = shape_filter_distance_meters

        self.matched_vehicle_position: GnssPosition|None = None

    def match(self, vehicle: Vehicle, gnss_positions: list[GnssPosition], last_trip_candidate_probabilities: dict|None) -> tuple[bool, dict]:
        if len(self._trip_candidates) > 0:
            logging.info(f"{self.__class__.__name__}: Matching AVL data for vehicle {vehicle.vehicle_ref} with {len(self._trip_candidates)} possible trip candidates ...")
            start_time: float = time()

            if len(gnss_positions) > 1:
                movement: SpatialVectorCollection = SpatialVectorCollection(gnss_positions)

                trip_candidate_scores: dict[str, float] = dict()
                for trip_candidate in self._trip_candidates:

                    # check for prerequisites

                    # check whether another vehicle has logged on this trip
                    # skip the ressource-consuming matching in that case and skip the candidate
                    if any(
                        v.activity is not None
                        and v.activity.trip_descriptor is not None 
                        and v.activity.trip_descriptor.trip_id == trip_candidate.descriptor.trip_id
                        for v in self._storage.get_vehicles()
                    ):
                        continue
                    
                    # match trip candidate for scoring
                    # 1. step: spatial matching
                    # 2. step: temporal matching

                    # generate LineString in web-mercator projection for spatial and temporal matching
                    trip_shape: LineString = LineString([c[::-1] for c in polyline.decode(trip_candidate.shape_polyline)])
                    trip_shape = web_mercator(trip_shape)

                    # run spatial matching for trip candidate
                    spatial_match: SpatialMatch = SpatialMatch(trip_shape)
                    spatial_match_score: float = spatial_match.calculate_match_score(movement)
                    if spatial_match_score == 0.0:
                        continue

                    # run temporal matching for trip candidate
                    temporal_match: TemporalMatch = TemporalMatch(
                        trip_candidate.stop_times, 
                        trip_shape
                    )

                    temporal_match_score: float = temporal_match.calculate_match_score(spatial_match.spatial_progress_percentage)
                    if temporal_match_score == 0.0:
                        continue

                    # finally calculate trip candidate score and store it for this iteration
                    trip_candidate_score: float = spatial_match_score * temporal_match_score
                    trip_candidate_scores[trip_candidate.descriptor.trip_id] = trip_candidate_score
                
                # log if all trips have been discarded
                # in this case, the process function is done at all
                if len(trip_candidate_scores) == 0:
                    logging.warning(f"{self.__class__.__name__}: All trip candidates have been discarded due to logical or spatial, temporal mismatch.")

                    # no convergence and no candidates ...
                    return (False, dict())

                # check if there was an update yet
                # run bayesian update in order to manifest the trip scores
                # if there was no last update yet, run with prior == likelihood
                # the bayesian update function returns also, whether the best trip candidate is 
                # surely matched
                if last_trip_candidate_probabilities is not None:
                    bayesian_result: tuple[bool, dict] = bayesian_update(
                        last_trip_candidate_probabilities,
                        trip_candidate_scores
                    )

                    trip_candidate_convergence: bool = bayesian_result[0]
                    trip_candidate_probabilities: dict = bayesian_result[1]
                else:
                    bayesian_result: tuple[bool, dict] = bayesian_update(
                        {k: [v] for k, v in trip_candidate_scores.items()},
                        trip_candidate_scores
                    )

                    trip_candidate_convergence: bool = bayesian_result[0]
                    trip_candidate_probabilities: dict = bayesian_result[1]

                # stop time elapsed and print scored trip candidates
                end_time: float = time()
                logging.info(f"{self.__class__.__name__}: Matching completed after {(end_time - start_time)}s.")

                if len(trip_candidate_probabilities) > 0:
                    for trip_id, probability_vector in trip_candidate_probabilities.items():
                        logging.info(f"{self.__class__.__name__}: Matched [TripID] {trip_id} [Score] {probability_vector[-1]}, [Convergence] {trip_candidate_convergence}")

                # finally return updated trip scores
                return (trip_candidate_convergence, trip_candidate_probabilities)
            else:
                logging.warning(f"{self.__class__.__name__}: No AVL data for vehicle {vehicle.vehicle_ref}.")

                return (False, last_trip_candidate_probabilities)

        else:
            logging.warning(f"{self.__class__.__name__}: No trip candidates available to match AVL data for vehicle {vehicle.vehicle_ref}.")

            return (False, last_trip_candidate_probabilities)

    def test(self, vehicle: Vehicle, gnss_positions: list[GnssPosition]) -> bool:
        if len(self._trip_candidates) > 0:
            logging.info(f"{self.__class__.__name__}: Testing AVL data for vehicle {vehicle.vehicle_ref} with {len(self._trip_candidates)} possible trip candidates ...")
            start_time: float = time()

            if len(gnss_positions) > 1:
                movement: SpatialVectorCollection = SpatialVectorCollection(gnss_positions)

                trip_matching: bool = False
                trip_candidate: Trip = self._trip_candidates[0]

                # generate LineString in web-mercator projection for spatial and temporal matching
                trip_shape: LineString = LineString([c[::-1] for c in polyline.decode(trip_candidate.shape_polyline)])
                trip_shape = web_mercator(trip_shape)

                # run spatial matching for trip candidate
                spatial_match: SpatialMatch = SpatialMatch(trip_shape)
                spatial_match_score: float = spatial_match.calculate_match_score(movement)
                if spatial_match_score == 0.0:
                    trip_matching = False
                else:
                    trip_matching = True

                # filter position to shape if enabled
                if self._shape_filter_enabled:
                    web_mercator_position: Point = web_mercator(Point(gnss_positions[-1].longitude, gnss_positions[-1].latitude))
                    shape_distance: float = web_mercator_position.distance(trip_shape)

                    if shape_distance < self._shape_filter_distance_meters:
                        snapped_point: Point = trip_shape.interpolate(spatial_match.spatial_progress_distance)
                        snapped_point = wgs_84(snapped_point)

                        self.matched_vehicle_position = GnssPosition(
                            latitude=snapped_point.y,
                            longitude=snapped_point.x,
                            timestamp=gnss_positions[-1].timestamp
                        )

                        logging.info(f"{self.__class__.__name__}: Filtered AVL position for vehicle {vehicle.vehicle_ref} to {snapped_point.y}, {snapped_point.x} on trip {trip_candidate.descriptor.trip_id}.")
                else:
                    self.matched_vehicle_position = gnss_positions[-1]
                
                # stop time elapsed
                end_time: float = time()
                logging.info(f"{self.__class__.__name__}: Testing completed after {(end_time - start_time)}s.")
            
                return trip_matching
            else:
                logging.warning(f"{self.__class__.__name__}: No AVL data for vehicle {vehicle.vehicle_ref}.")

                return False
        else:
            logging.warning(f"{self.__class__.__name__}: No trip candidates available to test AVL data for vehicle {vehicle.vehicle_ref}.")

            return dict()
        
    def predict_trip_metrics(self, vehicle: Vehicle, gnss_position: GnssPosition) -> dict[TripMetrics]|None:
        if len(self._trip_candidates) > 0:
            logging.info(f"{self.__class__.__name__}: Predicting trip metrics for AVL data of vehicle {vehicle.vehicle_ref} with {len(self._trip_candidates)} possible trip candidates ...")
            start_time: float = time()
            trip_metrics: dict[str, TripMetrics] = dict()

            for trip_candidate in self._trip_candidates:
                
                # generate LineString in web-mercator projection for spatial and temporal matching
                trip_shape: LineString = LineString([c[::-1] for c in polyline.decode(trip_candidate.shape_polyline)])
                trip_shape = web_mercator(trip_shape)

                # run temporal matching for trip candidate
                temporal_match: TemporalMatch = TemporalMatch(
                    trip_candidate.stop_times, 
                    trip_shape
                )

                trip_metrics[trip_candidate.descriptor.trip_id] = temporal_match.predict_trip_metrics(gnss_position)

            # stop time elapsed
            end_time: float = time()
            logging.info(f"{self.__class__.__name__}: Prediction completed after {(end_time - start_time)}s.")
        
            return trip_metrics
        else:
            logging.warning(f"{self.__class__.__name__}: No trip candidates available to predict trip metrics for AVL data of vehicle {vehicle.vehicle_ref}.")

            return None