import time
import zmq

from avl2gtfsrt.events.eventstreambase import EventStreamBase


class EventPublisher(EventStreamBase):

    def __init__(self) -> None:
        super().__init__()

        self._zmq_socket: zmq.Socket = self._zmq.socket(zmq.PUB)
        self._zmq_socket.bind("tcp://*:5555")

    def _loop(self) -> None:
        while self._should_run.is_set():
            self._zmq_socket.send_string("heartbeat")
            time.sleep(1)
        
