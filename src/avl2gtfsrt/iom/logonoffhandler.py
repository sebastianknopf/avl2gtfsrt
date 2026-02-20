import logging

from typing import cast

from avl2gtfsrt.vdv.vdv435 import AbstractBasicStructure
from avl2gtfsrt.vdv.vdv435 import TechnicalVehicleLogOnRequestStructure, TechnicalVehicleLogOnResponseStructure
from avl2gtfsrt.vdv.vdv435 import TechnicalVehicleLogOnResponseDataStructure, TechnicalVehicleLogOnResponseErrorStructure
from avl2gtfsrt.vdv.vdv435 import TechnicalVehicleLogOffRequestStructure, TechnicalVehicleLogOffResponseStructure
from avl2gtfsrt.vdv.vdv435 import TechnicalVehicleLogOffResponseDataStructure, TechnicalVehicleLogOffResponseErrorStructure
from avl2gtfsrt.iom.basehandler import AbstractRequestResponseHandler
from avl2gtfsrt.model.types import Vehicle, VehicleActivity, VehicleCache, Trip
from avl2gtfsrt.objectstorage import ObjectStorage
from avl2gtfsrt.events.eventpublisher import EventPublisher
from avl2gtfsrt.events.eventmessage import EventMessage


class TechnicalVehicleLogOnHandler(AbstractRequestResponseHandler):
    def __init__(self, object_storage: ObjectStorage, event_stream: EventPublisher) -> None:
        super().__init__(object_storage)

        self._event_stream = event_stream
    
    def handle_request(self, msg: AbstractBasicStructure) -> AbstractBasicStructure:
        msg = cast(TechnicalVehicleLogOnRequestStructure, msg)
        
        vehicle_ref: str = msg.vehicle_ref.value

        vehicle: Vehicle = self._storage.get_vehicle(vehicle_ref)
        if vehicle is None:
            vehicle = Vehicle(vehicle_ref=vehicle_ref)

        if not vehicle.is_technically_logged_on:
            vehicle.is_technically_logged_on = True
            vehicle.is_differential_deleted = False
            vehicle.activity = VehicleActivity()
            vehicle.cache = VehicleCache()

            self._storage.update_vehicle(vehicle)
            self._event_stream.publish(EventMessage(EventMessage.TECHNICAL_VEHICLE_LOG_ON, vehicle_ref))

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
    def __init__(self, object_storage: ObjectStorage, event_stream: EventPublisher) -> None:
        super().__init__(object_storage)

        self._event_stream = event_stream
    
    def handle_request(self, msg: AbstractBasicStructure) -> AbstractBasicStructure:
        msg = cast(TechnicalVehicleLogOffRequestStructure, msg)
        
        vehicle_ref: str = msg.vehicle_ref.value

        vehicle: Vehicle = self._storage.get_vehicle(vehicle_ref)
        if vehicle.is_technically_logged_on:
            
            # mark a potential trip as deleted in order to delete existing trip updates 
            # if the vehicle was operationally logged on
            if vehicle.is_operationally_logged_on:
                current_trip_id: str = vehicle.activity.trip_descriptor.trip_id
                current_trip: Trip = self._storage.get_trip(current_trip_id)

                if current_trip is not None:
                    current_trip.is_differential_deleted = True
                    self._storage.update_trip(current_trip)
            
            vehicle.is_operationally_logged_on = False
            vehicle.is_technically_logged_on = False
            #vehicle.activity.trip_descriptor = None
            #vehicle.activity.trip_metrics = None
            # ^^^ leave trip_descriptor and trip_metrics for the option to send differential GTFS-RT updates
            # GtfsRealtimeExport runs a separate cleanup method for that
            vehicle.cache = None
            vehicle.is_differential_deleted = True

            self._storage.update_vehicle(vehicle)
            self._event_stream.publish(EventMessage(EventMessage.TECHNICAL_VEHICLE_LOG_OFF, vehicle_ref))

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