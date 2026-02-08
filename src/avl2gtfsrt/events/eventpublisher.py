from avl2gtfsrt.events.eventstreambase import EventStreamBase
from avl2gtfsrt.events.eventmessage import EventMessage


class EventPublisher(EventStreamBase):

    def __init__(self) -> None:
        super().__init__()

    def publish(self, message: EventMessage) -> None:
        self._redis.publish('avl2gtfsrt', str(message))
        
