import logging
import requests

from datetime import datetime, timezone

from itcs435.common.env import is_debug

class OtpClient:

    def __init__(self, endpoint: str):
        self._endpoint = endpoint
        
    def get_trip_candidates(self, lat: float, lon: float) -> dict:
        query = """
        query TripCandidates($lat: Float!, $lon: Float!, $startTime: DateTime!) {
          nearest(latitude: $lat, longitude: $lon, maximumDistance: 200, filterByPlaceTypes:stopPlace) {
            edges {
              node {
                distance,
                place {
                  ... on StopPlace {
                    id,
                    estimatedCalls(startTime: $startTime, numberOfDepartures: 5) {
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
                          aimedArrivalTime,
                          aimedDepartureTime,
                            quay {
                            id,
                            latitude,
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
        
        variables = {
          'lat': lat,
          'lon': lon,
          'startTime': datetime.now(timezone.utc).isoformat()
        }
        
        data: dict = self._request(query, variables)
        return data.get('data', {}).get('nearest', {})
        
    def _request(self, query: str, variables: dict) -> dict:
        try:
            response = requests.post(
                self._endpoint,
                json={
                    'query': query, 
                    'variables': variables
                },
                headers={
                    'Content-Type': 'application/json'
                }
            )
            
            response.raise_for_status()
            
            return response.json()
        except Exception as ex:
            if is_debug():
                logging.exception(ex)
            else:
                logging.error(str(ex)) 
            
            return None