
from itcs435.avl.spatialvector import SpatialVector, SpatialVectorCollection

class AvlMatcher:

    def __init__(self, vehicles: dict) -> None:
        self._vehicles = vehicles

    def process(self, vehicle: dict, gnss_positions: list[dict[str, any]]) -> None:
        activity: SpatialVectorCollection = SpatialVectorCollection(gnss_positions)

