from pydantic import Field

from itcs435.common.shared import isotimestamp, uid
from itcs435.serialization import Serializable


""" Basic Types """
class VehicleRef(Serializable):
    version: str = Field(alias='@version', default='any')
    value: str = Field(alias='#text')

""" Abstract Structures """
class AbstractBasicStructure(Serializable):
    version: str = Field(alias='@version', default='1.0')
    timestamp: str = Field(alias='Timestamp', default_factory=isotimestamp)

class AbstractMessageStructure(AbstractBasicStructure):
    message_id: str = Field(alias='MessageId', default_factory=uid)

class AbstractRequestStructure(AbstractMessageStructure):
    pass

class AbstractRequestWithReferenceStructure(AbstractMessageStructure):
    message_id_ref: str = Field(alias='MessageIdRef')

class AbstractResponseStructure(AbstractMessageStructure):
    common_reponse_code: str = Field(alias='CommonResponseCode', default='ok')

class InvalidMessageResponseStructure(AbstractResponseStructure):
    pass

class AbstractDataPublicationStructure(AbstractBasicStructure):
    timestamp_of_measurement: str = Field(alias='TimestampOfMeasurement', default=isotimestamp)
    publisher_id: str = Field('PublisherId')

""" Technical LogOn / LogOff Structures """
class AbstractTechnicalLogOnOffRequestStructure(AbstractMessageStructure):
    pass

class AbstractTechnicalVehicleLogOnOffRequestStructure(AbstractTechnicalLogOnOffRequestStructure):
    xmlns_netex: str = Field(alias='@xmlns:netex', default='http://www.netex.org.uk/netex')

    vehicle_ref: VehicleRef = Field(alias='netex:VehicleRef')
    onboard_unit_id: str|None = Field(alias='OnBoardUnitId', default=None)

class TechnicalVehicleLogOnResponseDataStructure(Serializable):
    pass

class TechnicalVehicleLogOnResponseErrorStructure(Serializable):
    technical_vehicle_log_on_response_code: str = Field(alias='TechnicalVehicleLogOnResponseCode')

class TechnicalVehicleLogOnRequestStructure(AbstractTechnicalVehicleLogOnOffRequestStructure):
    base_version: str|None = Field(alias='BaseVersion', default=None)

class TechnicalVehicleLogOnResponseStructure(AbstractResponseStructure):
    technical_vehicle_log_on_response_data: TechnicalVehicleLogOnResponseDataStructure|None = Field(alias='TechnicalVehicleLogOnResponseData', default=None)
    technical_vehicle_log_on_response_error: TechnicalVehicleLogOnResponseErrorStructure|None = Field(alias='TechnicalVehicleLogOnResponseError', default=None)

class TechnicalVehicleLogOffRequestStructure(AbstractTechnicalVehicleLogOnOffRequestStructure):
    pass

class TechnicalVehicleLogOffResponseDataStructure(Serializable):
    pass

class TechnicalVehicleLogOffResponseErrorStructure(Serializable):
    technical_vehicle_log_off_response_code: str = Field(alias='TechnicalVehicleLogOffResponseCode')

class TechnicalVehicleLogOffResponseStructure(AbstractResponseStructure):
    technical_vehicle_log_off_response_data: TechnicalVehicleLogOffResponseDataStructure|None = Field(alias='TechnicalVehicleLogOffResponseData', default=None)
    technical_vehicle_log_off_response_error: TechnicalVehicleLogOffResponseErrorStructure|None = Field(alias='TechnicalVehicleLogOffResponseError', default=None)

