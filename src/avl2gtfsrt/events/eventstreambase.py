import zmq

from abc import ABC, abstractmethod
from threading import Thread, Event


class EventStreamBase(ABC):

    def __init__(self) -> None:
        self._zmq: zmq.Context = zmq.Context()

        self._zmq_thread: Thread = Thread(target=self._loop, daemon=True)
        
        self._should_run: Event = Event()
        self._should_run.set()

    @abstractmethod
    def _loop(self) -> None:
        pass

    def start(self) -> None:
        self._zmq_thread.start()
    
    def stop(self) -> None:
        self._should_run.clear()

        self._zmq_socket.close()
        self._zmq.term()