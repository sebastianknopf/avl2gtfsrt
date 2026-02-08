import logging
import zmq

from avl2gtfsrt.events.eventstreambase import EventStreamBase


class EventSubscriber(EventStreamBase):

    def __init__(self, host: str) -> None:
        super().__init__()

        self._zmq_socket: zmq.Socket = self._zmq.socket(zmq.SUB)
        self._zmq_socket.connect(f"tcp://{host}:5555")
        self._zmq_socket.setsockopt_string(zmq.SUBSCRIBE, "heartbeat")

    def _loop(self) -> None:
        while self._should_run.is_set():
            logging.info("Received Message: " + self._zmq_socket.recv_string())