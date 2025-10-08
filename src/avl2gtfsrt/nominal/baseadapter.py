from abc import ABC, abstractmethod


class BaseAdapter(ABC):

    @abstractmethod
    def get_trip_candidates(self, latitude: float, longitude: float) -> list[dict]:
        pass