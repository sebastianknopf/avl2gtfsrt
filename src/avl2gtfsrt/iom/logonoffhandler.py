import logging

from typing import cast

from avl2gtfsrt.vdv.vdv435 import AbstractBasicStructure
from avl2gtfsrt.vdv.vdv435 import TechnicalVehicleLogOnRequestStructure, TechnicalVehicleLogOnResponseStructure
from avl2gtfsrt.vdv.vdv435 import TechnicalVehicleLogOnResponseDataStructure, TechnicalVehicleLogOnResponseErrorStructure
from avl2gtfsrt.vdv.vdv435 import TechnicalVehicleLogOffRequestStructure, TechnicalVehicleLogOffResponseStructure
from avl2gtfsrt.vdv.vdv435 import TechnicalVehicleLogOffResponseDataStructure, TechnicalVehicleLogOffResponseErrorStructure
from avl2gtfsrt.iom.basehandler import AbstractRequestResponseHandler
from avl2gtfsrt.model.types import Vehicle, VehicleActivity


class TechnicalVehicleLogOnHandler(AbstractRequestResponseHandler):
    def handle_request(self, msg: AbstractBasicStructure) -> AbstractBasicStructure:
        msg = cast(TechnicalVehicleLogOnRequestStructure, msg)
        
        vehicle_ref: str = msg.vehicle_ref.value

        vehicle: Vehicle = self._storage.get_vehicle(vehicle_ref)
        if vehicle is None:
            vehicle = Vehicle(vehicle_ref=vehicle_ref)

        if not vehicle.is_technically_logged_on:
            vehicle.is_technically_logged_on = True
            vehicle.activity = VehicleActivity()

            self._storage.update_vehicle(vehicle)

            response: TechnicalVehicleLogOnResponseStructure = TechnicalVehicleLogOnResponseStructure()
            response.technical_vehicle_log_on_response_data = TechnicalVehicleLogOnResponseDataStructure()

            logging.info(f"{self.__class__.__name__}: Vehicle {vehicle_ref} logged on successfully.")

            return response
        else:
            response: TechnicalVehicleLogOnResponseStructure = TechnicalVehicleLogOnResponseStructure()
            response.common_reponse_code = 'messageUnderstood'
            response.technical_vehicle_log_on_response_error = TechnicalVehicleLogOnResponseErrorStructure(
                TechnicalVehicleLogOnResponseCode='doubleLogOn'
            )

            logging.error(f"{self.__class__.__name__}: Vehicle {vehicle_ref} tried to log on but is already logged on.")

            return response
        
class TechnicalVehicleLogOffHandler(AbstractRequestResponseHandler):
    def handle_request(self, msg: AbstractBasicStructure) -> AbstractBasicStructure:
        msg = cast(TechnicalVehicleLogOffRequestStructure, msg)
        
        vehicle_ref: str = msg.vehicle_ref.value

        vehicle: Vehicle = self._storage.get_vehicle(vehicle_ref)
        if vehicle.is_technically_logged_on:
            vehicle.is_operationally_logged_on = False
            vehicle.is_technically_logged_on = False
            vehicle.activity = None

            self._storage.update_vehicle(vehicle)

            response: TechnicalVehicleLogOffResponseStructure = TechnicalVehicleLogOffResponseStructure()
            response.technical_vehicle_log_off_response_data = TechnicalVehicleLogOffResponseDataStructure()

            logging.info(f"{self.__class__.__name__}: Vehicle {vehicle_ref} logged off successfully.")

            return response
        else:
            response: TechnicalVehicleLogOffResponseStructure = TechnicalVehicleLogOffResponseStructure()
            response.common_reponse_code = 'messageUnderstood'
            response.technical_vehicle_log_off_response_error = TechnicalVehicleLogOffResponseErrorStructure(
                TechnicalVehicleLogOffResponseCode='vehicleNotLoggedOn'
            )

            logging.error(f"{self.__class__.__name__}: Vehicle {vehicle_ref} tried to log off but is not logged on.")

            return response