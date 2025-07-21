from abc import ABC, abstractmethod


class BaseNominalAdapter(ABC):

    @abstractmethod
    def cache_trip_candidates_by_position(self, latitude: float, longitude: float) -> None:
        pass