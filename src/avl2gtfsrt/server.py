import json
import os
import pytz
import uvicorn

from datetime import datetime
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import ParseDict
from math import floor

class GtfsRealtimeServer():
    
    def __init__(self) -> None:
        self._fastapi = FastAPI()
        self._api_router = APIRouter()

        self._api_router.add_api_route('/vehicle-positions.pbf', endpoint=self._vehicle_positions, methods=['GET'], name='vehicle_positions')
        self._api_router.add_api_route('/trip-updates.pbf', endpoint=self._trip_updates, methods=['GET'], name='trip_updates')

    async def _vehicle_positions(self, request: Request) -> Response:
        return await self._response(request, [])

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