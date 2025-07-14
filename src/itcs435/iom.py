import logging
import re

from paho.mqtt import client as mqtt
from pymongo import MongoClient

from itcs435.vdv435 import AbstractBasicStructure
from itcs435.vdv435 import AbstractMessageStructure
from itcs435.vdv435 import Serializable
from itcs435.vdv435 import TestParentClassStructure, TestSubClassStructure
from itcs435.siri.publisher import Publisher

class IoM:

    def __init__(self, organisation_id: str, itcs_id: str, mqtt_client: mqtt.Client, mongo_client: MongoClient, siri_publisher: Publisher) -> None:
        self._organisation_id = organisation_id
        self._itcs_id = itcs_id
        self._mqtt_client = mqtt_client
        self._mongo_client = mongo_client
        self._siri_publisher = siri_publisher

        # create TLS topic structures
        self._tls_sub_itcs_inbox = (f"IoM/1.0/DataVersion/+/Inbox/ItcsInbox/Country/de/+/Organisation/{self._organisation_id}/+/ItcsId/{self._itcs_id}/#", 2)
        self._tls_pub_vehicle_inbox = (f"IoM/1.0/DataVersion/+/Inbox/VehicleInbox/Country/de/+/Organisation/{self._organisation_id}/+/VehicleId/", 2)
        self._tls_sub_vehicle_physical_position = (f"IoM/1.0/DataVersion/+/Country/de/+/Organisation/{self._organisation_id}/+/Vehicle/+/+/PhysicalPosition/#", 0)
        self._tls_sub_vehicle_logical_position = (f"IoM/1.0/DataVersion/+/Country/de/+/Organisation/{self._organisation_id}/+/Vehicle/+/+/LogicalPositionData", 0)

    def get_subscribed_topics(self) -> tuple[str, int]:
        return [
            self._tls_sub_itcs_inbox,
            self._tls_sub_vehicle_physical_position,
            self._tls_sub_vehicle_logical_position
        ]
    
    def process(self, topic: str, payload: bytes) -> None:
        if self._topic_matches(topic, self._tls_sub_itcs_inbox[0]):
            self._handle_request(topic, payload)
        else:
            self._handle_message(topic, payload)

    def terminate(self) -> None:
        pass

    def _handle_request(self, topic: str, payload: bytes) -> None:
        # lookup for correlation ID in the topic
        topic_components: list[str] = topic.split('/')
        if 'CorrelationId' in topic_components:
            correlation_id: str = topic_components[topic_components.index('CorrelationId') + 1]
        else:
            raise LookupError(f"Request CorrelationId not found in topic {topic}")
        
        # handle request based on the topic
        

    def _handle_message(self, topic: str, payload: bytes) -> None:
        pass
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        regex = re.escape(pattern)
        regex = regex.replace(r'\+', '[^/]+')
        regex = regex.replace(r'\#', '.*')
        regex = '^' + regex + '$'

        return re.match(regex, topic) is not None