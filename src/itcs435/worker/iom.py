import logging
import signal
import threading

from paho.mqtt import client as mqtt

class IomWorker:

    def __init__(self, mqtt_host, mqtt_port, mqtt_username, mqtt_password) -> None:
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._mqtt_username = mqtt_username
        self._mqtt_password = mqtt_password

        self._mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5, client_id='itcs435-worker')
        self._mqtt.on_message = self._on_message
        
        self._should_run = threading.Event()
        self._should_run.set()

    def _signal_handler(self, signum, frame):
        logging.info(f'Received signal {signum}')
        self._should_run.clear()

    def _on_message(self, client, userdata, message):
        logging.info(f"Received message on topic {message.topic}: {message.payload.decode()}")
        # Process the message as needed

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

        self._mqtt.subscribe("#", qos=1)

        self._mqtt.loop_start()

        try:
            # watch self._should_run for stopping gracefully
            while self._should_run.is_set():
                pass
        except Exception as ex:
            logging.error(f"Exception in worker: {ex}")
        finally:
            logging.info("Shutting down MQTT connection...")
            self._mqtt.loop_stop()

            self._mqtt.unsubscribe("#")

            self._mqtt.disconnect()