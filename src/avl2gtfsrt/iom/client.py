import logging
import re

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from paho.mqtt import client as mqtt
from threading import Condition
from threading import Lock
from queue import Queue

from avl2gtfsrt.common.env import is_debug
from avl2gtfsrt.common.mqtt import get_tls_value
from avl2gtfsrt.common.serialization import Serializable
from avl2gtfsrt.vdv.vdv435 import *
from avl2gtfsrt.iom.logonoffhandler import TechnicalVehicleLogOnHandler
from avl2gtfsrt.iom.logonoffhandler import TechnicalVehicleLogOffHandler
from avl2gtfsrt.iom.positioninghandler import GnssPhysicalPositionHandler
from avl2gtfsrt.objectstorage import ObjectStorage


class TopicLevelStructureDict(dict):
    def __missing__(self, key):
        return f"{{{key}}}"
    
class IomRole:
    ITCS = 1
    VEHICLE = 2
    
class IomClient:

    def __init__(self, config: dict, iom_role: IomRole, object_storage: ObjectStorage, thread_executor: ThreadPoolExecutor) -> None:
        self.instance_id: str = config['instance_id']
        self.organisation_id = config['organisation_id']
        self.itcs_id = config['itcs_id']

        self._role = iom_role
        self._storage = object_storage
        self._executor = thread_executor

        # setup internal thread handling members
        self._vehicle_locks: dict[str, bool] = dict()
        self._vehicle_queues: dict[str, Queue] = dict()
        self._lock = Lock()

        # correlation ID and latch for running requests via MQTT
        self._correlation_id: str|None = None
        self._correlation_result: str|None = None
        self._correlation_condition: Condition = Condition()

        # create MQTT client
        self._mqtt: mqtt.Client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, 
            protocol=mqtt.MQTTv5, 
            client_id=f"avl2gtfsrt-IoM-{self.organisation_id}"
        )

        # create TLS topic structures
        self._tls_sub_itcs_inbox: tuple[str, int] = ("IoM/1.0/DataVersion/+/Inbox/ItcsInbox/Country/de/+/Organisation/{organisation_id}/+/ItcsId/{itcs_id}/#", 2)
        self._tls_pub_vehicle_inbox: tuple[str, int] = ("IoM/1.0/DataVersion/{data_version}/Inbox/VehicleInbox/Country/de/any/Organisation/{organisation_id}/any/VehicleId/{vehicle_id}/CorrelationId/{correlation_id}/ResponseData", 2)
        self._tls_sub_vehicle_physical_position: tuple[str, int] = ("IoM/1.0/DataVersion/+/Country/de/+/Organisation/{organisation_id}/+/Vehicle/+/+/PhysicalPosition/#", 0)

        self._tls_pub_itcs_inbox: tuple[str, int] = ("IoM/1.0/DataVersion/any/Inbox/ItcsInbox/Country/de/any/Organisation/{organisation_id}/any/ItcsId/{itcs_id}/CorrelationId/{correlation_id}/RequestData", 2)
        self._tls_sub_vehicle_inbox: tuple[str, int] = ("IoM/1.0/DataVersion/+/Inbox/VehicleInbox/Country/de/+/Organisation/{organisation_id}/+/VehicleId/+/CorrelationId/+/ResponseData", 2)
        self._tls_pub_vehicle_physical_position: tuple[str, int] = ("IoM/1.0/DataVersion/any/Country/de/any/Organisation/{organisation_id}/any/Vehicle/{vehicle_ref}/any/PhysicalPosition/GnssPhysicalPositionData", 0)
        
        # keep track of all global placeholders here
        # used in _get_tls method later
        self._tls_dict: TopicLevelStructureDict = TopicLevelStructureDict()
        self._tls_dict['organisation_id'] = self.organisation_id
        self._tls_dict['itcs_id'] = self.itcs_id

        # set MQTT parameters
        self._mqtt_host: str|None = config['host'] if 'host' in config else None
        self._mqtt_port: str|None = config['port'] if 'port' in config else '1883'
        self._mqtt_username: str|None = config['username'] if 'username' in config else None
        self._mqtt_password: str|None = config['password'] if 'password' in config else None
        
        if self._mqtt_host is None:
            raise RuntimeError('MQTT host is not configured. Please configure a MQTT hostname or IP address.')

    def get_subscribed_topics(self) -> tuple[str, int]:
        if self._role == IomRole.ITCS:
            subscribed_topics: list = [
                self._get_tls('sub_itcs_inbox'),
                self._get_tls('sub_vehicle_physical_position')
            ]
        elif self._role == IomRole.VEHICLE:
            subscribed_topics: list = [
            self._get_tls('sub_vehicle_inbox')
        ]

        return subscribed_topics
    
    def start(self) -> None:
        # define MQTT callback methods
        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_message = self._on_message
        self._mqtt.on_disconnect = self._on_disconnect

        # set username and password if provided
        if self._mqtt_username is not None and self._mqtt_password is not None:
            self._mqtt.username_pw_set(username=self._mqtt_username, password=self._mqtt_password)

        # finally connect to the broker ...
        logging.info(f"{self.instance_id}/{self.__class__.__name__}: Connecting to MQTT broker at {self._mqtt_host}:{self._mqtt_port} ...")
        self._mqtt.connect(self._mqtt_host, int(self._mqtt_port))
        
        self._mqtt.loop_start()
    
    def process(self, topic: str, payload: bytes) -> None:
        logging.info(f"{self.instance_id}/{self.__class__.__name__}: Received message in topic {topic}")
        
        if self._role == IomRole.ITCS and self._tls_matches(topic, 'sub_itcs_inbox'):
            # if we're waiting for a response, handle the incoming message as response
            # otherwise handle it as request
            if self._correlation_id is None:
                self._handle_request(topic, payload)
            else:
                self._handle_reponse(topic, payload)
        elif self._role == IomRole.VEHICLE and self._tls_matches(topic, 'sub_vehicle_inbox'):
            # if we're waiting for a response, handle the incoming message as response
            # otherwise handle it as request
            if self._correlation_id is None:
                self._handle_request(topic, payload)
            else:
                self._handle_reponse(topic, payload)
        else:
            self._handle_message(topic, payload)

    def terminate(self) -> None:
        logging.info(f"{self.instance_id}/{self.__class__.__name__}: Shutting down MQTT connection ...")
        self._mqtt.disconnect()

        self._mqtt.loop_stop()

    def log_on_vehicle(self, vehicle_ref: str) -> bool:
        if self._role == IomRole.VEHICLE:
            vehicle_ref: VehicleRef = VehicleRef(**{'#text': vehicle_ref})
            
            log_on_message: TechnicalVehicleLogOnRequestStructure = TechnicalVehicleLogOnRequestStructure(**{
                'netex:VehicleRef': vehicle_ref
            })

            response: TechnicalVehicleLogOnResponseStructure = self._request('pub_itcs_inbox', log_on_message.xml())
            if response.technical_vehicle_log_on_response_error is not None:
                response_code: str = response.technical_vehicle_log_on_response_error.technical_vehicle_log_on_response_code
                raise RuntimeError(f"Failed to log on vehicle {vehicle_ref}, Response: {response_code}!")
            else:
                logging.info(f"{self.instance_id}/{self.__class__.__name__}: Vehicle {vehicle_ref} successfully logged on.")

    def log_off_vehicle(self, vehicle_ref: str) -> bool:
        if self._role == IomRole.VEHICLE:
            vehicle_ref: VehicleRef = VehicleRef(**{'#text': vehicle_ref})
            
            log_off_message: TechnicalVehicleLogOffRequestStructure = TechnicalVehicleLogOffRequestStructure(**{
                'netex:VehicleRef': vehicle_ref
            })

            response: TechnicalVehicleLogOffResponseStructure = self._request('pub_itcs_inbox', log_off_message.xml())
            if response.technical_vehicle_log_off_response_error is not None:
                response_code: str = response.technical_vehicle_log_off_response_error.technical_vehicle_log_off_response_code
                raise RuntimeError(f"Failed to log on vehicle {vehicle_ref}, Response: {response_code}!")
            else:
                logging.info(f"{self.instance_id}/{self.__class__.__name__}: Vehicle {vehicle_ref} successfully logged off.")

    def publish_gnss_position_update(self, vehicle_ref: str, latitude: float, longitude: float, timestamp: datetime) -> None:
        if self._role == IomRole.VEHICLE:
            timestamp_of_measurement: str = timestamp.replace(microsecond=0).isoformat()
            
            gnss_physical_position_structure: GnssPhysicalPositionDataStructure = GnssPhysicalPositionDataStructure(
                PublisherId=self._mqtt._client_id,
                TimestampOfMeasurement=timestamp_of_measurement,
                GnssPhysicalPosition=GnssPhysicalPosition(
                    WGS84PhysicalPosition=WGS84PhysicalPosition(
                        Latitude=latitude,
                        Longitude=longitude
                    )
                )
            )

            self._publish(
                'pub_vehicle_physical_position', 
                gnss_physical_position_structure.xml(), 
                retain=True,
                vehicle_ref=vehicle_ref
            )
        else:
            raise RuntimeError("Only clients with role type VEHICLE are allowed to publish GNSS position updates.")
    
    def _on_connect(self, client, userdata, flags, rc, properties):
        if not rc.is_failure:
            for topic, qos in self.get_subscribed_topics():
                logging.info(f"{self.instance_id}/{self.__class__.__name__}: Subscribing to topic: {topic}")
                self._mqtt.subscribe(topic, qos=qos)
        else:
            raise RuntimeError("Failed to connect to the IoM MQTT broker.")

    def _on_message(self, client, userdata, message):
        try:
            self.process(message.topic, message.payload)
        except Exception as ex:
            if is_debug():
                logging.exception(ex)
            else:
                logging.error(str(ex))

    def _on_disconnect(self, client, userdata, flags, rc, properties):
        for topic, qos in self.get_subscribed_topics():
            logging.info(f"{self.instance_id}/{self.__class__.__name__}: Unsubscribing from topic: {topic}")
            self._mqtt.unsubscribe(topic)
    
    def _publish(self, tls_name: str, payload: str, retain=False, **arguments):
        tls: tuple[str, int] = self._get_tls(tls_name)

        tls_str: str = tls[0]
        tls_str = tls_str.format(**arguments)

        self._mqtt.publish(
            tls_str,
            payload,
            tls[1],
            retain
        )

        logging.info(f"{self.instance_id}/{self.__class__.__name__}: Published message to topic {tls_str}")

    def _request(self, tls_name: str, payload: str, **arguments) -> AbstractResponseStructure:
        if self._correlation_id is None:
            self._correlation_id = '1'
        
        self._publish(tls_name, payload, False, correlation_id=self._correlation_id)

        with self._correlation_condition:
            self._correlation_condition.wait(timeout=30)   
            
            self._correlation_id = None
            self._correlation_result = None

            if self._correlation_result is not None:
                response: AbstractResponseStructure = Serializable.load(self._correlation_result)
                return response
            else:                
                raise RuntimeError(f"No valid response to request with correlation ID {self._correlation_id}!")
    
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

            with self._lock:
                # register vehicle or reset all monitoring lists  
                if vehicle_ref not in self._vehicle_locks:
                    self._vehicle_locks[vehicle_ref] = False

                if vehicle_ref not in self._vehicle_queues:
                    self._vehicle_queues[vehicle_ref] = Queue()

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

            with self._lock:
                # reset all monitoring lists
                if vehicle_ref in self._vehicle_locks:
                    self._vehicle_locks[vehicle_ref] = False

                if vehicle_ref in self._vehicle_queues:
                    self._vehicle_queues[vehicle_ref] = Queue()

            self._publish(
                'pub_vehicle_inbox', 
                response.xml(),
                data_version=data_version,
                vehicle_id=vehicle_ref,
                correlation_id=correlation_id
            )

    def _handle_reponse(self, topic: str, payload: bytes) -> None:
        # lookup for correlation ID in the topic
        correlation_id: str = get_tls_value(topic, 'CorrelationId')

        # check whether correlation ID matches to the last request
        if correlation_id == self._correlation_id:

            # set result
            self._correlation_id = None
            self._correlation_result = payload

            # raise condition update
            with self._correlation_condition:
                self._correlation_condition.notify()
    
    def _handle_message(self, topic: str, payload: bytes) -> None:
        # handle message based on the topic
        msg: AbstractBasicStructure = Serializable.load(payload)

        # check if the message is subclass of AbstractDataPublicationStructure
        # other classes are not meant to be used in pub / sub pattern
        if not issubclass(msg.__class__, AbstractDataPublicationStructure):
            raise TypeError(f"{msg.__class__.__name__} is not subclass of AbstractDataPublicationStructure and not usable in Pub/Sub")
        
        # lookup for IDs which will be required for all handler results
        vehicle_ref: str = get_tls_value(topic, 'Vehicle')

        with self._lock:
            if vehicle_ref not in self._vehicle_locks or vehicle_ref not in self._vehicle_queues:
                logging.error(f"{self.instance_id}/{self.__class__.__name__}: Vehicle not registered in monitoring yet... Make sure the vehicle is technically logged on.")
                return

            if not self._vehicle_locks[vehicle_ref]:
                # mark vehicle as locked and put the action into the executor
                self._vehicle_locks[vehicle_ref] = True
                self._executor.submit(
                    self._handle_message_executor,
                    vehicle_ref,
                    topic,
                    msg
                )
            else:
                # the vehicle is currently processed by a thread
                # put the message into the queue
                # it will be executed once the current thread terminates
                logging.info(f"{self.instance_id}/{self.__class__.__name__}: Vehicle is blocked currently, enqueuing message ...")
                self._vehicle_queues[vehicle_ref].put((
                    vehicle_ref,
                    topic, 
                    msg
                ))

    def _handle_message_executor(self, vehicle_ref: str, topic: str, msg: AbstractBasicStructure) -> None:
        
        # run this in a separate try-catch clause
        # as the main thread does not see exceptions occured in ThreadPoolExecutor
        try:
            
            # handle incoming GnssPhysicalPositionData update
            if isinstance(msg, GnssPhysicalPositionDataStructure):
                handler: GnssPhysicalPositionHandler = GnssPhysicalPositionHandler(self._storage)
                handler.handle(topic, msg)

            # after handling release the current vehicle
            with self._lock:
                # check whether there're other messages in queue for this vehicle
                # if so, process them too; else remove the lock from the vehicle
                if not self._vehicle_queues[vehicle_ref].empty():
                    next_message: tuple = self._vehicle_queues[vehicle_ref].get()
                    self._executor.submit(
                        self._handle_message_executor,
                        *next_message
                    )
                else:
                    self._vehicle_locks[vehicle_ref] = False
        
        except Exception as ex:
            if is_debug():
                logging.exception(ex)
            else:
                logging.error(str(ex))

            # release vehicle lock in case of an exception
            # other messages may be processed correctly 
            with self._lock:
                self._vehicle_locks[vehicle_ref] = False

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