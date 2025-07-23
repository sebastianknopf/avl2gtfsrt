import logging
import polyline

from shapely.geometry import LineString, Polygon, Point
from shapely.ops import transform
from pyproj import CRS, Transformer

from itcs435.avl.spatialvector import SpatialVector, SpatialVectorCollection

class AvlMatcher:

    def __init__(self, vehicles: dict, trip_candidates: dict) -> None:
        self._vehicles = vehicles
        self._trip_candidates = trip_candidates

    def process(self, vehicle: dict, gnss_positions: list[dict[str, any]]) -> None:

        if len(self._trip_candidates) > 0:
            logging.info(f"{self.__class__.__name__}: Matching AVL data for vehicle {vehicle.get('vehicle_ref')} with {len(self._trip_candidates)} possible trip candidates ...")

            if len(gnss_positions) > 1:
                activity: SpatialVectorCollection = SpatialVectorCollection(gnss_positions)

                for trip_candidate in self._trip_candidates:

                    if 'pointsOnLink' not in trip_candidate['serviceJourney'] or trip_candidate['serviceJourney']['pointsOnLink'] is None:
                        logging.warning(f"{self.__class__.__name__}: Trip candidate {trip_candidate['serviceJourney']['id']} does not have geometry data. Skipping trip candidate.")
                        continue

                    # transform shape of the trip candidate into a LineString
                    # add buffer of 5 meters to the shape
                    trip_shape: LineString = LineString([c[::-1] for c in polyline.decode(trip_candidate['serviceJourney']['pointsOnLink']['points'])])
                    trip_shape = transform(Transformer.from_crs(CRS('EPSG:4326'), CRS('EPSG:3857'), always_xy=True).transform, trip_shape)
                    buffered_trip_shape: Polygon = trip_shape.buffer(15.0)

                    # check if the GNSS coordinate activty matches the trip candidate
                    activity_shape: LineString = activity.get_web_mercator_line_string()
                    if not buffered_trip_shape.covers(activity_shape):
                        logging.info(f"{self.__class__.__name__}: Trip candidate {trip_candidate['serviceJourney']['id']} discarded because vehicle activity does not match the trip geometry.")
                        continue

                    # check if the activity runs into the same direction as the trip candidate
                    projections = [trip_shape.project(Point(p)) for p in activity_shape.coords]
                    if not all(earlier <= later for earlier, later in zip(projections, projections[1:])):
                        logging.info(f"{self.__class__.__name__}: Trip candidate {trip_candidate['serviceJourney']['id']} discarded because vehicle activity runs into the opposite direction as the trip geometry.")
                        continue

                    logging.info(f"{self.__class__.__name__}: Trip candidate {trip_candidate['serviceJourney']['id']} matched for vehicle {vehicle.get('vehicle_ref')}.")
            else:
                logging.warning(f"{self.__class__.__name__}: Not enough GNSS positions to match AVL data for vehicle {vehicle.get('vehicle_ref')}. At least two positions are required.")

        else:
            logging.warning(f"{self.__class__.__name__}: No trip candidates available to match AVL data for vehicle {vehicle.get('vehicle_ref')}.")
