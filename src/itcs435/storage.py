import logging

from pymongo import MongoClient


class Storage:
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

    def close(self):
        self._mdb.close()