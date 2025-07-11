import logging
import os
import signal
import threading

from paho.mqtt import client as mqtt

from itcs435.siri.publisher import Publisher

class IomWorker:

    def __init__(self, mqtt_host, mqtt_port, mqtt_username, mqtt_password) -> None:
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._mqtt_username = mqtt_username
        self._mqtt_password = mqtt_password

        self._mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5, client_id='itcs435-worker')
        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_message = self._on_message

        self._publisher = Publisher(
            os.getenv('ITCS435_PUBLISHER_PARTICIPANT_REF', 'PY_TEST_PUBLISHER'),
            os.getenv('ITCS435_PUBLISHER_PARTICIPANT_CONFIG_FILENAME', './config/participants.yaml'),
            datalog_directory=os.getenv('ITCS435_PUBLISHER_DATALOG_DIRECTORY', 'datalog')
        )
        
        self._should_run = threading.Event()
        self._should_run.set()

    def _signal_handler(self, signum, frame):
        logging.info(f'Received signal {signum}')
        self._should_run.clear()

    def _on_connect(self, client, userdata, flags, rc, properties):
        if not rc.is_failure:
            self._mqtt.subscribe("#", qos=1)

    def _on_message(self, client, userdata, message):
        logging.info(f"Received message on topic {message.topic}")
        # Process the message as needed

    def _on_disconnect(self, client, userdata, flags, rc, properties):
        self._mqtt.unsubscribe("#")

    def run(self) -> None:
        # register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # set username and password if provided
        if self._mqtt_username is not None and self._mqtt_password is not None:
            self._mqtt.username_pw_set(username=self._mqtt_username, password=self._mqtt_password)

        # connect to MQTT broker
        logging.info(f"Connecting to MQTT broker at {self._mqtt_host}:{self._mqtt_port}")
        self._mqtt.connect(self._mqtt_host, int(self._mqtt_port))
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

            logging.info("Shutting down MQTT connection...")
            self._mqtt.loop_stop()
            self._mqtt.disconnect()

            logging.info("Shutting down SIRI publisher ...")
            self._publisher.stop()