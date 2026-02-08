import json
import os
import pytz

from datetime import datetime
from math import floor

from google.transit import gtfs_realtime_pb2
from google.protobuf.json_format import ParseDict
from avl2gtfsrt.common.shared import strip_feed_id, clamp
from avl2gtfsrt.model.types import GnssPosition, Vehicle, TripDescriptor, Trip, TripMetrics
from avl2gtfsrt.objectstorage import ObjectStorage


class GtfsRealtimeExport():

    def __init__(self, object_storage: ObjectStorage):
        self._object_storage = object_storage

    def _create_feed_message(self, data: list, debug: bool = False) -> gtfs_realtime_pb2.FeedMessage|str:
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
        
        if debug:
            json_result: str = json.dumps(feed_message, indent=4)

            return json_result
        else:
            pbf_result: bytes = ParseDict(feed_message, gtfs_realtime_pb2.FeedMessage()).SerializeToString()

            return pbf_result
    
    def export_full_vehicle_positions(self, debug: bool = False) -> gtfs_realtime_pb2.FeedMessage|str:
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

        return self._create_feed_message(entities, debug)
    
    def export_full_trip_updates(self, debug: bool = False) -> gtfs_realtime_pb2.FeedMessage|str:
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

                    # generate StopTimeUpdates for each upcoming stop
                    # extract current_delay into a single variable as it may be modified during processing
                    current_delay: int = vehicle.activity.trip_metrics.current_delay
                    for stop_time in trip.stop_times:
                        # we only want to see upcoming stops, so filter for all stops where stop_sequence
                        # is lesser than the next stop sequence of the vehicle
                        if stop_time.stop_sequence < vehicle.activity.trip_metrics.next_stop_sequence:
                            continue

                        # keep track of eventual waiting times to comply with a delay
                        waiting_time: int = stop_time.departure_timestamp - stop_time.arrival_timestamp

                        # handle waiting times depending whether the trip is delayed or too early
                        if current_delay < 0:
                            arrival_delay: int = current_delay

                            # we assume that the vehicle will wait its nominal departure time 
                            # at a station with designed waiting time
                            if waiting_time > 0:
                                departure_delay: int = 0
                                current_delay = 0
                            else:
                                departure_delay: int = current_delay
                        elif current_delay > 0:
                            # waiting time is not needed anymore but reduces the delay
                            arrival_delay: int = current_delay
                            departure_delay: int = clamp(
                                current_delay - waiting_time, 
                                min(0, current_delay),
                                current_delay
                            )

                            # as we re-calculated the delay, set it for further processing too ...
                            current_delay = departure_delay
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

                    entities.append(entity)

        return self._create_feed_message(entities, debug)