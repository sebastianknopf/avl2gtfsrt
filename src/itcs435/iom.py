
from paho.mqtt import client as mqtt
from pymongo import MongoClient

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
        pass

    def terminate(self) -> None:
        pass