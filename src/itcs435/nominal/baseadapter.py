from abc import ABC, abstractmethod


class BaseNominalAdapter(ABC):

    @abstractmethod
    def load_nominal_trips_by_position(self, latitude: float, longitude: float) -> None:
        pass