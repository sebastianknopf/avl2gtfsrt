import logging

from paho.mqtt import client as mqtt

class IomWorker:

    def __init__(self, mqtt_host, mqtt_port, mqtt_username, mqtt_password) -> None:
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._mqtt_username = mqtt_username
        self._mqtt_password = mqtt_password

        self._mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5, client_id='itcs435-worker')

    def run(self) -> None:
        
        if self._mqtt_username is not None and self._mqtt_password is not None:
            self._mqtt.username_pw_set(username=self._mqtt_username, password=self._mqtt_password)

        self._mqtt.connect(self._mqtt_host, int(self._mqtt_port))
        self._mqtt.loop_start()

        try:
            while True:
                pass
        except InterruptedError:
            pass

        self._mqtt.loop_stop()
        self._mqtt.disconnect()