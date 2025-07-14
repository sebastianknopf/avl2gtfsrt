import uuid

from datetime import datetime, timezone
from pydantic import Field

from itcs435.serialization import Serializable

""" Basic Types """
class VehicleRef(Serializable):
    version: str = Field(alias='@version', default='any')
    value: str = Field(alias='#text')

""" Abstract Structures """
class AbstractBasicStructure(Serializable):
    version: str = Field(alias='@version', default='1.0')
    timestamp: str = Field(alias='Timestamp', default=str(datetime.now(timezone.utc).replace(microsecond=0).isoformat()))

class AbstractMessageStructure(AbstractBasicStructure):
    message_id: str = Field(alias='MessageId', default=str(uuid.uuid4()))

class AbstractRequestStructure(AbstractMessageStructure):
    pass

class AbstractRequestWithReferenceStructure(AbstractMessageStructure):
    message_id_ref: str = Field(alias='MessageIdRef')

class AbstractResponseStructure(AbstractMessageStructure):
    common_reponse_code: str = Field(alias='CommonResponseCode', default='ok')

class InvalidMessageResponseStructure(AbstractResponseStructure):
    pass

class AbstractDataPublicationStructure(AbstractBasicStructure):
    timestamp_of_measurement: str = Field(alias='TimestampOfMeasurement', default=str(datetime.now(timezone.utc).replace(microsecond=0).isoformat()))
    publisher_id: str = Field('PublisherId')

""" LogOn / LogOff Structures """
class AbstractTechnicalLogOnOffRequestStructure(AbstractMessageStructure):
    pass

class AbstractTechnicalVehicleLogOnOffRequestStructure(AbstractTechnicalLogOnOffRequestStructure):
    xmlns_netex: str = Field(alias='@xmlns:netex', default='http://www.netex.org.uk/netex')

    vehicle_ref: VehicleRef = Field(alias='netex:VehicleRef')
    onboard_unit_id: str|None = Field(alias='OnBoardUnitId', default=None)

class TechnicalVehicleLogOnRequestStructure(AbstractTechnicalVehicleLogOnOffRequestStructure):
    base_version: str|None = Field(alias='BaseVersion', default=None)

class TechnicalVehicleLogOnResponseStructure(AbstractResponseStructure):
    technical_vehicle_log_on_response_data: str = Field(alias='TechnicalVehicleLogOnResponseData', default='')
