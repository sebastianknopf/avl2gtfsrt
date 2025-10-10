import logging

from typing import cast

from avl2gtfsrt.vdv.vdv435 import AbstractBasicStructure
from avl2gtfsrt.vdv.vdv435 import TechnicalVehicleLogOnRequestStructure, TechnicalVehicleLogOnResponseStructure
from avl2gtfsrt.vdv.vdv435 import TechnicalVehicleLogOnResponseDataStructure, TechnicalVehicleLogOnResponseErrorStructure
from avl2gtfsrt.vdv.vdv435 import TechnicalVehicleLogOffRequestStructure, TechnicalVehicleLogOffResponseStructure
from avl2gtfsrt.vdv.vdv435 import TechnicalVehicleLogOffResponseDataStructure, TechnicalVehicleLogOffResponseErrorStructure
from avl2gtfsrt.iom.basehandler import AbstractRequestResponseHandler

class TechnicalVehicleLogOnHandler(AbstractRequestResponseHandler):
    def handle_request(self, msg: AbstractBasicStructure) -> AbstractBasicStructure:
        msg = cast(TechnicalVehicleLogOnRequestStructure, msg)
        
        vehicle_ref: str = msg.vehicle_ref.value

        vehicle = self._object_storage.get_vehicle(vehicle_ref)
        if vehicle is None or vehicle is not None and not vehicle.get('is_technically_logged_on', False):
            self._object_storage.update_vehicle(vehicle_ref, {
                'is_technically_logged_on': True
            })

            self._object_storage.delete_vehicle_activity(vehicle_ref)

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

        vehicle = self._object_storage.get_vehicle(vehicle_ref)
        if vehicle is not None and vehicle.get('is_technically_logged_on', False):
            self._object_storage.update_vehicle(
                vehicle_ref,
                {
                    'is_technically_logged_on': False,
                    'is_operationally_logged_on': False
                }
            )

            self._object_storage.delete_vehicle_activity(vehicle_ref)

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