import time
import redis

from avl2gtfsrt.events.eventstreambase import EventStreamBase


class EventPublisher(EventStreamBase):

    def __init__(self) -> None:
        super().__init__()

    def publish_message(self, message: str) -> None:
        self._redis.publish("heartbeat", message)
        
