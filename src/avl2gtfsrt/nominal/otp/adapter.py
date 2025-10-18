import logging
import requests

from datetime import datetime, timezone, timedelta

from avl2gtfsrt.common.env import is_debug
from avl2gtfsrt.common.datetime import get_operation_day, get_operation_time
from avl2gtfsrt.model.types import StopTime, Stop, Trip, TripDescriptor
from avl2gtfsrt.nominal.baseadapter import BaseAdapter


class OtpAdapter(BaseAdapter):

    def __init__(self, endpoint: str, username: str|None = None, password: str|None = None):
        self._endpoint = endpoint
        self._username = username
        self._password = password
        
    def get_trip_candidates(self, lat: float, lon: float) -> list[Trip]:
        query = """
        query TripCandidates($lat: Float!, $lon: Float!, $startTime: DateTime!) {
          nearest(latitude: $lat, longitude: $lon, maximumDistance: 200, filterByPlaceTypes: stopPlace) {
            edges {
              node {
                distance,
                place {
                  ... on StopPlace {
                    id,
                    estimatedCalls(startTime: $startTime, numberOfDepartures: 20) {
                      date
                      serviceJourney {
                        id,
                        journeyPattern {
                          line {
                            id
                          }
                        }
                        pointsOnLink {
                          points
                        }
                        estimatedCalls {
                          aimedArrivalTime
                          aimedDepartureTime
                          stopPositionInPattern
                          quay {
                            id
                            latitude
                            longitude
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        reference_timestamp: datetime = datetime.now(timezone.utc).replace(microsecond=0)
        reference_timestamp = reference_timestamp - timedelta(minutes=15)

        variables: dict = {
          'lat': lat,
          'lon': lon,
          'startTime': reference_timestamp.isoformat()
        }
        
        data: dict = self._request(query, variables)

        if data is not None and 'data' in data and 'nearest' in data['data'] and data['data']['nearest'] is not None and len(data['data']['nearest'].get('edges', [])) > 0:
            trip_data: list[dict] = data['data']['nearest'].get('edges', [])[0].get('node', {}).get('place', {}).get('estimatedCalls', [])
            trips: list[Trip] = list()

            for td in trip_data:
                
                # check some prequisites here, we don't want invalid trips at all ...
                if 'serviceJourney' not in td or 'estimatedCalls' not in td['serviceJourney']:
                    logging.warning(f"{self.__class__.__name__}: Trip result contains no serviceJourney data and was discarded.")

                if len(td['serviceJourney']['estimatedCalls']) == 0:
                    logging.warning(f"{self.__class__.__name__}: Trip {td['serviceJourney']['id']} contains no estimated calls and was discarded.")

                if 'pointsOnLink' not in td['serviceJourney'] or 'points' not in td['serviceJourney']['pointsOnLink']:
                    logging.warning(f"{self.__class__.__name__}: Trip {td['serviceJourney']['id']} contains no shape data and was discarded.")
                
                # here we go, the trip is valid, so process all other information into a dataclass
                stop_times: list[StopTime] = list()
                for std in td['serviceJourney']['estimatedCalls']:
                    stop_time: StopTime = StopTime(
                        arrival_timestamp=int(datetime.fromisoformat(std['aimedDepartureTime'] if 'aimedDepartureTime' in std else std['aimedArrivalTime']).timestamp()),
                        departure_timestamp=int(datetime.fromisoformat(std['aimedDepartureTime'] if 'aimedDepartureTime' in std else std['aimedArrivalTime']).timestamp()),
                        stop_sequence=std['stopPositionInPattern'],
                        stop=Stop(
                            stop_id=std['quay']['id'],
                            latitude=std['quay']['latitude'],
                            longitude=std['quay']['longitude']
                        )
                    )

                    stop_times.append(stop_time)
                
                # construct the final trip here ...
                trip: Trip = Trip(
                    descriptor=TripDescriptor(
                        trip_id=td['serviceJourney']['id'],
                        route_id=td['serviceJourney']['journeyPattern']['line']['id'],
                        start_time = get_operation_time(
                            td['date'],
                            td['serviceJourney']['estimatedCalls'][0]['aimedDepartureTime']
                        ),
                        start_date = get_operation_day(td['date'])
                    ),
                    shape_polyline=td['serviceJourney']['pointsOnLink']['points'],
                    stop_times=stop_times
                )

                trips.append(trip)
            
            return trips
        else: 
            return []
        
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