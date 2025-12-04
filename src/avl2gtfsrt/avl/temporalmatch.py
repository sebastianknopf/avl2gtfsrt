import logging

from datetime import datetime, timezone
from shapely.geometry import LineString, Point

from avl2gtfsrt.common.shared import web_mercator, clamp
from avl2gtfsrt.model.types import GnssPosition, StopTime, TripMetrics


class TemporalMatch:

    MAX_DEVIATION_PERCENTAGE: float = 30.0

    def __init__(self, stop_times: list[StopTime], trip_shape: LineString) -> None:

        # store stop times for further processing
        self._stop_times: list[StopTime] = stop_times

        # transform shape of the trip candidate into a LineString
        self._trip_shape: LineString = trip_shape

        self._stop_projections_on_trip_shape: dict = {s.stop_sequence: self._trip_shape.project(web_mercator(Point(s.stop.longitude, s.stop.latitude))) for s in self._stop_times}

        # containers for later calculated data
        self.time_based_progress_percentage: float = 0.0
        self.match_score: float = 0.0

        # do not use unixtimestamp here, as we need the timestamp in minutes, without seconds!!!
        current_timestamp: int = int(datetime.now(timezone.utc).replace(microsecond=0, second=0).timestamp())

        # check whether the trip should run currently
        first_departure_timestamp: int = self._stop_times[0].departure_timestamp
        last_departure_timestamp: int = self._stop_times[-1].departure_timestamp

        if current_timestamp <= first_departure_timestamp:
            self.time_based_progress_percentage = 0.0
            self.time_based_current_stop_sequence = 0
            self.time_based_next_stop_sequence = 0
            return
        
        if current_timestamp >= last_departure_timestamp:
            self.time_based_progress_percentage = 100.0
            self.time_based_current_stop_sequence = self._stop_times[-2].stop_sequence
            self.time_based_next_stop_sequence = self._stop_times[-1].stop_sequence
            return

        # calculate the current percentual progress of the trip 
        # based on times of stop times
        for c in range(0, len(self._stop_times) - 1):
            this_stop_time: StopTime = self._stop_times[c]
            next_stop_time: StopTime = self._stop_times[c + 1]

            this_departure: int = this_stop_time.departure_timestamp
            next_departure: int = next_stop_time.departure_timestamp

            # if the current timestamp is on/bewteen two stops
            if this_departure <= current_timestamp <= next_departure:

                # calculate the percentual progress of the trip based on the current timestamp
                this_duration: int = abs(current_timestamp - this_departure)
                next_duration: int = abs(next_departure - this_departure)

                time_based_progress: float = (this_duration / next_duration) if next_duration > 0.0 else 1.0

                # calculate the projection length based on the time-based progress
                this_projection: float = self._stop_projections_on_trip_shape[this_stop_time.stop_sequence]
                next_projection: float = self._stop_projections_on_trip_shape[next_stop_time.stop_sequence]
                
                self.time_based_progress_percentage = (this_projection + (next_projection - this_projection) * time_based_progress) / self._trip_shape.length * 100.0
                self.time_based_progress_percentage = clamp(self.time_based_progress_percentage, 0.0, 100.0)

                self.time_based_current_stop_sequence: int = this_stop_time.stop_sequence
                self.time_based_next_stop_sequence: int = next_stop_time.stop_sequence

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
        trip_metrics.current_stop_status = 'IN_TRANSIT_TO'

        # calculate current spatial progress for further processing
        position_projection: float = self._trip_shape.project(web_mercator(Point(gnss_position.longitude, gnss_position.latitude)))

        # determine current and next stop index
        for stop_sequence, stop_projection in self._stop_projections_on_trip_shape.items():
            if stop_projection >= position_projection:
                # calculate distance to the next stop and predict stop status
                distance: float = stop_projection - position_projection
                if abs(distance) < 30:
                    trip_metrics.current_stop_status = 'STOPPED_AT'

                    if stop_sequence == max(list(self._stop_projections_on_trip_shape.keys())):
                        trip_metrics.current_stop_is_final = True

                elif distance < 60:
                    trip_metrics.current_stop_status = 'INCOMING_AT'

                    if stop_sequence == max(list(self._stop_projections_on_trip_shape.keys())):
                        trip_metrics.current_stop_is_final = True

                # set current and next stop sequence and ID
                if stop_sequence > 0:
                    trip_metrics.current_stop_sequence = stop_sequence - 1
                    trip_metrics.current_stop_id = self._stop_times[stop_sequence - 1].stop.stop_id
                
                trip_metrics.next_stop_sequence = stop_sequence
                trip_metrics.next_stop_id = self._stop_times[stop_sequence].stop.stop_id

                # monitor delay between nominal next stop and AVL-based next stop
                # calculate the difference based on the departure times
                # TODO: implement a better delay prediciton here ... this is quite... basic
                current_timestamp: int = int(datetime.now(timezone.utc).timestamp())
                actual_next_stop_time: StopTime|None = next((s for s in self._stop_times if s.stop_sequence == trip_metrics.next_stop_sequence), None)
                nominal_next_stop_time: StopTime|None = next((s for s in self._stop_times if s.stop_sequence == self.time_based_next_stop_sequence), None)
                
                if actual_next_stop_time is not None:
                    trip_metrics.current_delay = current_timestamp - actual_next_stop_time.departure_timestamp
                    
                break

        return trip_metrics
