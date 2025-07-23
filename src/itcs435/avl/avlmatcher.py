import logging

from itcs435.avl.spatialvector import SpatialVector, SpatialVectorCollection

class AvlMatcher:

    def __init__(self, vehicles: dict, trip_candidates: dict) -> None:
        self._vehicles = vehicles
        self._trip_candidates = trip_candidates

    def process(self, vehicle: dict, gnss_positions: list[dict[str, any]]) -> None:

        if len(self._trip_candidates) > 0:
            logging.info(f"{self.__class__.__name__}: Matching AVL data for vehicle {vehicle.get('vehicle_ref')} with {len(self._trip_candidates)} possible trip candidates ...")

            if len(gnss_positions) > 1:
                activity: SpatialVectorCollection = SpatialVectorCollection(gnss_positions)
            else:
                logging.warning(f"{self.__class__.__name__}: Not enough GNSS positions to match AVL data for vehicle {vehicle.get('vehicle_ref')}. At least two positions are required.")

