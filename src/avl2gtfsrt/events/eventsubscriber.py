import json
import logging
from avl2gtfsrt.events.eventmessage import EventMessage
import redis

from avl2gtfsrt.events.eventstreambase import EventStreamBase
from avl2gtfsrt.events.eventmessage import EventMessage


class EventSubscriber(EventStreamBase):

    def __init__(self) -> None:
        super().__init__()

        self._redis_pubsub: redis.pubsub = self._redis.pubsub()
        self._redis_pubsub.subscribe('avl2gtfsrt')

        self.on_event_message: callable|None = None

    def _loop(self) -> None:
        for msg in self._redis_pubsub.listen():
             if not self._should_run.is_set():
                break

             if msg['type'] == 'message':
                try:
                    message: EventMessage = EventMessage.create(msg['data'].decode('utf-8'))
                    
                    if self.on_event_message is not None:
                        self.on_event_message(message)

                except Exception as e:
                    logging.error(f"{self.__class__.__name__}: Failed to parse message: {e}")
    
    def stop(self) -> None:
        self._redis_pubsub.close()

        super().stop()