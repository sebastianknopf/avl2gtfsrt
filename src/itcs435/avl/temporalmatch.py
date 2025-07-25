import logging
import polyline

from datetime import datetime, timezone
from shapely.geometry import LineString, Point

from itcs435.common.shared import web_mercator, clamp

class TemporalMatch:

    MAX_DEVIATION_PERCENTAGE: float = 30.0

    def __init__(self, estimated_calls: list, trip_shape_polyline: str) -> None:

        # transform shape of the trip candidate into a LineString
        self._trip_shape: LineString = LineString([c[::-1] for c in polyline.decode(trip_shape_polyline)])
        self._trip_shape = web_mercator(self._trip_shape)

        self._stop_projections_on_trip_shape: dict = {c['stopPositionInPattern']: self._trip_shape.project(web_mercator(Point(c['quay']['longitude'], c['quay']['latitude']))) for c in estimated_calls}

        # containers for later calculated data
        self.time_based_progress_percentage: float = 0.0
        self.match_score: float = 0.0
        self.next_stop_index: int|None = None

        # do not use unixtimestamp here, as we need the timestamp in minutes, without seconds!!!
        current_timestamp: int = int(datetime.now(timezone.utc).replace(microsecond=0, second=0).timestamp())

        # check whether the trip should run currently
        first_departure: int = int(datetime.fromisoformat(estimated_calls[0]['aimedDepartureTime'] if 'aimedDepartureTime' in estimated_calls[0] else estimated_calls[0]['aimedArrivalTime']).timestamp())
        last_departure: int = int(datetime.fromisoformat(estimated_calls[-1]['aimedDepartureTime'] if 'aimedDepartureTime' in estimated_calls[-1] else estimated_calls[-1]['aimedArrivalTime']).timestamp())

        if current_timestamp < first_departure:
            self.time_based_progress_percentage = 0.0
            return
        
        if current_timestamp > last_departure:
            self.time_based_progress_percentage = 100.0
            return

        # calculate the current percentual progress of the trip 
        # based on estimated calls
        for c in range(0, len(estimated_calls) - 1):
            this_call: dict = estimated_calls[c]
            next_call: dict = estimated_calls[c + 1]

            this_departure: int = int(datetime.fromisoformat(this_call['aimedDepartureTime'] if 'aimedDepartureTime' in this_call else this_call['aimedArrivalTime']).timestamp())
            next_departure: int = int(datetime.fromisoformat(next_call['aimedDepartureTime'] if 'aimedDepartureTime' in next_call else next_call['aimedArrivalTime']).timestamp())

            # if the current timestamp is on/bewteen two stops
            if this_departure <= current_timestamp <= next_departure:

                # calculate the percentual progress of the trip based on the current timestamp
                this_duration: int = abs(current_timestamp - this_departure)
                next_duration: int = abs(next_departure - this_departure)

                time_based_progress: float = (this_duration / next_duration) if next_duration > 0.0 else 1.0

                # calculate the projection length based on the time-based progress
                this_projection: float = self._stop_projections_on_trip_shape[this_call['stopPositionInPattern']]
                next_projection: float = self._stop_projections_on_trip_shape[next_call['stopPositionInPattern']]
                
                self.time_based_progress_percentage: float = (this_projection + (next_projection - this_projection) * time_based_progress) / self._trip_shape.length * 100.0
                self.time_based_progress_percentage = clamp(self.time_based_progress_percentage, 0.0, 100.0)

                self.next_stop_index = next_call['stopPositionInPattern']

                break        

    def calculate_match_score(self, spatial_progress_value: float) -> float:
        
        # if the vehicle has moved yed but the trip should not be started yet
        # or should be ended up already, we can discard the trip candidate
        if spatial_progress_value != 0.0:
            if self.time_based_progress_percentage == 0.0 or self.time_based_progress_percentage == 100.0:
                logging.info(f"{self.__class__.__name__}: Trip candidate discarded due to time-based progress percentage being {self.time_based_progress_percentage}%.")

                return 0.0
        
        # calculate the deviation between the time-based progress percentage and the spatial progress value as symmetric deviation
        deviation_percentage: float = abs(self.time_based_progress_percentage - spatial_progress_value)

        # if the deviation is too high, we can discard the trip candidate
        if deviation_percentage > self.MAX_DEVIATION_PERCENTAGE:
            logging.info(f"{self.__class__.__name__}: Trip candidate discarded due to high deviation of {deviation_percentage:.2f}% between time-based progress percentage and spatial progress.")

            return 0.0

        # finally calculate match score
        self.match_score = 1.0 - deviation_percentage / 100.0

        return self.match_score
    
    def calculate_next_stop_index(self, spatial_progress: float) -> int|None:
        for i, p in self._stop_projections_on_trip_shape.items():
            stop_percentage: float = p / self._trip_shape.length * 100.0
            if stop_percentage > spatial_progress:
                self.next_stop_index = i
                return self.next_stop_index
            
        self.next_stop_index = None
        return None





