import logging

from datetime import datetime, timezone
from shapely.geometry import LineString, Point

from avl2gtfsrt.common.shared import web_mercator, clamp
from avl2gtfsrt.model.types import GnssPosition, TripMetrics


class TemporalMatch:

    MAX_DEVIATION_PERCENTAGE: float = 30.0

    def __init__(self, calls: list, trip_shape: LineString) -> None:

        # store estimated calls for further processing
        # check that they're estimated calls available for this trip
        self._calls: list = calls

        if len(self._calls) == 0:
            self.time_based_progress_percentage = 0.0
            return

        # transform shape of the trip candidate into a LineString
        self._trip_shape: LineString = trip_shape

        self._stop_projections_on_trip_shape: dict = {c['stopPositionInPattern']: self._trip_shape.project(web_mercator(Point(c['quay']['longitude'], c['quay']['latitude']))) for c in calls}

        # containers for later calculated data
        self.time_based_progress_percentage: float = 0.0
        self.match_score: float = 0.0

        # do not use unixtimestamp here, as we need the timestamp in minutes, without seconds!!!
        current_timestamp: int = int(datetime.now(timezone.utc).replace(microsecond=0, second=0).timestamp())

        # check whether the trip should run currently
        first_departure: int = int(datetime.fromisoformat(self._calls[0]['aimedDepartureTime'] if 'aimedDepartureTime' in self._calls[0] else self._calls[0]['aimedArrivalTime']).timestamp())
        last_departure: int = int(datetime.fromisoformat(self._calls[-1]['aimedDepartureTime'] if 'aimedDepartureTime' in self._calls[-1] else self._calls[-1]['aimedArrivalTime']).timestamp())

        if current_timestamp < first_departure:
            self.time_based_progress_percentage = 0.0
            self.time_based_current_stop_sequence = 0
            self.time_based_next_stop_sequence = 0
            return
        
        if current_timestamp > last_departure:
            self.time_based_progress_percentage = 100.0
            self.time_based_current_stop_sequence = 0
            self.time_based_next_stop_sequence = 0
            return

        # calculate the current percentual progress of the trip 
        # based on times of estimated calls
        for c in range(0, len(self._calls) - 1):
            this_call: dict = self._calls[c]
            next_call: dict = self._calls[c + 1]

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

                self.time_based_current_stop_sequence: int = this_call['stopPositionInPattern']
                self.time_based_next_stop_sequence: int = next_call['stopPositionInPattern']
                
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
        for stop_index, stop_projection in self._stop_projections_on_trip_shape.items():
            if stop_projection >= position_projection:
                # calculate distance to the next stop and predict stop status
                distance: float = stop_projection - position_projection
                if abs(distance) < 30:
                    trip_metrics.current_stop_status = 'STOPPED_AT'
                elif distance < 60:
                    trip_metrics.current_stop_status = 'INCOMING_AT'

                # set current and next stop sequence and ID
                if stop_index > 0:
                    trip_metrics.current_stop_sequence = stop_index - 1
                    trip_metrics.current_stop_id = self._calls[stop_index - 1]['quay']['id']
                
                trip_metrics.next_stop_sequence = stop_index
                trip_metrics.next_stop_id = self._calls[stop_index]['quay']['id']

                # monitor delay between nominal next stop and AVL-based next stop
                # calculate the difference based on the departure times
                # TODO: implement a better delay prediciton here ... this is quite... basic
                actual_next_call: dict|None = next((c for c in self._calls if c['stopPositionInPattern'] == trip_metrics.next_stop_sequence), None)
                nominal_next_call: dict|None = next((c for c in self._calls if c['stopPositionInPattern'] == self.time_based_next_stop_sequence), None)
                
                if actual_next_call is not None and nominal_next_call is not None:
                    actual_next_departure: int = int(datetime.fromisoformat(actual_next_call['aimedDepartureTime'] if 'aimedDepartureTime' in actual_next_call else actual_next_call['aimedArrivalTime']).timestamp())
                    nominal_next_departure: int = int(datetime.fromisoformat(nominal_next_call['aimedDepartureTime'] if 'aimedDepartureTime' in nominal_next_call else nominal_next_call['aimedArrivalTime']).timestamp())

                    trip_metrics.current_delay = int(nominal_next_departure - actual_next_departure)

                break

        return trip_metrics
