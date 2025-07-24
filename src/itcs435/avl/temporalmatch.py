import polyline

from datetime import datetime
from shapely.geometry import LineString, Polygon, Point

from itcs435.common.shared import web_mercator
from itcs435.common.shared import unixtimestamp
from itcs435.avl.spatialvector import SpatialVectorCollection

class TemporalMatch:

    def __init__(self, estimated_calls: list, trip_shape_polyline: str) -> None:

        # transform shape of the trip candidate into a LineString
        self._trip_shape: LineString = LineString([c[::-1] for c in polyline.decode(trip_shape_polyline)])
        self._trip_shape = web_mercator(trip_shape_polyline)

        # calculate the current percentual progress of the trip 
        # based on estimated calls
        current_timestamp: int = unixtimestamp()
        for c in range(0, len(estimated_calls) - 1):
            this_call: dict = estimated_calls[c]
            next_call: dict = estimated_calls[c + 1]

            this_departure: int = int(datetime.fromisoformat(this_call['aimedDepartureTime'] if 'aimedDepartureTime' in this_call else this_call['aimedArrivalTime']).timestamp())
            if current_timestamp > this_departure:
                continue

            # calculate the percentual progress of the trip based on the current timestamp
            next_departure: int = int(datetime.fromisoformat(next_call['aimedDepartureTime'] if 'aimedDepartureTime' in next_call else next_call['aimedArrivalTime']).timestamp())
            time_based_progress: float = (current_timestamp - this_departure) / (next_departure - this_departure)

            # calculate the projection length based on the time-based progress
            next_point: Point = Point(next_call['quay']['longitude'], next_call['quay']['latitude'])
            next_projection: float = self._trip_shape.project(next_point)
            
            self.time_based_progress_percentage: float = next_projection * time_based_progress / self._trip_shape.length * 100.0

        # containers for later calculated data
        self.match_score: float = 0.0

    def calculate_match_score(self, spatial_progress_value: float) -> float:
        
        p1: float = self.time_based_progress_percentage
        p2: float = spatial_progress_value

        deviation_percentage: float = abs(p2 - p1) / ((p1 + p2) / 2) * 100

        self.match_score = deviation_percentage

        return self.match_score





