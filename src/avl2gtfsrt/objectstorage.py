from pymongo import MongoClient

from avl2gtfsrt.common.shared import unixtimestamp

class ObjectStorage:
    def __init__(self, username: str, password: str, db_name: str = 'avl2gtfsrt'):
        self._mdb = MongoClient(f"mongodb://{username}:{password}@mongodb:27017/?authSource=admin")

        self._db = self._mdb[db_name]

    def get_vehicles(self) -> list:
        return list(self._db.vehicles.find({}))
    
    def get_vehicle(self, vehicle_ref: str) -> dict|None:
        vehicle = self._db.vehicles.find_one({'vehicle_ref': vehicle_ref})
        return vehicle
    
    def update_vehicle(self, vehicle_ref: str, data: dict) -> None:
        self._db.vehicles.update_one(
            {'vehicle_ref': vehicle_ref},
            {'$set': data},
            upsert=True
        )

    def get_vehicle_position(self, vehicle_ref: str) -> dict|None:
        vehicle_position = self._db.vehicle_activities.find_one({'vehicle_ref': vehicle_ref})
        return vehicle_position['gnss_positions'][-1] if len(vehicle_position['gnss_positions']) > 0 else None

    def get_vehicle_activity(self, vehicle_ref: str) -> dict|None:
        vehicle_activity = self._db.vehicle_activities.find_one({'vehicle_ref': vehicle_ref})
        vehicle_activity = self._cleanup_vehicle_activity_gnss(vehicle_activity)

        return vehicle_activity
    
    def update_vehicle_activity(self, vehicle_ref: str, data: dict) -> None:
        data = self._cleanup_vehicle_activity_gnss(data)        
        
        self._db.vehicle_activities.update_one(
            {'vehicle_ref': vehicle_ref},
            {'$set': data},
            upsert=True
        )

    def delete_vehicle_activity(self, vehicle_ref: str) -> None:
        self._db.vehicle_activities.delete_one({'vehicle_ref': vehicle_ref})

    def get_trips(self) -> dict:
        return list(self._db.trips.find({}))
    
    def get_trip(self, trip_id: str) -> dict|None:
        trip = self._db.trips.find_one({'trip_id': trip_id})
        return trip
    
    def update_trip(self, trip_id: str, data: dict) -> None:
        self._db.trips.update_one(
            {'trip_id': trip_id},
            {'$set': data},
            upsert=True
        )

    def _cleanup_vehicle_activity_gnss(self, data: dict) -> dict:
        
        # reduce last positions to the latest 10 elements
        # remove also positions if they are older than 5 minutes
        if data is not None and 'gnss_positions' in data:

            # define variables for cleaning up
            gnss_max_age_seconds: int = 60

            # remove all GNSS positions which are older than 60s
            current_timestamp: int = unixtimestamp()
            updated_gnss_positions: list[dict] = []
            for gnss_position in data['gnss_positions']:
                if gnss_position['timestamp'] > current_timestamp - gnss_max_age_seconds:
                    updated_gnss_positions.append(gnss_position)

            data['gnss_positions'] = updated_gnss_positions

            # restrict to a maximum of 12 GNSS positions totally
            data['gnss_positions'] = data['gnss_positions'][-12:]

        return data

    def close(self):
        self._mdb.close()