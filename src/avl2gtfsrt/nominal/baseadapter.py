from abc import ABC, abstractmethod

from avl2gtfsrt.model.types import Trip


class BaseAdapter(ABC):

    @abstractmethod
    def get_trip_candidates(self, latitude: float, longitude: float) -> list[Trip]:
        pass