from abc import ABC, abstractmethod


class BaseNominalAdapter(ABC):

    @abstractmethod
    def get_trip_candidates(self, latitude: float, longitude: float) -> None:
        pass