import logging
import polyline

from shapely.geometry import LineString, Polygon, Point

from itcs435.common.shared import web_mercator
from itcs435.avl.spatialvector import SpatialVectorCollection


class SpatialMatch:

    TRIP_SHAPE_BUFFER_SIZE: float = 15.0
    TRIP_SHAPE_FORWARD_MOVEMENT_RATIO: float = 0.75

    def __init__(self, trip_shape_polyline: str) -> None:
        
        # transform shape of the trip candidate into a LineString
        self._trip_shape: LineString = LineString([c[::-1] for c in polyline.decode(trip_shape_polyline)])
        self._trip_shape = web_mercator(self._trip_shape)
        
        # add buffer around trip shape to allow for some tolerance in matching
        self._buffered_trip_shape: Polygon = self._trip_shape.buffer(self.TRIP_SHAPE_BUFFER_SIZE)

        # containers for later calculated data
        self.match_score: float = 0.0
        self.spatial_progress_percentage: float|None = None
    
    def calculate_match_score(self, vehicle_activity: SpatialVectorCollection) -> float:
        activity_coords: list = [(v.start['longitude'], v.start['latitude']) for v in vehicle_activity.spatial_vectors]
        activity_coords.append((vehicle_activity.spatial_vectors[-1].end['longitude'], vehicle_activity.spatial_vectors[-1].end['latitude']))
        
        self._activity_shape: LineString = LineString(activity_coords)
        self._activity_shape = web_mercator(self._activity_shape)

        # calculate percentual progress of the trip determined by position
        self.spatial_progress_percentage = self._trip_shape.project(Point(self._activity_shape.coords[-1])) / self._trip_shape.length * 100.0

        # check if the GNSS coordinate activty matches the trip candidate
        if not self._buffered_trip_shape.covers(self._activity_shape):
            logging.info(f"{self.__class__.__name__}: Vehicle activity does not match the trip geometry.")
            
            return self.match_score

        # check if the activity runs into the same direction as the trip candidate
        # therefore, a certain proportion of the activity must move forward along the trip shape
        activity_projections: list = [self._trip_shape.project(Point(p)) for p in self._activity_shape.coords]

        num_forward_movements: int = sum(1 for i in range(len(activity_projections) - 1) if activity_projections[i] < activity_projections[i + 1])
        num_backward_movements: int = sum(1 for i in range(len(activity_projections) - 1) if activity_projections[i] > activity_projections[i + 1])

        self.match_score: float = num_forward_movements / num_backward_movements if num_backward_movements > 0 else 1.0

        if self.match_score < self.TRIP_SHAPE_FORWARD_MOVEMENT_RATIO:
            logging.info(f"{self.__class__.__name__}: Vehicle activity does not move forward along the trip geometry.")
            
            return self.match_score
        else:
            logging.info(f"{self.__class__.__name__}: Vehicle activity matched trip geometry with forward movement ratio of {self.match_score:.2f}, spatial progress percentage is {self.spatial_progress_percentage:.2f}%.")

            return self.match_score