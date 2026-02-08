import redis

from abc import ABC, abstractmethod
from threading import Thread, Event


class EventStreamBase(ABC):

    def __init__(self) -> None:
        self._redis: redis.Redis = redis.Redis(
            host='avl2gtfsrt-redis',
            port=6379,
            db=0
        )

        self._redis_thread: Thread = Thread(target=self._loop, daemon=True, name='eventstreambase-redis-thread')
        
        self._should_run: Event = Event()
        self._should_run.set()

    def _loop(self) -> None:
        pass

    def start(self) -> None:
        self._redis_thread.start()
    
    def stop(self) -> None:
        self._should_run.clear()

        self._redis.close()