import logging

from itcs435.avl.spatialmatch import SpatialMatch
from itcs435.avl.temporalmatch import TemporalMatch
from itcs435.avl.spatialvector import SpatialVectorCollection

class AvlMatcher:

    def __init__(self, vehicles: dict, trip_candidates: dict) -> None:
        self._vehicles = vehicles
        self._trip_candidates = trip_candidates

    def process(self, vehicle: dict, gnss_positions: list[dict[str, any]]) -> None:

        if len(self._trip_candidates) > 0:
            logging.info(f"{self.__class__.__name__}: Matching AVL data for vehicle {vehicle.get('vehicle_ref')} with {len(self._trip_candidates)} possible trip candidates ...")

            if len(gnss_positions) > 1:
                activity: SpatialVectorCollection = SpatialVectorCollection(gnss_positions)

                scored_trip_candidates: dict = dict()
                for trip_candidate in self._trip_candidates:

                    # check for prerequisites

                    # check whether trip has a geometry assigned at all
                    if 'pointsOnLink' not in trip_candidate['serviceJourney'] or trip_candidate['serviceJourney']['pointsOnLink'] is None:
                        logging.warning(f"{self.__class__.__name__}: Trip candidate {trip_candidate['serviceJourney']['id']} does not have geometry data. Skipping trip candidate.")
                        continue

                    # check whether another vehicle has logged on this trip
                    # skip the ressource-consuming matching in that case and skip the candidate
                    if any(v.get('current_trip_id', None) == trip_candidate['serviceJourney']['id'] for v in self._vehicles):
                        continue
                    
                    # match trip candidate for scoring
                    # 1. step: spatial matching
                    # 2. step: temporal matching

                    # run spatial matching for trip candidate
                    spatial_match: SpatialMatch = SpatialMatch(trip_candidate['serviceJourney']['pointsOnLink']['points'])
                    spatial_match_score: float = spatial_match.calculate_match_score(activity)
                    if spatial_match_score == 0.0:
                        continue

                    # run temporal matching for trip candidate
                    temporal_match: TemporalMatch = TemporalMatch(
                        trip_candidate['serviceJourney']['estimatedCalls'], 
                        trip_candidate['serviceJourney']['pointsOnLink']['points']
                    )

                    temporal_match_score: float = temporal_match.calculate_match_score(spatial_match.spatial_progress_percentage)
                    if temporal_match_score == 0.0:
                        continue

                    next_stop_metrics = temporal_match.predict_next_stop_metrics(spatial_match.spatial_progress_percentage)

                    scored_trip_candidates[trip_candidate['serviceJourney']['id']] = spatial_match_score * temporal_match_score

                # print scored trip candidates
                if len(scored_trip_candidates) > 0:
                    for trip_id, score in scored_trip_candidates.items():
                        logging.info(f"{self.__class__.__name__}: Matched [TripID] {trip_id} [Score] {score}")

        else:
            logging.warning(f"{self.__class__.__name__}: No trip candidates available to match AVL data for vehicle {vehicle.get('vehicle_ref')}.")
