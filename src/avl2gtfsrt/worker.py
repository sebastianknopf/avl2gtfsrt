import logging
import os
import signal
import threading
import time

from concurrent.futures import ThreadPoolExecutor

from avl2gtfsrt.iom.implementation import IoM
from avl2gtfsrt.objectstorage import ObjectStorage

class Worker:

    def __init__(self) -> None:
        # connect to local MongoDB
        mongodb_username: str = os.getenv('A2G_MONGODB_USERNAME', '')
        mongodb_password: str = os.getenv('A2G_MONGODB_PASSWORD', '')

        logging.info(f"{self.__class__.__name__}: Connecting to MongoDB ...")
        self._object_storage: ObjectStorage = ObjectStorage(mongodb_username, mongodb_password)

        # create thread pool for matching threads
        logging.info(f"{self.__class__.__name__}: Setting up ThreadPoolExecutor ...")
        self._executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=10)

        # create IoM instance
        organisation_id: str = os.getenv('A2G_ORGANISATION_ID', 'TEST')
        itcs_id: str = os.getenv('A2G_ITCS_ID', '1')

        self._iom: IoM = IoM(
            organisation_id=organisation_id,
            itcs_id=itcs_id,
            object_storage=self._object_storage,
            thread_executor=self._executor
        )

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

        logging.info(f"{self.__class__.__name__}: Worker startup complete.")

        try:
            # watch self._should_run for stopping gracefully
            while self._should_run.is_set():
                time.sleep(1)

        except Exception as ex:
            logging.error(f"{self.__class__.__name__}: Exception in worker: {ex}")
        finally:

            logging.info(f"{self.__class__.__name__}: Terminating IoM ...")
            self._iom.terminate()

            logging.info(f"{self.__class__.__name__}: Shutting down ThreadPoolExecutor ...")
            self._executor.shutdown(wait=True)

            logging.info(f"{self.__class__.__name__}: Closing MongoDB connection ...")
            self._object_storage.close()

            logging.info(f"{self.__class__.__name__}: Worker shutdown complete.")