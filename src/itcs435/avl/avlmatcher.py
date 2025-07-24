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

                for trip_candidate in self._trip_candidates:

                    # check for prerequisites
                    if 'pointsOnLink' not in trip_candidate['serviceJourney'] or trip_candidate['serviceJourney']['pointsOnLink'] is None:
                        logging.warning(f"{self.__class__.__name__}: Trip candidate {trip_candidate['serviceJourney']['id']} does not have geometry data. Skipping trip candidate.")
                        continue

                    # match trip candidate for scoring
                    match_score: float = 0.0
                    logging.info(f"{self.__class__.__name__}: Trying to match trip candidate {trip_candidate['serviceJourney']['id']} ...")

                    # run spatial matching for trip candidate
                    spatial_match: SpatialMatch = SpatialMatch(trip_candidate['serviceJourney']['pointsOnLink']['points'])
                    match_score: float = spatial_match.calculate_match_score(activity)
                    if match_score == 0.0:
                        logging.info(f"{self.__class__.__name__}: Trip candidate {trip_candidate['serviceJourney']['id']} discarded for vehicle {vehicle.get('vehicle_ref')} due to spatial matching failure.")
                        continue

                    # run temporal matching for trip candidate
                    temporal_match: TemporalMatch = TemporalMatch(
                        trip_candidate['serviceJourney']['estimatedCalls'], 
                        trip_candidate['serviceJourney']['pointsOnLink']['points']
                    )

                    match_score: float = temporal_match.calculate_match_score(spatial_match.spatial_progress_percentage)
                    if match_score == 0.0:
                        logging.info(f"{self.__class__.__name__}: Trip candidate {trip_candidate['serviceJourney']['id']} discarded for vehicle {vehicle.get('vehicle_ref')} due to temporal matching failure.")
                        continue

                    next_stop_index: int|None = temporal_match.calculate_next_stop_index(spatial_match.spatial_progress_percentage)

                    logging.info(f"{self.__class__.__name__}: Trip candidate successfully {trip_candidate['serviceJourney']['id']} matched for vehicle {vehicle.get('vehicle_ref')} with total match score of {match_score}. Next stop index is {next_stop_index}.")

            else:
                logging.warning(f"{self.__class__.__name__}: Not enough GNSS positions to match AVL data for vehicle {vehicle.get('vehicle_ref')}. At least two positions are required.")

        else:
            logging.warning(f"{self.__class__.__name__}: No trip candidates available to match AVL data for vehicle {vehicle.get('vehicle_ref')}.")
