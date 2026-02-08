import logging
import redis

from avl2gtfsrt.events.eventstreambase import EventStreamBase


class EventSubscriber(EventStreamBase):

    def __init__(self) -> None:
        super().__init__()

        self._redis_pubsub: redis.pubsub = self._redis.pubsub()
        self._redis_pubsub.subscribe("heartbeat")

    def _loop(self) -> None:
        for msg in self._redis_pubsub.listen():
             if not self._should_run.is_set():
                break

             if msg['type'] == 'message':
                 logging.info("Received Message: " + msg['data'].decode('utf-8'))

    def stop(self) -> None:
        self._redis_pubsub.close()

        super().stop()