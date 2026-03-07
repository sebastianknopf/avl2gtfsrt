import logging
import os
import uvicorn

from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware
from google.transit import gtfs_realtime_pb2

from avl2gtfsrt.objectstorage import ObjectStorage
from avl2gtfsrt.gtfsrt.export import GtfsRealtimeExport


class GtfsRealtimeServer():
    
    def __init__(self) -> None:
        # connect to local MongoDB
        mongodb_username: str = os.getenv('A2G_MONGODB_USERNAME', '')
        mongodb_password: str = os.getenv('A2G_MONGODB_PASSWORD', '')

        logging.info(f"{self.__class__.__name__}: Connecting to MongoDB ...")
        self._object_storage: ObjectStorage = ObjectStorage(
            mongodb_username, 
            mongodb_password,
            int(os.getenv('A2G_MATCHING_DATA_REVIEW_SECONDS', '120')),
            int(os.getenv('A2G_MATCHING_MAX_DATA_POINTS', '60'))
        )
        
        logging.info(f"{self.__class__.__name__}: Creating FastAPI instance ...")
        self._fastapi = FastAPI()
        self._fastapi.add_middleware(
            CORSMiddleware,
            allow_origins=['*'],
            allow_credentials=True,
            allow_methods=['GET'],
            allow_headers=['*']
        )

        self._api_router = APIRouter()
        self._api_router.add_api_route('/vehicle-positions.pbf', endpoint=self._vehicle_positions, methods=['GET'], name='vehicle_positions')
        self._api_router.add_api_route('/trip-updates.pbf', endpoint=self._trip_updates, methods=['GET'], name='trip_updates')

    async def _vehicle_positions(self, request: Request) -> Response:
        gtfsrt_export: GtfsRealtimeExport = GtfsRealtimeExport(self._object_storage)
        gtfsrt_data: gtfs_realtime_pb2.FeedMessage|str = gtfsrt_export.export_full_vehicle_positions(debug='debug' in request.query_params)

        return await self._response(request, gtfsrt_data)

    async def _trip_updates(self, request: Request) -> Response:
        gtfsrt_export: GtfsRealtimeExport = GtfsRealtimeExport(self._object_storage)
        gtfsrt_data: gtfs_realtime_pb2.FeedMessage|str = gtfsrt_export.export_full_trip_updates(debug='debug' in request.query_params)

        return await self._response(request, gtfsrt_data)
    
    async def _response(self, request: Request, data: gtfs_realtime_pb2.FeedMessage|str) -> Response:
        if 'debug' in request.query_params:
            return Response(content=data, media_type='application/json')
        else:
            return Response(content=data, media_type='application/octet-stream')
    
    def run(self) -> None:
        self._fastapi.include_router(self._api_router)
        
        uvicorn.run(app=self._fastapi, host='0.0.0.0', port=9000)