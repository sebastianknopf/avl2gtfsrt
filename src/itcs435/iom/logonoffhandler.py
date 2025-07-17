from typing import cast

from itcs435.vdv.vdv435 import AbstractBasicStructure
from itcs435.vdv.vdv435 import TechnicalVehicleLogOnRequestStructure, TechnicalVehicleLogOnResponseStructure
from itcs435.vdv.vdv435 import TechnicalVehicleLogOnResponseDataStructure, TechnicalVehicleLogOnResponseErrorStructure
from itcs435.vdv.vdv435 import TechnicalVehicleLogOffRequestStructure, TechnicalVehicleLogOffResponseStructure
from itcs435.vdv.vdv435 import TechnicalVehicleLogOffResponseDataStructure, TechnicalVehicleLogOffResponseErrorStructure
from itcs435.iom.basehandler import AbstractRequestResponseHandler

class TechnicalVehicleLogOnHandler(AbstractRequestResponseHandler):
    def handle_request(self, msg: AbstractBasicStructure) -> AbstractBasicStructure:
        msg = cast(TechnicalVehicleLogOnRequestStructure, msg)
        
        vehicle_ref: str = msg.vehicle_ref.value

        vehicle = self._storage.get_vehicle(vehicle_ref)
        if vehicle is None or vehicle is not None and not vehicle.get('is_technically_logged_on', False):
            self._storage.update_vehicle(vehicle_ref, {
                'is_technically_logged_on': True
            })

            response: TechnicalVehicleLogOnResponseStructure = TechnicalVehicleLogOnResponseStructure()
            response.technical_vehicle_log_on_response_data = TechnicalVehicleLogOnResponseDataStructure()

            return response
        else:
            response: TechnicalVehicleLogOnResponseStructure = TechnicalVehicleLogOnResponseStructure()
            response.common_reponse_code = 'messageUnderstood'
            response.technical_vehicle_log_on_response_error = TechnicalVehicleLogOnResponseErrorStructure(
                TechnicalVehicleLogOnResponseCode='doubleLogOn'
            )

            return response
        
class TechnicalVehicleLogOffHandler(AbstractRequestResponseHandler):
    def handle_request(self, msg: AbstractBasicStructure) -> AbstractBasicStructure:
        msg = cast(TechnicalVehicleLogOffRequestStructure, msg)
        
        vehicle_ref: str = msg.vehicle_ref.value

        vehicle = self._storage.get_vehicle(vehicle_ref)
        if vehicle is not None and vehicle.get('is_technically_logged_on', False):
            self._storage.update_vehicle(
                vehicle_ref,
                {'is_technically_logged_on': False}
            )

            response: TechnicalVehicleLogOffResponseStructure = TechnicalVehicleLogOffResponseStructure()
            response.technical_vehicle_log_off_response_data = TechnicalVehicleLogOffResponseDataStructure()

            return response
        else:
            response: TechnicalVehicleLogOffResponseStructure = TechnicalVehicleLogOffResponseStructure()
            response.common_reponse_code = 'messageUnderstood'
            response.technical_vehicle_log_off_response_error = TechnicalVehicleLogOffResponseErrorStructure(
                TechnicalVehicleLogOffResponseCode='vehicleNotLoggedOn'
            )

            return response