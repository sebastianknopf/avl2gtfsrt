import logging
import time
import os

from avl2gtfsrt.objectstorage import ObjectStorage
from avl2gtfsrt.events.eventsubscriber import EventSubscriber
from avl2gtfsrt.events.eventmessage import EventMessage
from avl2gtfsrt.gtfsrt.export import GtfsRealtimeExport

class GtfsRealtimePublisher:
    
    def __init__(self):
        # connect to local MongoDB
        mongodb_username: str = os.getenv('A2G_MONGODB_USERNAME', '')
        mongodb_password: str = os.getenv('A2G_MONGODB_PASSWORD', '')

        logging.info(f"{self.__class__.__name__}: Connecting to MongoDB ...")
        self._object_storage: ObjectStorage = ObjectStorage(
            mongodb_username, 
            mongodb_password,
            int(os.getenv('A2G_MATCHING_DATA_REVIEW_SECONDS', '120')),
            int(os.getenv('A2G_MATCHING_MAX_DATA_POINTS', '60'))
        )

    def _on_event_message(self, message: EventMessage):
        logging.info(f"{self.__class__.__name__}: Received message {message}")

        gtfsrt_export: GtfsRealtimeExport = GtfsRealtimeExport(self._object_storage)

        if message.event_type == EventMessage.TECHNICAL_VEHICLE_LOG_ON:
            pass
        elif message.event_type == EventMessage.TECHNICAL_VEHICLE_LOG_OFF:
            pass
        elif message.event_type == EventMessage.OPERATIONAL_VEHICLE_LOG_ON:
            pass
        elif message.event_type == EventMessage.OPERATIONAL_VEHICLE_LOG_OFF:
            pass
        elif message.event_type == EventMessage.GNSS_PHYSICAL_POSITION_UPDATE:
            pass
    
        print(gtfsrt_export.export_differential_vehicle_positions(message.vehicle_id, debug=True))
        print(gtfsrt_export.export_differential_trip_updates(vehicle_id=message.vehicle_id, debug=True))
    
    def run(self):

        self._event_stream: EventSubscriber = EventSubscriber()
        self._event_stream.on_event_message = self._on_event_message
        
        self._event_stream.start()

        while True:
            time.sleep(5)