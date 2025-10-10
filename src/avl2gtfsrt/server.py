import json
import logging
import os
import pytz
import uuid
import uvicorn

from datetime import datetime
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import ParseDict
from math import floor

from avl2gtfsrt.objectstorage import ObjectStorage

class GtfsRealtimeServer():
    
    def __init__(self) -> None:
        # connect to local MongoDB
        mongodb_username: str = os.getenv('A2G_MONGODB_USERNAME', '')
        mongodb_password: str = os.getenv('A2G_MONGODB_PASSWORD', '')

        logging.info(f"{self.__class__.__name__}: Connecting to MongoDB ...")
        self._object_storage: ObjectStorage = ObjectStorage(mongodb_username, mongodb_password)
        
        logging.info(f"{self.__class__.__name__}: Creating FastAPI instance ...")
        self._fastapi = FastAPI()
        self._api_router = APIRouter()

        self._api_router.add_api_route('/vehicle-positions.pbf', endpoint=self._vehicle_positions, methods=['GET'], name='vehicle_positions')
        self._api_router.add_api_route('/trip-updates.pbf', endpoint=self._trip_updates, methods=['GET'], name='trip_updates')

    async def _vehicle_positions(self, request: Request) -> Response:
        entities: list[dict] = list()
        
        vehicles: list = self._object_storage.get_vehicles()
        for vehicle in vehicles:
            if vehicle.get('is_technically_logged_on', False):
                vehicle_position: dict = self._object_storage.get_vehicle_position(vehicle.get('vehicle_ref'))
                if vehicle_position is not None:
                    entity: dict = {
                        'id': str(uuid.uuid4()),
                        'vehicle': {
                            'timestamp': vehicle_position['timestamp'], 
                            'vehicle': {
                                'id': vehicle.get('vehicle_ref')
                            },
                            'position': {
                                'latitude': vehicle_position['latitude'],
                                'longitude': vehicle_position['longitude']
                            }
                        }
                    }

                    if vehicle.get('is_operationally_logged_on', False):
                        entity['trip'] = {
                            'trip_id': 'test',
                            'route_id': 'test',
                            'start_time': '11:00:00',
                            'start_date': 20251010
                        }
            
                    entities.append(entity)

        return await self._response(request, entities)

    async def _trip_updates(self, request: Request) -> Response:
        return await self._response(request, [])
    
    async def _response(self, request: Request, data: list) -> Response:
        timestamp = datetime.now().astimezone(pytz.timezone(os.getenv('A2G_SERVER_TIMEZONE', 'Europe/Berlin'))).timestamp()
        timestamp = floor(timestamp)
        
        feed_message: dict = {
            'header': {
                'gtfs_realtime_version': '2.0',
                'incrementality': 'FULL_DATASET',
                'timestamp': timestamp
            },
            'entity': data
        }
        
        if 'debug' in request.query_params:
            json_result: str = json.dumps(feed_message, indent=4)

            return Response(content=json_result, media_type='application/json')
        else:
            pbf_result: bytes = ParseDict(feed_message, gtfs_realtime_pb2.FeedMessage()).SerializeToString()

            return Response(content=pbf_result, media_type='application/octet-stream')
    
    def run(self) -> None:
        self._fastapi.include_router(self._api_router)
        
        uvicorn.run(app=self._fastapi, host='0.0.0.0', port=9000)