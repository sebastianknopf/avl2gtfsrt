import logging
import re

from paho.mqtt import client as mqtt

from itcs435.common.serialization import Serializable
from itcs435.vdv.vdv435 import AbstractBasicStructure, AbstractMessageStructure
from itcs435.vdv.vdv435 import TechnicalVehicleLogOnRequestStructure, TechnicalVehicleLogOnResponseStructure
from itcs435.vdv.vdv435 import TechnicalVehicleLogOnResponseDataStructure, TechnicalVehicleLogOnResponseErrorStructure
from itcs435.vdv.vdv435 import TechnicalVehicleLogOffRequestStructure, TechnicalVehicleLogOffResponseStructure
from itcs435.vdv.vdv435 import TechnicalVehicleLogOffResponseDataStructure, TechnicalVehicleLogOffResponseErrorStructure
from itcs435.storage import Storage
from itcs435.siri.publisher import Publisher

class TopicLevelStructureDict(dict):
    def __missing__(self, key):
        return f"{{{key}}}"
    
class IomProcessor:

    def __init__(self, organisation_id: str, itcs_id: str, mqtt_client: mqtt.Client, storage: Storage, siri_publisher: Publisher) -> None:
        self._organisation_id = organisation_id
        self._itcs_id = itcs_id
        self._mqtt_client = mqtt_client
        self._storage = storage
        self._siri_publisher = siri_publisher

        # create TLS topic structures
        self._tls_sub_itcs_inbox = ("IoM/1.0/DataVersion/+/Inbox/ItcsInbox/Country/de/+/Organisation/{organisation_id}/+/ItcsId/{itcs_id}/#", 2)
        self._tls_pub_vehicle_inbox = ("IoM/1.0/DataVersion/{data_version}/Inbox/VehicleInbox/Country/de/any/Organisation/{organisation_id}/any/VehicleId/{vehicle_id}/CorrelationId/{correlation_id}/ResponseData", 2)
        self._tls_sub_vehicle_physical_position = ("IoM/1.0/DataVersion/+/Country/de/+/Organisation/{organisation_id}/+/Vehicle/+/+/PhysicalPosition/#", 0)
        self._tls_sub_vehicle_logical_position = ("IoM/1.0/DataVersion/+/Country/de/+/Organisation/{organisation_id}/+/Vehicle/+/+/LogicalPositionData", 0)

        # keep track of all global placeholders here
        # used in _get_tls method later
        self._tls_dict: TopicLevelStructureDict = TopicLevelStructureDict()
        self._tls_dict['organisation_id'] = self._organisation_id
        self._tls_dict['itcs_id'] = self._itcs_id

    def get_subscribed_topics(self) -> tuple[str, int]:
        subscribed_topics: list = [
            self._get_tls('sub_itcs_inbox'),
            self._get_tls('sub_vehicle_physical_position'),
            self._get_tls('sub_vehicle_logical_position')
        ]
        
        return subscribed_topics
    
    def process(self, topic: str, payload: bytes) -> None:
        if self._tls_matches(topic, 'sub_itcs_inbox'):
            self._handle_request(topic, payload)
        else:
            self._handle_message(topic, payload)

    def terminate(self) -> None:
        pass

    def _handle_request(self, topic: str, payload: bytes) -> None:
        # lookup for correlation ID in the topic
        data_version: str = self._get_tls_value(topic, 'DataVersion')
        correlation_id: str = self._get_tls_value(topic, 'CorrelationId')
        
        # handle request based on the topic
        msg: AbstractBasicStructure = Serializable.load(payload)

        # check if the message is subclass of AbstractMessageStructure
        # other classes are not meant to be used in request / response pattern
        if not issubclass(msg.__class__, AbstractMessageStructure):
            raise TypeError(f"{msg.__class__.__name__} is not subclass of AbstractMessageStructure and not usable in Request/Response")
        
        # handle request
        if isinstance(msg, TechnicalVehicleLogOnRequestStructure):
            vehicle_ref: str = msg.vehicle_ref.value

            vehicle = self._storage.get_vehicle(vehicle_ref)
            if vehicle is not None and vehicle.get('is_technically_logged_on', False):
                response: TechnicalVehicleLogOnResponseStructure = TechnicalVehicleLogOnResponseStructure()
                response.common_reponse_code = 'messageUnderstood'
                response.technical_vehicle_log_on_response_error = TechnicalVehicleLogOnResponseErrorStructure(
                    TechnicalVehicleLogOnResponseCode='doubleLogOn'
                )
            else:
                self._storage.update_vehicle(vehicle_ref, {
                    'is_technically_logged_on': True
                })

                response: TechnicalVehicleLogOnResponseStructure = TechnicalVehicleLogOnResponseStructure()
                response.technical_vehicle_log_on_response_data = TechnicalVehicleLogOnResponseDataStructure()

            self._publish_message(
                'pub_vehicle_inbox', 
                response.xml(),
                data_version=data_version,
                vehicle_id=vehicle_ref,
                correlation_id=correlation_id
            )

        elif isinstance(msg, TechnicalVehicleLogOffRequestStructure):
            vehicle_ref: str = msg.vehicle_ref.value

            vehicle = self._storage.get_vehicle(vehicle_ref)
            if vehicle is not None and not vehicle.get('is_technically_logged_on', False):
                response: TechnicalVehicleLogOffResponseStructure = TechnicalVehicleLogOffResponseStructure()
                response.common_reponse_code = 'messageUnderstood'
                response.technical_vehicle_log_off_response_error = TechnicalVehicleLogOffResponseErrorStructure(
                    TechnicalVehicleLogOffResponseCode='vehicleNotLoggedOn'
                )
            else:
                self._storage.update_vehicle(
                    vehicle_ref,
                    {'is_technically_logged_on': False}
                )

                response: TechnicalVehicleLogOffResponseStructure = TechnicalVehicleLogOffResponseStructure()
                response.technical_vehicle_log_off_response_data = TechnicalVehicleLogOffResponseDataStructure()

            self._publish_message(
                'pub_vehicle_inbox', 
                response.xml(),
                data_version=data_version,
                vehicle_id=vehicle_ref,
                correlation_id=correlation_id
            )


    def _handle_message(self, topic: str, payload: bytes) -> None:
        pass
    
    def _tls_matches(self, topic: str, tls_name: str) -> bool:
        tls_str: str = self._get_tls(tls_name)[0]
        
        regex = re.escape(tls_str)
        regex = regex.replace(r'\+', '[^/]+')
        regex = regex.replace(r'\#', '.*')
        regex = '^' + regex + '$'

        return re.match(regex, topic) is not None
    
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
    
    def _get_tls_value(self, topic: str, key: str, fail_on_error: bool = True) -> str|None:
        topic_components: list[str] = topic.split('/')
        if key in topic_components:
            result: str = topic_components[topic_components.index(key) + 1]

            return result
        else:
            if fail_on_error:
                raise LookupError(f"Key {key} not found in topic {topic}")
        
        return None
        
    def _publish_message(self, tls_name: str, payload: str, retain=False, **arguments):
        tls: tuple[str, int] = self._get_tls(tls_name)

        tls_str: str = tls[0]
        tls_str = tls_str.format(**arguments)

        self._mqtt_client.publish(
            tls_str,
            payload,
            tls[1],
            retain
        )

        logging.info(f"Published message to topic: {tls_str}")
