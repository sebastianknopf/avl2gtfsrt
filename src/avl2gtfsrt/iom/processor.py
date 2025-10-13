import logging
import re

from paho.mqtt import client as mqtt

from avl2gtfsrt.common.mqtt import get_tls_value
from avl2gtfsrt.common.serialization import Serializable
from avl2gtfsrt.common.datetime import get_operation_day, get_operation_time
from avl2gtfsrt.vdv.vdv435 import AbstractBasicStructure, AbstractMessageStructure, AbstractDataPublicationStructure
from avl2gtfsrt.vdv.vdv435 import TechnicalVehicleLogOnRequestStructure
from avl2gtfsrt.vdv.vdv435 import TechnicalVehicleLogOffRequestStructure
from avl2gtfsrt.vdv.vdv435 import GnssPhysicalPositionDataStructure
from avl2gtfsrt.iom.logonoffhandler import TechnicalVehicleLogOnHandler
from avl2gtfsrt.iom.logonoffhandler import TechnicalVehicleLogOffHandler
from avl2gtfsrt.iom.positioninghandler import GnssPhysicalPositionHandler
from avl2gtfsrt.objectstorage import ObjectStorage

class TopicLevelStructureDict(dict):
    def __missing__(self, key):
        return f"{{{key}}}"
    
