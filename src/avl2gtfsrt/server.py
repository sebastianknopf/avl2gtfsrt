import json
import logging
import os
import pytz
import uvicorn

from datetime import datetime
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware
from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import ParseDict
from math import floor

from avl2gtfsrt.common.shared import strip_feed_id, clamp
from avl2gtfsrt.model.types import GnssPosition, Vehicle, TripDescriptor, Trip, TripMetrics
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
        entities: list[dict] = list()
        
        vehicles: list[Vehicle] = self._object_storage.get_vehicles()
        for vehicle in vehicles:
            if vehicle.is_technically_logged_on:
                vehicle_position: GnssPosition = vehicle.activity.gnss_positions[-1] if len(vehicle.activity.gnss_positions) > 0 else None
                if vehicle_position is not None:
                    entity: dict = {
                        'id': vehicle.vehicle_ref,
                        'vehicle': {
                            'timestamp': vehicle_position.timestamp, 
                            'vehicle': {
                                'id': vehicle.vehicle_ref,
                                'label': vehicle.vehicle_ref,
                                'licensePlate': vehicle.vehicle_ref
                            },
                            'position': {
                                'latitude': vehicle_position.latitude,
                                'longitude': vehicle_position.longitude
                            }
                        }
                    }

                    if vehicle.is_operationally_logged_on:                        
                        vehicle_trip_descriptor: TripDescriptor = vehicle.activity.trip_descriptor
                        if vehicle_trip_descriptor is not None:
                            entity['vehicle']['trip'] = {
                                'trip_id': strip_feed_id(vehicle_trip_descriptor.trip_id),
                                'route_id': strip_feed_id(vehicle_trip_descriptor.route_id),
                                'start_time': vehicle_trip_descriptor.start_time,
                                'start_date': vehicle_trip_descriptor.start_date
                            }

                        vehicle_trip_metrics: TripMetrics = vehicle.activity.trip_metrics
                        if vehicle_trip_metrics is not None and vehicle_trip_metrics.next_stop_sequence is not None:
                            entity['vehicle']['currentStopSequence'] = vehicle_trip_metrics.next_stop_sequence

                        if vehicle_trip_metrics is not None and vehicle_trip_metrics.current_stop_status is not None:
                            entity['vehicle']['currentStatus'] = vehicle_trip_metrics.current_stop_status

                        if vehicle_trip_metrics is not None and vehicle_trip_metrics.next_stop_id is not None:
                            entity['vehicle']['stopId'] = strip_feed_id(vehicle_trip_metrics.next_stop_id)
            
                    entities.append(entity)

        return await self._response(request, entities)

    async def _trip_updates(self, request: Request) -> Response:
        entities: list[dict] = list()
        
        vehicles: list[Vehicle] = self._object_storage.get_vehicles()
        for vehicle in vehicles:
            if vehicle.is_technically_logged_on and vehicle.is_operationally_logged_on and vehicle.activity.trip_metrics is not None:
                
                trip: Trip = self._object_storage.get_trip(vehicle.activity.trip_descriptor.trip_id)
                vehicle_position: GnssPosition = vehicle.activity.gnss_positions[-1] if len(vehicle.activity.gnss_positions) > 0 else None
                
                if trip is not None:
                    entity: dict = {
                        'id': strip_feed_id(trip.descriptor.trip_id),
                        'trip_update': {
                            'timestamp': vehicle_position.timestamp, 
                            'trip': {
                                'trip_id': strip_feed_id(trip.descriptor.trip_id),
                                'route_id': strip_feed_id(trip.descriptor.route_id),
                                'start_time': trip.descriptor.start_time,
                                'start_date': trip.descriptor.start_date
                            },
                            'vehicle': {
                                'id': vehicle.vehicle_ref,
                                'label': vehicle.vehicle_ref,
                                'licensePlate': vehicle.vehicle_ref
                            },
                            'stop_time_update': list()
                        }
                    }

                    for stop_time in trip.stop_times:
                        # we only want to see upcoming stops, so filter for all stops where stop_sequence
                        # is lesser than the next stop sequence of the vehicle
                        if stop_time.stop_sequence < vehicle.activity.trip_metrics.next_stop_sequence:
                            continue

                        # keep track of eventual waiting times to comply with a delay
                        waiting_time: int = stop_time.departure_timestamp - stop_time.arrival_timestamp

                        # handle waiting times depending whether the trip is delayed or too early
                        if vehicle.activity.trip_metrics.current_delay < 0:
                            # we assume that the vehicle will wait its nominal departure time 
                            # at a station with designed waiting time
                            arrival_delay: int = vehicle.activity.trip_metrics.current_delay
                            departure_delay: int = 0
                        elif vehicle.activity.trip_metrics.current_delay > 0:
                            # waiting time is not needed anymore but reduces the delay
                            arrival_delay: int = vehicle.activity.trip_metrics.current_delay
                            departure_delay: int = clamp(
                                vehicle.activity.trip_metrics.current_delay - waiting_time, 
                                min(0, vehicle.activity.trip_metrics.current_delay),
                                vehicle.activity.trip_metrics.current_delay
                            )
                        else:
                            # we have no delay at all
                            arrival_delay: int = 0
                            departure_delay: int = 0

                        stop_time_update: dict = {
                            'stop_id': strip_feed_id(stop_time.stop.stop_id),
                            'arrival': {
                                'time': (stop_time.arrival_timestamp + arrival_delay),
                                'delay': arrival_delay
                            },
                            'departure': {
                                'time': (stop_time.departure_timestamp + departure_delay),
                                'delay': departure_delay
                            }
                        }

                        entity['trip_update']['stop_time_update'].append(stop_time_update)

                        #break

                    entities.append(entity)

        return await self._response(request, entities)
    
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