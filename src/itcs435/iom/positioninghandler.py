import logging

from typing import cast

from itcs435.common.mqtt import get_tls_value
from itcs435.vdv.vdv435 import AbstractBasicStructure
from itcs435.vdv.vdv435 import GnssPhysicalPositionDataStructure
from itcs435.iom.basehandler import AbstractHandler

class GnssPhysicalPositionHandler(AbstractHandler):

    def handle(self, topic: str, msg: AbstractBasicStructure) -> None:
        # Cast the message to the specific type if needed
        msg = cast(GnssPhysicalPositionDataStructure, msg)

        # process the physical position data
        vehicle_ref = get_tls_value(topic, 'Vehicle')
        logging.info(f"Processing GNSS physical position data for vehicle {vehicle_ref}")