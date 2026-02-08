import logging
import time

from avl2gtfsrt.events.eventsubscriber import EventSubscriber

class GtfsRealtimePublisher:
    def __init__(self):
        pass

    def run(self):

        self._event_stream: EventSubscriber = EventSubscriber()
        self._event_stream.start()

        while True:
            logging.info("Publishing GTFS Realtime data...")
            time.sleep(5)