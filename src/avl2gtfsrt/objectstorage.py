from pymongo import MongoClient

from avl2gtfsrt.common.shared import unixtimestamp
from avl2gtfsrt.model.serialization import serialize, deserialize
from avl2gtfsrt.model.types import *


class ObjectStorage:
    def __init__(self, username: str, password: str, data_review_seconds: int, max_data_points: int, db_name: str = 'avl2gtfsrt'): 
        self._mdb = MongoClient(f"mongodb://{username}:{password}@avl2gtfsrt-mongodb:27017/?authSource=admin")

        self._data_review_seconds: int = data_review_seconds
        self._max_data_points: int = max_data_points

        self._db = self._mdb[db_name]

    def get_vehicles(self) -> list[Vehicle]:
        data: list = list(self._db.vehicles.find({}))

        return [deserialize(Vehicle, v) for v in data]
    
    def get_vehicle(self, vehicle_ref: str) -> Vehicle|None:
        data: dict = self._db.vehicles.find_one({'vehicle_ref': vehicle_ref})
        
        return deserialize(Vehicle, data) if data is not None else None
    
    def update_vehicle(self, vehicle: Vehicle) -> None:
        if vehicle.activity is not None:
            vehicle.activity = self._cleanup_vehicle_activity_gnss(vehicle.activity)
        
        data: dict = serialize(vehicle)
        vehicle_ref: str = data['vehicle_ref']
 
        self._db.vehicles.update_one(
            {'vehicle_ref': vehicle_ref},
            {'$set': data},
            upsert=True
        )

    def cleanup_vehicle_trip_refs(self, vehicle: Vehicle) -> None:
        if vehicle.activity is not None:
            vehicle.activity.trip_descriptor = None
            vehicle.activity.trip_metrics = None
        
        self.update_vehicle(vehicle)

    def get_trips(self) -> list[Trip]:
        data: list = list(self._db.trips.find({}))

        return [deserialize(Trip, t) for t in data]
    
    def get_trip(self, trip_id: str) -> Trip|None:
        data: dict = self._db.trips.find_one({'descriptor.trip_id': trip_id})
        
        return deserialize(Trip, data) if data is not None else None
    
    def update_trip(self, trip: Trip) -> None:        
        data: dict = serialize(trip)
        trip_id: str = data['descriptor']['trip_id']
 
        self._db.trips.update_one(
            {'descriptor.trip_id': trip_id},
            {'$set': data},
            upsert=True
        )

    def delete_trip(self, trip: Trip) -> None:
        data: dict = serialize(trip)
        trip_id: str = data['descriptor']['trip_id']

        self._db.trips.delete_one(
            {'descriptor.trip_id': trip_id}
        )

    def _cleanup_vehicle_activity_gnss(self, activity: VehicleActivity) -> VehicleActivity:
        
        # 1. remove positions if they are older than max_age_seconds
        # 2. reduce latest positions to the maximum of max_data_points

        # define variables for cleaning up
        gnss_max_age_seconds: int = self._data_review_seconds

        # remove all GNSS positions which are older than 60s
        current_timestamp: int = unixtimestamp()
        updated_gnss_positions: list[GnssPosition] = list()
        for gnss_position in activity.gnss_positions:
            if gnss_position.timestamp > current_timestamp - gnss_max_age_seconds:
                updated_gnss_positions.append(gnss_position)

        activity.gnss_positions = updated_gnss_positions
        activity.gnss_positions = activity.gnss_positions[-(self._max_data_points):]

        return activity

    def close(self):
        self._mdb.close()