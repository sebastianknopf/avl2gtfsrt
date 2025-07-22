
from itcs435.avl.spatialvector import SpatialVector, SpatialVectorCollection

class AvlMatcher:

    def __init__(self, vehicles: dict, trip_candidates: dict) -> None:
        self._vehicles = vehicles
        self._trip_candidates = trip_candidates

    def process(self, vehicle: dict, gnss_positions: list[dict[str, any]]) -> None:
        if len(gnss_positions) > 1:
            activity: SpatialVectorCollection = SpatialVectorCollection(gnss_positions)

