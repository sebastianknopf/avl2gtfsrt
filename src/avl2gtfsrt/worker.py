import logging
import os
import signal
import threading
import time

from paho.mqtt import client as mqtt

from avl2gtfsrt.common.env import is_debug
from avl2gtfsrt.iom.processor import IomProcessor
from avl2gtfsrt.objectstorage import ObjectStorage

class AvlWorker:

    def __init__(self) -> None:
        
        self._organisation_id: str = os.getenv('A2G_ORGANISATION_ID', 'TEST')
        self._itcs_id: str = os.getenv('A2G_ITCS_ID', '1')

        self._mqtt: mqtt.Client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5, client_id='avl2gtfsrt-worker')
        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_message = self._on_message
        
        # connect to local MongoDB
        mongodb_username: str = os.getenv('A2G_MONGODB_USERNAME', '')
        mongodb_password: str = os.getenv('A2G_MONGODB_PASSWORD', '')

        logging.info(f"{self.__class__.__name__}: Connecting to MongoDB ...")
        self._object_storage: ObjectStorage = ObjectStorage(mongodb_username, mongodb_password)

        # create IoM instance
        self._iom: IomProcessor = IomProcessor(
            organisation_id=self._organisation_id,
            itcs_id=self._itcs_id,
            mqtt_client=self._mqtt,
            storage=self._object_storage
        )

        self._should_run = threading.Event()
        self._should_run.set()

    def _signal_handler(self, signum, frame):
        logging.info(f'{self.__class__.__name__}: Received signal {signum}')
        self._should_run.clear()

    def _on_connect(self, client, userdata, flags, rc, properties):
        if not rc.is_failure:
            for topic, qos in self._iom.get_subscribed_topics():
                logging.info(f"{self.__class__.__name__}: Subscribing to topic: {topic}")
                self._mqtt.subscribe(topic, qos=qos)

    def _on_message(self, client, userdata, message):
        try:
            self._iom.process(message.topic, message.payload)
        except Exception as ex:
            if is_debug():
                logging.exception(ex)
            else:
                logging.error(str(ex))

    def _on_disconnect(self, client, userdata, flags, rc, properties):
        for topic, qos in self._iom.get_subscribed_topics():
            logging.info(f"{self.__class__.__name__}: Unsubscribing from topic: {topic}")
            self._mqtt.unsubscribe(topic)

    def run(self) -> None:
        # register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # wait for 5s to startup network adapters in container
        #logging.info(f"{self.__class__.__name__}: Waiting for network adapters to start ...")
        #time.sleep(5)

        # set username and password if provided
        mqtt_username: str = os.getenv('A2G_WORKER_MQTT_USERNAME', None)
        mqtt_password: str = os.getenv('A2G_WORKER_MQTT_PASSWORD', None)
        if mqtt_username is not None and mqtt_password is not None:
            self._mqtt.username_pw_set(username=mqtt_username, password=mqtt_password)

        # connect to MQTT broker
        mqtt_host: str = os.getenv('A2G_WORKER_MQTT_HOST', 'test.mosquitto.org')
        mqtt_port: str = os.getenv('A2G_WORKER_MQTT_PORT', '1883')

        logging.info(f"{self.__class__.__name__}: Connecting to MQTT broker at {mqtt_host}:{mqtt_port}")
        self._mqtt.connect(mqtt_host, int(mqtt_port))
        self._mqtt.loop_start()

        logging.info(f"{self.__class__.__name__}: Worker startup complete.")

        try:
            # watch self._should_run for stopping gracefully
            while self._should_run.is_set():
                pass
        except Exception as ex:
            logging.error(f"{self.__class__.__name__}: Exception in worker: {ex}")
        finally:

            logging.info(f"{self.__class__.__name__}: Shutting down MQTT connection...")
            self._mqtt.loop_stop()
            self._mqtt.disconnect()

            logging.info(f"{self.__class__.__name__}: Closing MongoDB connection ...")
            self._object_storage.close()

            logging.info(f"{self.__class__.__name__}: Worker shutdown complete.")