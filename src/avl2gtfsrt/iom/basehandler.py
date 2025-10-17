from abc import ABC

from avl2gtfsrt.objectstorage import ObjectStorage
from avl2gtfsrt.vdv.vdv435 import AbstractBasicStructure


class AbstractHandler(ABC):

    def __init__(self, storage: ObjectStorage) -> None:
        self._storage = storage

    def handle(self, topic: str, msg: AbstractBasicStructure) -> None:
        raise NotImplementedError("Subclasses must implement this method")
    

class AbstractRequestResponseHandler(AbstractHandler):

    def handle_request(self, msg: AbstractBasicStructure) -> AbstractBasicStructure:
        raise NotImplementedError("Subclasses must implement this method")