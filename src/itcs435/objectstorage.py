import logging

from pymongo import MongoClient

from itcs435.common.shared import unixtimestamp

class ObjectStorage:
    def __init__(self, username: str, password: str, db_name: str = 'itcs435'):
        
        logging.info("Connecting to MongoDB ...")
        self._mdb = MongoClient(f"mongodb://{username}:{password}@mongodb:27017/?authSource=admin")

        self._db = self._mdb[db_name]

    def get_vehicle(self, vehicle_ref: str) -> dict|None:
        vehicle = self._db.vehicles.find_one({"vehicle_ref": vehicle_ref})
        return vehicle
    
    def update_vehicle(self, vehicle_ref: str, data: dict):
        self._db.vehicles.update_one(
            {'vehicle_ref': vehicle_ref},
            {'$set': data},
            upsert=True
        )

    def get_vehicle_position(self, vehicle_ref: str) -> dict|None:
        vehicle_position = self._db.vehicle_positions.find_one({'vehicle_ref': vehicle_ref})
        return vehicle_position
    
    def update_vehicle_position(self, vehicle_ref: str, data: dict) -> None:
        
        # reduce last positions to the latest 10 elements
        # remove also positions if they are older than 5 minutes
        if 'gnss_positions' in data:

            data['gnss_positions'] = data['gnss_positions'][-10:]

            updated_gnss_positions: list[dict] = []
            current_timestamp: int = unixtimestamp()
            for gnss_position in data['gnss_positions']:
                if gnss_position['timestamp'] > current_timestamp - 300:
                    updated_gnss_positions.append(gnss_position)

            data['gnss_positions'] = updated_gnss_positions
        
        self._db.vehicle_positions.update_one(
            {'vehicle_ref': vehicle_ref},
            {'$set': data},
            upsert=True
        )

    def close(self):
        self._mdb.close()