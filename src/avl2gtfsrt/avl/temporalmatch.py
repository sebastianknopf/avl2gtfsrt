import logging

from datetime import datetime, timezone
from shapely.geometry import LineString, Point

from avl2gtfsrt.common.shared import web_mercator, clamp
from avl2gtfsrt.model.types import GnssPosition, TripMetrics

class TemporalMatch:

    MAX_DEVIATION_PERCENTAGE: float = 30.0

    def __init__(self, estimated_calls: list, trip_shape: LineString) -> None:

        # store estimated calls for further processing
        self._estimated_calls: list = estimated_calls

        # transform shape of the trip candidate into a LineString
        self._trip_shape: LineString = trip_shape

        self._stop_projections_on_trip_shape: dict = {c['stopPositionInPattern']: self._trip_shape.project(web_mercator(Point(c['quay']['longitude'], c['quay']['latitude']))) for c in estimated_calls}

        # containers for later calculated data
        self.time_based_progress_percentage: float = 0.0
        self.match_score: float = 0.0

        # do not use unixtimestamp here, as we need the timestamp in minutes, without seconds!!!
        current_timestamp: int = int(datetime.now(timezone.utc).replace(microsecond=0, second=0).timestamp())

        # check whether the trip should run currently
        first_departure: int = int(datetime.fromisoformat(self._estimated_calls[0]['aimedDepartureTime'] if 'aimedDepartureTime' in self._estimated_calls[0] else self._estimated_calls[0]['aimedArrivalTime']).timestamp())
        last_departure: int = int(datetime.fromisoformat(self._estimated_calls[-1]['aimedDepartureTime'] if 'aimedDepartureTime' in self._estimated_calls[-1] else self._estimated_calls[-1]['aimedArrivalTime']).timestamp())

        if current_timestamp < first_departure:
            self.time_based_progress_percentage = 0.0
            return
        
        if current_timestamp > last_departure:
            self.time_based_progress_percentage = 100.0
            return

        # calculate the current percentual progress of the trip 
        # based on times of estimated calls
        for c in range(0, len(self._estimated_calls) - 1):
            this_call: dict = self._estimated_calls[c]
            next_call: dict = self._estimated_calls[c + 1]

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
                
                break        

    def calculate_match_score(self, spatial_progress_percentage: float) -> float:
        
        # if the vehicle has moved yed but the trip should not be started yet
        # or should be ended up already, we can discard the trip candidate
        if spatial_progress_percentage != 0.0:
            if self.time_based_progress_percentage == 0.0:
                logging.debug(f"{self.__class__.__name__}: Trip candidate discarded due to time-based progress percentage being {self.time_based_progress_percentage}%.")

                return 0.0
        
        # calculate the deviation between the time-based progress percentage and the spatial progress value as symmetric deviation
        deviation_percentage: float = self.time_based_progress_percentage - spatial_progress_percentage

        # if the deviation is too high, we can discard the trip candidate
        if abs(deviation_percentage) > self.MAX_DEVIATION_PERCENTAGE:
            logging.debug(f"{self.__class__.__name__}: Trip candidate discarded due to high deviation of {deviation_percentage:.2f}% between time-based progress percentage and spatial progress.")

            return 0.0

        # calculate match score
        # consider early trips with lesser factor
        if deviation_percentage >= 0.0:
            self.match_score = (1.0 - abs(deviation_percentage) / 100.0)
        else:
            self.match_score = (1.0 - abs(deviation_percentage) / 100.0) * 0.8

        return self.match_score
    
    def predict_trip_metrics(self, gnss_position: GnssPosition) -> TripMetrics:
        trip_metrics: TripMetrics = TripMetrics()

        # calculate current spatial progress for further processing
        position_projection: float = self._trip_shape.project(web_mercator(Point(gnss_position.longitude, gnss_position.latitude)))

        # determine current and next stop index
        for stop_index, stop_projection in self._stop_projections_on_trip_shape.items():
            if stop_projection >= position_projection:
                if stop_index > 0:
                    trip_metrics.current_stop_index = stop_index - 1
                    trip_metrics.current_stop_id = self._estimated_calls[stop_index - 1]['quay']['id']
                
                trip_metrics.next_stop_index = stop_index
                trip_metrics.next_stop_id = self._estimated_calls[stop_index]['quay']['id']

                break

        # TODO: calculate delay somehow ...

        return trip_metrics

