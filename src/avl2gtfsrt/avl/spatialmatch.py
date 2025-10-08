import logging
import polyline

from shapely.geometry import LineString, Polygon, Point

from avl2gtfsrt.common.shared import clamp, web_mercator
from avl2gtfsrt.avl.spatialvector import SpatialVectorCollection


class SpatialMatch:

    TRIP_SHAPE_BUFFER_SIZE: float = 30.0
    TRIP_SHAPE_MATCHING_RATIO: float = 0.60
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
        activity_coords = [web_mercator(Point(*c)) for c in activity_coords]

        # calculate percentual progress of the trip determined by position
        self.spatial_progress_percentage = self._trip_shape.project(activity_coords[-1]) / self._trip_shape.length * 100.0

        # check if the GNSS coordinate activty matches the trip candidate
        num_points_matching: int = sum(1 for c in activity_coords if self._buffered_trip_shape.covers(c))
        num_points_total: int = len(activity_coords)

        match_ratio: float = num_points_matching / num_points_total if num_points_total > 0 else 0.0
        if match_ratio < self.TRIP_SHAPE_MATCHING_RATIO:
            logging.debug(f"{self.__class__.__name__}: Vehicle activity does not match the trip geometry.")
            
            return 0.0

        # check if the activity runs into the same direction as the trip candidate
        # therefore, a certain proportion of the activity must move forward along the trip shape
        activity_projections: list = [self._trip_shape.project(c) for c in activity_coords]

        num_forward_movements: int = sum(1 for i in range(len(activity_projections) - 1) if activity_projections[i] < activity_projections[i + 1])
        num_backward_movements: int = sum(1 for i in range(len(activity_projections) - 1) if activity_projections[i] > activity_projections[i + 1])

        forward_movement_ratio: float = clamp(num_forward_movements / num_backward_movements if num_backward_movements > 0 else 1.0, 0.0, 1.0)
        if forward_movement_ratio < self.TRIP_SHAPE_FORWARD_MOVEMENT_RATIO:
            logging.debug(f"{self.__class__.__name__}: Vehicle activity does not move forward along the trip geometry.")

            return 0.0

        # trip candidate is matching with sufficient ratio
        # caluclate match score and go on!
        self.match_score = match_ratio * forward_movement_ratio

        logging.debug(f"{self.__class__.__name__}: Vehicle activity matched trip geometry with forward movement ratio of {self.match_score:.2f}, spatial progress percentage is {self.spatial_progress_percentage:.2f}%.")

        return self.match_score