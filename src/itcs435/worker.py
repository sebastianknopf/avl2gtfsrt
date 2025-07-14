import logging
import os
import signal
import threading

from paho.mqtt import client as mqtt
from pymongo import MongoClient

from itcs435.iom import IoM
from itcs435.siri.publisher import Publisher

class IomWorker:

    def __init__(self) -> None:
        
        self._organisation_id: str = os.getenv('ITCS435_ORGANISATION_ID', 'TEST')
        self._itcs_id: str = os.getenv('ITCS435_ITCS_ID', '1')

        self._mqtt: mqtt.Client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5, client_id='itcs435-worker')
        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_message = self._on_message

        self._publisher = Publisher(
            os.getenv('ITCS435_PUBLISHER_PARTICIPANT_REF', 'PY_TEST_PUBLISHER'),
            os.getenv('ITCS435_PUBLISHER_PARTICIPANT_CONFIG_FILENAME', './config/participants.yaml'),
            datalog_directory=os.getenv('ITCS435_PUBLISHER_DATALOG_DIRECTORY', 'datalog')
        )
        
        self._mdb: MongoClient = None

        self._iom: IoM = IoM(
            organisation_id=self._organisation_id,
            itcs_id=self._itcs_id,
            mqtt_client=self._mqtt,
            mongo_client=self._mdb,
            siri_publisher=self._publisher
        )

        self._should_run = threading.Event()
        self._should_run.set()

    def _signal_handler(self, signum, frame):
        logging.info(f'Received signal {signum}')
        self._should_run.clear()

    def _on_connect(self, client, userdata, flags, rc, properties):
        if not rc.is_failure:
            for topic, qos in self._iom.get_subscribed_topics():
                logging.info(f"Subscribing to topic: {topic}")
                self._mqtt.subscribe(topic, qos=qos)

    def _on_message(self, client, userdata, message):
        self._iom.process(message.topic, message.payload)

    def _on_disconnect(self, client, userdata, flags, rc, properties):
        for topic, qos in self._iom.get_subscribed_topics():
            logging.info(f"Unsubscribing from topic: {topic}")
            self._mqtt.unsubscribe(topic)

    def run(self) -> None:
        # register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # connect to local MongoDB
        mongodb_username: str = os.getenv('ITCS435_MONGODB_USERNAME', '')
        mongodb_password: str = os.getenv('ITCS435_MONGODB_PASSWORD', '')

        logging.info("Connecting to MongoDB ...")
        self._mdb = MongoClient(f"mongodb://{mongodb_username}:{mongodb_password}@mongodb:27017")

        # set username and password if provided
        mqtt_username: str = os.getenv('ITCS435_WORKER_MQTT_USERNAME', None)
        mqtt_password: str = os.getenv('ITCS435_WORKER_MQTT_PASSWORD', None)
        if mqtt_username is not None and mqtt_password is not None:
            self._mqtt.username_pw_set(username=mqtt_username, password=mqtt_password)

        # connect to MQTT broker
        mqtt_host: str = os.getenv('ITCS435_WORKER_MQTT_HOST', 'test.mosquitto.org')
        mqtt_port: str = os.getenv('ITCS435_WORKER_MQTT_PORT', '1883')

        logging.info(f"Connecting to MQTT broker at {mqtt_host}:{mqtt_port}")
        self._mqtt.connect(mqtt_host, int(mqtt_port))
        self._mqtt.loop_start()

        # start publisher server
        logging.info("Starting SIRI publisher ...")
        self._publisher.start()

        try:
            # watch self._should_run for stopping gracefully
            while self._should_run.is_set():
                pass
        except Exception as ex:
            logging.error(f"Exception in worker: {ex}")
        finally:

            self._iom.terminate()

            logging.info("Shutting down MQTT connection...")
            self._mqtt.loop_stop()
            self._mqtt.disconnect()

            logging.info("Shutting down SIRI publisher ...")
            self._publisher.stop()

            logging.info("Closing MongoDB connection ...")
            self._mdb.close()