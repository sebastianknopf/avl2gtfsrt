import logging
import time


class GtfsRealtimePublisher:
    def __init__(self):
        pass

    def run(self):
        while True:
            logging.info("Publishing GTFS Realtime data...")
            time.sleep(5)