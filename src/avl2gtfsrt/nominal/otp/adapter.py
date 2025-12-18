import logging
import os
import requests

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from avl2gtfsrt.common.env import is_debug
from avl2gtfsrt.common.datetime import get_operating_day_time_str, get_operating_day_seconds
from avl2gtfsrt.model.types import StopTime, Stop, Trip, TripDescriptor
from avl2gtfsrt.nominal.baseadapter import BaseAdapter


class OtpAdapter(BaseAdapter):

    def __init__(self, endpoint: str, username: str|None = None, password: str|None = None):
        self._endpoint = endpoint
        self._username = username
        self._password = password
        
    def _request(self, query: str, variables: dict) -> dict:
        try:
            
            authentication: tuple|None = None
            if self._username is not None and self._password is not None:
                authentication = (self._username, self._password)
            
            response = requests.post(
                self._endpoint,
                json={
                    'query': query, 
                    'variables': variables
                },
                headers={
                    'Content-Type': 'application/json'
                },
                auth=authentication
            )
            
            response.raise_for_status()
            
            return response.json()
        except Exception as ex:
            if is_debug():
                logging.exception(ex)
            else:
                logging.error(str(ex)) 
            
            return None
        
    def _load_nearby_stops(self, lat: float, lon: float) -> list[str]:
        query: str = """
        query NearbyStops($lat: Float!, $lon: Float!) {
          stopsByRadius(lat: $lat, lon: $lon, radius: 200) {
            edges {
              node {
                distance,
                stop {
                  gtfsId
                }
              }
            }
          }
        }
        """

        variables: dict = {
            'lat': lat,
            'lon': lon
        }

        data: dict = self._request(query, variables)

        
        if data is not None and 'data' in data and 'stopsByRadius' in data['data'] and data['data']['stopsByRadius'] is not None and len(data['data']['stopsByRadius'].get('edges', [])) > 0:
            stop_ids: list[str] = list()

            for edge in data['data']['stopsByRadius']['edges']:
                if 'node' in edge and 'stop' in edge['node'] and 'gtfsId' in edge['node']['stop']:
                    stop_ids.append(edge['node']['stop']['gtfsId'])

            return stop_ids
        else:
            return []
        
    def _load_departing_trips(self, stop_id: str, reference_timestamp: datetime) -> list[dict[str, any]]:
        query: str = """
        query DepartingTrips($date: String!, $stopId: String!) {
          stop(id: $stopId) {
            stoptimesForServiceDate(date: $date) {
              stoptimes {
                scheduledArrival
                scheduledDeparture
                trip {
                  gtfsId
                  route {
                    gtfsId
                  }
                  tripGeometry {
                    points
                  }
                  stoptimes {
                    scheduledArrival
                    scheduledDeparture
                    stopPositionInPattern
                    stop {
                      gtfsId
                      name
                      lat
                      lon
                    }
                  }
                }
              }
            }
          }
        }
        """

        # check whether the current timestamp is before the end of the last operating day
        # if so, use the last calendar day as reference date
        reference_timestamp_midnight: int = int(reference_timestamp.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        operating_day_end_seconds: int = get_operating_day_seconds(os.getenv('A2G_OPERATING_DAY_END', '27:00:00')) - 86400

        if reference_timestamp.timestamp() <= reference_timestamp_midnight + operating_day_end_seconds:
            reference_date: datetime = reference_timestamp - timedelta(days=1)
        else:
            reference_date: datetime = reference_timestamp

        # construct variables and load data
        variables: dict = {
            'stopId': stop_id,
            'date': reference_date.strftime('%Y-%m-%d')
        }

        data: dict = self._request(query, variables)

        # process everything here
        if data is not None and 'data' in data and 'stop' in data['data'] and data['data']['stop'] is not None and len(data['data']['stop'].get('stoptimesForServiceDate', [])) > 0:
            stoptimes_for_service_date: dict = data['data']['stop'].get('stoptimesForServiceDate')

            trip_data: list[dict[str, any]] = list()
            for stoptimes_for_pattern in stoptimes_for_service_date:
                if 'stoptimes' in stoptimes_for_pattern and len(stoptimes_for_pattern['stoptimes']) > 0:
                    for stoptime in stoptimes_for_pattern['stoptimes']:
                        departure_timestamp: int = reference_timestamp_midnight + int(stoptime['scheduledDeparture'] if 'scheduledDeparture' in stoptime else stoptime['scheduledArrival'])
                        if departure_timestamp >= int(reference_timestamp.timestamp()):
                            trip: dict[str, any] = stoptime['trip']
                            trip['stopScheduledDeparture'] = departure_timestamp

                            trip_data.append(stoptime['trip'])

            return trip_data
        else:
            return []

    def _load_trips(self, lat: float, lon: float, reference_timestamp: datetime) -> list[dict[str, any]]:
        stop_ids: list[str] = self._load_nearby_stops(lat, lon)
        if len(stop_ids) == 0:
            logging.warning(f"{self.__class__.__name__}: No nearby stops found for coordinates ({lat}, {lon}).")

        trip_data: list[dict[str, any]] = list()
        for stop_id in stop_ids:
            departing_trips: list[dict[str, any]] = self._load_departing_trips(stop_id, reference_timestamp)
            if len(departing_trips) == 0:
                logging.debug(f"{self.__class__.__name__}: No departing trips found for stop {stop_id}.")

            trip_data.extend(departing_trips)

        trip_data = sorted(trip_data, key=lambda x: x['stopScheduledDeparture'])
        return trip_data[:20]
    
    def get_trip_candidates(self, lat: float, lon: float) -> list[Trip]:
        
        reference_timestamp: datetime = datetime.now(ZoneInfo(os.getenv('A2G_TIMEZONE', 'Europe/Berlin'))).replace(microsecond=0)
        reference_timestamp = reference_timestamp - timedelta(minutes=15)

        trips: list[Trip] = list()

        trip_data: list[dict[str, any]] = self._load_trips(lat, lon, reference_timestamp)
        for td in trip_data:
            
            # check some prequisites here, we don't want invalid trips at all ...            
            if 'tripGeometry' not in td or 'points' not in td['tripGeometry']:
                logging.debug(f"{self.__class__.__name__}: Trip {td['gtfsId']} contains no shape data and was discarded.")
                continue

            if 'stoptimes' not in td or len(td['stoptimes']) == 0:
                logging.debug(f"{self.__class__.__name__}: Trip {td['gtfsId']} contains no stop times and was discarded.")
                continue
            
            # here we go, the trip is valid, so process all other information into a dataclass
            reference_timestamp_midnight: int = int(reference_timestamp.replace(hour=0, minute=0, second=0).timestamp())

            stop_times: list[StopTime] = list()
            for std in td['stoptimes']:
                stop_time: StopTime = StopTime(
                    arrival_timestamp=reference_timestamp_midnight + int(std['scheduledArrival'] if 'scheduledArrival' in std else std['scheduledDeparture']),
                    departure_timestamp=reference_timestamp_midnight + int(std['scheduledDeparture'] if 'scheduledDeparture' in std else std['scheduledArrival']),
                    stop_sequence=std['stopPositionInPattern'],
                    stop=Stop(
                        stop_id=std['stop']['gtfsId'],
                        latitude=std['stop']['lat'],
                        longitude=std['stop']['lon']
                    )
                )

                stop_times.append(stop_time)
            
            # construct the final trip here ...
            trip: Trip = Trip(
                descriptor=TripDescriptor(
                    trip_id=td['gtfsId'],
                    route_id=td['route']['gtfsId'],
                    start_time = get_operating_day_time_str(stop_times[0].departure_timestamp - reference_timestamp_midnight),
                    start_date = reference_timestamp.strftime('%Y%m%d'),
                ),
                shape_polyline=td['tripGeometry']['points'],
                stop_times=stop_times
            )

            trips.append(trip)
        
        return trips