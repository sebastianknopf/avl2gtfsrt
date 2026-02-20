import logging
import os
import signal
import threading
import time

from concurrent.futures import ThreadPoolExecutor

from avl2gtfsrt.events.eventpublisher import EventPublisher
from avl2gtfsrt.iom.client import IomClient, IomRole
from avl2gtfsrt.vdv.vdv435 import *
from avl2gtfsrt.iom.logonoffhandler import TechnicalVehicleLogOnHandler
from avl2gtfsrt.iom.logonoffhandler import TechnicalVehicleLogOffHandler
from avl2gtfsrt.iom.positioninghandler import GnssPhysicalPositionHandler
from avl2gtfsrt.objectstorage import ObjectStorage

class Worker:

    def __init__(self) -> None:
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

        # create thread pool for matching threads
        logging.info(f"{self.__class__.__name__}: Setting up ThreadPoolExecutor ...")
        self._executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=10)

        # create IoM instance
        instance_id: str = os.getenv('A2G_INSTANCE_ID', 'default')
        organisation_id: str = os.getenv('A2G_ORGANISATION_ID', 'TEST')
        itcs_id: str = os.getenv('A2G_ITCS_ID', '1')

        self._iom: IomClient = IomClient(
            config={
                'instance_id': instance_id,
                'organisation_id': organisation_id,
                'itcs_id': itcs_id,
                'host': os.getenv('A2G_WORKER_MQTT_HOST', 'localhost'),
                'port': int(os.getenv('A2G_WORKER_MQTT_PORT', '1883')),
                'username': os.getenv('A2G_WORKER_MQTT_USERNAME', ''),
                'password': os.getenv('A2G_WORKER_MQTT_PASSWORD', '')
            },
            iom_role=IomRole.ITCS,
            thread_executor=self._executor
        )

        self._iom.on_technical_vehicle_log_on = self._iom_technical_vehicle_log_on
        self._iom.on_technical_vehicle_log_off = self._iom_technical_vehicle_log_off
        self._iom.on_gnss_position_update = self._iom_gnss_position_update

        # create event stream for communication with the publisher
        self._event_stream: EventPublisher = EventPublisher()

        self._should_run = threading.Event()
        self._should_run.set()

    def _signal_handler(self, signum, frame):
        logging.info(f'{self.__class__.__name__}: Received signal {signum}')
        self._should_run.clear()

    def run(self) -> None:
        # register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # startup the IoM
        logging.info(f"{self.__class__.__name__}: Initializing IoM ...")
        self._iom.start()

        # startup the event stream
        logging.info(f"{self.__class__.__name__}: Initializing internal event stream ...")
        self._event_stream.start()

        logging.info(f"{self.__class__.__name__}: Worker startup complete.")

        try:
            # watch self._should_run for stopping gracefully
            while self._should_run.is_set():
                time.sleep(1)

        except Exception as ex:
            logging.error(f"{self.__class__.__name__}: Exception in worker: {ex}")
        finally:

            logging.info(f"{self.__class__.__name__}: Stopping internal event stream ...")
            self._event_stream.stop()

            logging.info(f"{self.__class__.__name__}: Terminating IoM ...")
            self._iom.terminate()

            logging.info(f"{self.__class__.__name__}: Shutting down ThreadPoolExecutor ...")
            self._executor.shutdown(wait=True)

            logging.info(f"{self.__class__.__name__}: Closing MongoDB connection ...")
            self._object_storage.close()

            logging.info(f"{self.__class__.__name__}: Worker shutdown complete.")

    def _iom_technical_vehicle_log_on(self, msg: AbstractBasicStructure) -> AbstractBasicStructure:
        handler: TechnicalVehicleLogOnHandler = TechnicalVehicleLogOnHandler(self._object_storage, self._event_stream)
        return handler.handle_request(msg)
    
    def _iom_technical_vehicle_log_off(self, msg: AbstractBasicStructure) -> AbstractBasicStructure:
        handler: TechnicalVehicleLogOffHandler = TechnicalVehicleLogOffHandler(self._object_storage, self._event_stream)
        return handler.handle_request(msg)
    
    def _iom_gnss_position_update(self, topic: str, msg: AbstractBasicStructure) -> None:
        handler: GnssPhysicalPositionHandler = GnssPhysicalPositionHandler(self._object_storage, self._event_stream)
        handler.handle(topic, msg)