import logging
import polyline

from shapely.geometry import LineString
from time import time

from avl2gtfsrt.avl.spatialmatch import SpatialMatch
from avl2gtfsrt.avl.temporalmatch import TemporalMatch
from avl2gtfsrt.avl.spatialvector import SpatialVectorCollection
from avl2gtfsrt.common.shared import web_mercator
from avl2gtfsrt.common.statistics import bayesian_update
from avl2gtfsrt.model.serialization import serialize, deserialize
from avl2gtfsrt.model.types import Vehicle, GnssPosition, TripMetrics
from avl2gtfsrt.objectstorage import ObjectStorage

class AvlMatcher:

    def __init__(self, object_storage: ObjectStorage, trip_candidates: dict) -> None:
        self._storage = object_storage
        self._trip_candidates = trip_candidates

    def match(self, vehicle: dict, gnss_positions: list[dict[str, any]], last_trip_candidate_probabilities: dict|None) -> tuple[bool, dict]:
        if len(self._trip_candidates) > 0:
            logging.info(f"{self.__class__.__name__}: Matching AVL data for vehicle {vehicle.get('vehicle_ref')} with {len(self._trip_candidates)} possible trip candidates ...")
            start_time: float = time()

            if len(gnss_positions) > 1:
                activity: SpatialVectorCollection = SpatialVectorCollection(gnss_positions)

                trip_candidate_scores: dict[str, float] = dict()
                for trip_candidate in self._trip_candidates:

                    # check for prerequisites

                    # check whether trip has a geometry assigned at all
                    if 'pointsOnLink' not in trip_candidate['serviceJourney'] or trip_candidate['serviceJourney']['pointsOnLink'] is None:
                        logging.warning(f"{self.__class__.__name__}: Trip candidate {trip_candidate['serviceJourney']['id']} does not have geometry data. Skipping trip candidate.")
                        continue

                    # check whether another vehicle has logged on this trip
                    # skip the ressource-consuming matching in that case and skip the candidate
                    if any(
                        self._storage.get_vehicle_trip_descriptor(v) is not None 
                        and self._storage.get_vehicle_trip_descriptor(v)['trip_id'] == trip_candidate['serviceJourney']['id'] 
                        for v in self._storage.get_vehicles()
                    ):
                        continue
                    
                    # match trip candidate for scoring
                    # 1. step: spatial matching
                    # 2. step: temporal matching

                    # generate LineString in web-mercator projection for spatial and temporal matching
                    trip_shape: LineString = LineString([c[::-1] for c in polyline.decode(trip_candidate['serviceJourney']['pointsOnLink']['points'])])
                    trip_shape = web_mercator(trip_shape)

                    # run spatial matching for trip candidate
                    spatial_match: SpatialMatch = SpatialMatch(trip_shape)
                    spatial_match_score: float = spatial_match.calculate_match_score(activity)
                    if spatial_match_score == 0.0:
                        continue

                    # run temporal matching for trip candidate
                    temporal_match: TemporalMatch = TemporalMatch(
                        trip_candidate['serviceJourney']['estimatedCalls'], 
                        trip_shape
                    )

                    temporal_match_score: float = temporal_match.calculate_match_score(spatial_match.spatial_progress_percentage)
                    if temporal_match_score == 0.0:
                        continue

                    # finally calculate trip candidate score and store it for this iteration
                    trip_candidate_score: float = spatial_match_score * temporal_match_score
                    trip_candidate_scores[trip_candidate['serviceJourney']['id']] = trip_candidate_score
                
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
                logging.warning(f"{self.__class__.__name__}: No AVL data for vehicle {vehicle.get('vehicle_ref')}.")

                return (False, last_trip_candidate_probabilities)

        else:
            logging.warning(f"{self.__class__.__name__}: No trip candidates available to match AVL data for vehicle {vehicle.get('vehicle_ref')}.")

            return (False, last_trip_candidate_probabilities)

    def test(self, vehicle: dict, gnss_positions: list[dict[str, any]]) -> dict[str, bool]:
        if len(self._trip_candidates) > 0:
            logging.info(f"{self.__class__.__name__}: Testing AVL data for vehicle {vehicle.get('vehicle_ref')} with {len(self._trip_candidates)} possible trip candidates ...")
            start_time: float = time()

            if len(gnss_positions) > 1:
                activity: SpatialVectorCollection = SpatialVectorCollection(gnss_positions)

                trip_matches: dict[str, bool] = dict()
                for trip_candidate in self._trip_candidates:

                    # generate LineString in web-mercator projection for spatial and temporal matching
                    trip_shape: LineString = LineString([c[::-1] for c in polyline.decode(trip_candidate['serviceJourney']['pointsOnLink']['points'])])
                    trip_shape = web_mercator(trip_shape)

                    # run spatial matching for trip candidate
                    spatial_match: SpatialMatch = SpatialMatch(trip_shape)
                    spatial_match_score: float = spatial_match.calculate_match_score(activity)
                    if spatial_match_score > 0.0:
                        trip_matches[trip_candidate['serviceJourney']['id']] = True
                    else:
                        trip_matches[trip_candidate['serviceJourney']['id']] = False

                # stop time elapsed
                end_time: float = time()
                logging.info(f"{self.__class__.__name__}: Testing completed after {(end_time - start_time)}s.")
            
                return trip_matches
            else:
                logging.warning(f"{self.__class__.__name__}: No AVL data for vehicle {vehicle.get('vehicle_ref')}.")

                return dict()
        else:
            logging.warning(f"{self.__class__.__name__}: No trip candidates available to test AVL data for vehicle {vehicle.get('vehicle_ref')}.")

            return dict()
        
    def predict_trip_metrics(self, vehicle: Vehicle, gnss_position: GnssPosition) -> dict[TripMetrics]|None:
        if len(self._trip_candidates) > 0:
            logging.info(f"{self.__class__.__name__}: Predicting trip metrics for AVL data of vehicle {vehicle.vehicle_ref} with {len(self._trip_candidates)} possible trip candidates ...")
            start_time: float = time()
            trip_metrics: dict[str, TripMetrics] = dict()

            for trip_candidate in self._trip_candidates:
                
                # generate LineString in web-mercator projection for spatial and temporal matching
                trip_shape: LineString = LineString([c[::-1] for c in polyline.decode(trip_candidate['serviceJourney']['pointsOnLink']['points'])])
                trip_shape = web_mercator(trip_shape)

                # run temporal matching for trip candidate
                temporal_match: TemporalMatch = TemporalMatch(
                    trip_candidate['serviceJourney']['estimatedCalls'], 
                    trip_shape
                )

                trip_metrics[trip_candidate['serviceJourney']['id']] = temporal_match.predict_trip_metrics(gnss_position)

            # stop time elapsed
            end_time: float = time()
            logging.info(f"{self.__class__.__name__}: Prediction completed after {(end_time - start_time)}s.")
        
            return trip_metrics
        else:
            logging.warning(f"{self.__class__.__name__}: No trip candidates available to predict trip metrics for AVL data of vehicle {vehicle.get('vehicle_ref')}.")

            return None