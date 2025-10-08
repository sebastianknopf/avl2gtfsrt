import logging
import requests

from datetime import datetime, timezone, timedelta

from avl2gtfsrt.common.env import is_debug
from avl2gtfsrt.nominal.baseadapter import BaseAdapter


class OtpAdapter(BaseAdapter):

    def __init__(self, endpoint: str, username: str|None = None, password: str|None = None):
        self._endpoint = endpoint
        self._username = username
        self._password = password
        
    def get_trip_candidates(self, lat: float, lon: float) -> list[dict]:
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

        if data is not None and 'data' in data and 'nearest' in data['data'] and len(data['data']['nearest'].get('edges', [])) > 0:
            return data['data']['nearest'].get('edges', [])[0].get('node', {}).get('place', {}).get('estimatedCalls', [])
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