class IomProcessor:

    def __init__(self, organisation_id: str, itcs_id: str, mqtt_client: mqtt.Client, storage: ObjectStorage) -> None:
        self._organisation_id = organisation_id
        self._itcs_id = itcs_id
        self._mqtt_client = mqtt_client
        self._storage = storage

        # create TLS topic structures
        self._tls_sub_itcs_inbox = ("IoM/1.0/DataVersion/+/Inbox/ItcsInbox/Country/de/+/Organisation/{organisation_id}/+/ItcsId/{itcs_id}/#", 2)
        self._tls_pub_vehicle_inbox = ("IoM/1.0/DataVersion/{data_version}/Inbox/VehicleInbox/Country/de/any/Organisation/{organisation_id}/any/VehicleId/{vehicle_id}/CorrelationId/{correlation_id}/ResponseData", 2)
        self._tls_sub_vehicle_physical_position = ("IoM/1.0/DataVersion/+/Country/de/+/Organisation/{organisation_id}/+/Vehicle/+/+/PhysicalPosition/#", 0)

        # keep track of all global placeholders here
        # used in _get_tls method later
        self._tls_dict: TopicLevelStructureDict = TopicLevelStructureDict()
        self._tls_dict['organisation_id'] = self._organisation_id
        self._tls_dict['itcs_id'] = self._itcs_id

    def get_subscribed_topics(self) -> tuple[str, int]:
        subscribed_topics: list = [
            self._get_tls('sub_itcs_inbox'),
            self._get_tls('sub_vehicle_physical_position')
        ]
        
        return subscribed_topics
    
    def process(self, topic: str, payload: bytes) -> None:
        logging.info(f"{self.__class__.__name__}: Received message in topic {topic}")
        
        if self._tls_matches(topic, 'sub_itcs_inbox'):
            self._handle_request(topic, payload)
        else:
            self._handle_message(topic, payload)

    def terminate(self) -> None:
        pass

    def _handle_request(self, topic: str, payload: bytes) -> None:
        # lookup for correlation ID in the topic
        data_version: str = get_tls_value(topic, 'DataVersion')
        correlation_id: str = get_tls_value(topic, 'CorrelationId')
        
        # handle request based on the topic
        msg: AbstractBasicStructure = Serializable.load(payload)

        # check if the message is subclass of AbstractMessageStructure
        # other classes are not meant to be used in request / response pattern
        if not issubclass(msg.__class__, AbstractMessageStructure):
            raise TypeError(f"{msg.__class__.__name__} is not subclass of AbstractMessageStructure and not usable in Request/Response")
        
        # handle request
        if isinstance(msg, TechnicalVehicleLogOnRequestStructure):
            handler: TechnicalVehicleLogOnHandler = TechnicalVehicleLogOnHandler(self._storage)
            response: AbstractBasicStructure = handler.handle_request(msg)

            vehicle_ref: str = msg.vehicle_ref.value

            self._publish(
                'pub_vehicle_inbox', 
                response.xml(),
                data_version=data_version,
                vehicle_id=vehicle_ref,
                correlation_id=correlation_id
            )

        elif isinstance(msg, TechnicalVehicleLogOffRequestStructure):
            handler: TechnicalVehicleLogOffHandler = TechnicalVehicleLogOffHandler(self._storage)
            response: AbstractBasicStructure = handler.handle_request(msg)

            vehicle_ref: str = msg.vehicle_ref.value

            self._publish(
                'pub_vehicle_inbox', 
                response.xml(),
                data_version=data_version,
                vehicle_id=vehicle_ref,
                correlation_id=correlation_id
            )

    def _handle_message(self, topic: str, payload: bytes) -> None:
        
        # handle message based on the topic
        msg: AbstractBasicStructure = Serializable.load(payload)

        # check if the message is subclass of AbstractDataPublicationStructure
        # other classes are not meant to be used in pub / sub pattern
        if not issubclass(msg.__class__, AbstractDataPublicationStructure):
            raise TypeError(f"{msg.__class__.__name__} is not subclass of AbstractDataPublicationStructure and not usable in Pub/Sub")
        
        # lookup for IDs which will be required for all handler results
        vehicle_ref: str = get_tls_value(topic, 'Vehicle')

        # handle message
        if isinstance(msg, GnssPhysicalPositionDataStructure):
            handler: GnssPhysicalPositionHandler = GnssPhysicalPositionHandler(self._storage)
            result: dict = handler.handle(topic, msg)

            if result is not None and result['handler_success']:
                if result['handler_result'] is not None and result['handler_result']['trip_convergence']:
                    trip: dict = result['handler_result']['trip_candidate']
                    
                    self._storage.update_vehicle(
                        vehicle_ref,
                        {'is_operationally_logged_on': True}
                    )

                    self._storage.update_vehicle_activity(
                        vehicle_ref,
                        {
                            'trip_descriptor': {
                                'trip_id': trip['serviceJourney']['id'],
                                'route_id': trip['serviceJourney']['journeyPattern']['line']['id'],
                                'start_time': get_operation_time(
                                    trip['date'],
                                    trip['serviceJourney']['estimatedCalls'][0]['aimedDepartureTime']
                                ),
                                'start_date': get_operation_day(trip['date'])
                            }
                        }
                    )

                    self._storage.update_trip(
                        trip['serviceJourney']['id'],
                        trip
                    )

    def _get_tls(self, tls_name: str) -> tuple[str, int]:
        if not tls_name.startswith('_tls_'):
            tls_name = f"_tls_{tls_name}"

        tls: tuple = getattr(self, tls_name, None)
        if tls is not None and isinstance(tls, tuple):
            tls_str: str = tls[0]
            tls_str = tls_str.format_map(self._tls_dict)

            return (tls_str, tls[1])
        else:
            raise ValueError(f"Undefined TLS {tls_name} not found!")
    
    def _tls_matches(self, topic: str, tls_name: str) -> bool:
        tls_str: str = self._get_tls(tls_name)[0]
        
        regex = re.escape(tls_str)
        regex = regex.replace(r'\+', '[^/]+')
        regex = regex.replace(r'\#', '.*')
        regex = '^' + regex + '$'

        return re.match(regex, topic) is not None
        
    def _publish(self, tls_name: str, payload: str, retain=False, **arguments):
        tls: tuple[str, int] = self._get_tls(tls_name)

        tls_str: str = tls[0]
        tls_str = tls_str.format(**arguments)

        self._mqtt_client.publish(
            tls_str,
            payload,
            tls[1],
            retain
        )

        logging.info(f"{self.__class__.__name__}: Published message to topic {tls_str}")
