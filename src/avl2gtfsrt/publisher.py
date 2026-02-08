import json
import logging
import time
import os

from google.transit import gtfs_realtime_pb2
from paho.mqtt import client as mqtt

from avl2gtfsrt.objectstorage import ObjectStorage
from avl2gtfsrt.events.eventsubscriber import EventSubscriber
from avl2gtfsrt.events.eventmessage import EventMessage
from avl2gtfsrt.gtfsrt.export import GtfsRealtimeExport

class GtfsRealtimePublisher:
    
    def __init__(self):
        # connect to local MongoDB
        mongodb_username: str = os.getenv('A2G_MONGODB_USERNAME', '')
        mongodb_password: str = os.getenv('A2G_MONGODB_PASSWORD', '')

        logging.info(f"{self.__class__.__name__}: Connecting to MongoDB ...")
        self._object_storage: ObjectStorage = ObjectStorage(
            mongodb_username, 
            mongodb_password,
            int(os.getenv('A2G_MATCHING_DATA_REVIEW_SECONDS', '120')),
            int(os.getenv('A2G_MATCHING_MAX_DATA_POINTS', '60'))
        )

        # load config string from ENVs
        try:
            self._organisation_id = os.getenv('A2G_ORGANISATION_ID', None)

            self._config: dict = json.loads(os.getenv('A2G_PUBLISHER_CONFIG', None))
            self._method = self._config.get('method', 'mqtt').lower()
        except Exception:
            logging.error(f"{self.__class__.__name__}: Variable A2G_PUBLISHER_CONFIG not set or invalid!")
            exit(1)

    def _setup_mqtt(self) -> None:
        mqtt_host: str = self._config.get('endpoint', None)
        mqtt_port: str = self._config.get('port', '1883')

        if mqtt_host is None:
            raise RuntimeError('MQTT host is not configured. Please configure a MQTT hostname or IP address.')

        self._mqtt = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, 
            protocol=mqtt.MQTTv5, 
            client_id=f"avl2gtfsrt-publisher-{self._organisation_id}"
        )
        
        mqtt_username: str|None = self._config.get('username', None)
        mqtt_password: str|None = self._config.get('password', None)

        # set username and password if provided
        if mqtt_username is not None and mqtt_password is not None:
            self._mqtt.username_pw_set(username=mqtt_username, password=mqtt_password)

        # finally connect to the broker ...
        logging.info(f"{self.__class__.__name__}: Connecting to MQTT broker at {mqtt_host}:{mqtt_port} ...")
        self._mqtt.connect(mqtt_host, int(mqtt_port))

        self._mqtt.loop_forever()

    def _send(self, vehicle_id: str, data_type: str, message: gtfs_realtime_pb2.FeedMessage|str) -> None:
        
        if isinstance(message, str):
            logging.info(f"{self.__class__.__name__}: Sending message for vehicle {vehicle_id} and data type {data_type} ...")
        
        if self._method == 'mqtt':
            topic: str = self._config.get('topic', 'gtfsrt/{dataType}/{vehicleId}')
            topic = topic.format(
                organisationId=self._organisation_id,
                dataType=data_type,
                vehicleId=vehicle_id
            )

            self._mqtt.publish(topic, message, qos=0)
        elif self._method == 'get':
            raise NotImplementedError()
        elif self._method == 'post':
            raise NotImplementedError()

    def _on_event_message(self, message: EventMessage):
        logging.info(f"{self.__class__.__name__}: Received message {message}")

        gtfsrt_export: GtfsRealtimeExport = GtfsRealtimeExport(self._object_storage)

        if message.event_type == EventMessage.TECHNICAL_VEHICLE_LOG_ON:
            pass
        elif message.event_type == EventMessage.TECHNICAL_VEHICLE_LOG_OFF:
            pass
        elif message.event_type == EventMessage.OPERATIONAL_VEHICLE_LOG_ON:
            pass
        elif message.event_type == EventMessage.OPERATIONAL_VEHICLE_LOG_OFF:
            pass
        elif message.event_type == EventMessage.GNSS_PHYSICAL_POSITION_UPDATE:
            pass
    
        self._send(message.vehicle_id, 'vehiclepositions', gtfsrt_export.export_differential_vehicle_positions(message.vehicle_id, debug=True))
        self._send(message.vehicle_id, 'tripupdates', gtfsrt_export.export_differential_trip_updates(vehicle_id=message.vehicle_id, debug=True))
    
    def run(self):

        self._event_stream: EventSubscriber = EventSubscriber()
        self._event_stream.on_event_message = self._on_event_message
        
        self._event_stream.start()

        if self._method == 'mqtt':
            self._setup_mqtt()
        elif self._method == 'get':
            raise NotImplementedError()
        elif self._method == 'post':
            raise NotImplementedError()