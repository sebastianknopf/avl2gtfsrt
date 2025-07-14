from datetime import datetime, timezone

from itcs435.serialization import attributes, Serializable

@attributes(timestamp='Timestamp', version='@version')
class AbstractBasicStructure(Serializable):
    version: str
    timestamp: str

    def __init__(self, **arguments):
        super().__init__(**arguments)

        self.version = '1.0'
        self.timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

@attributes(message_id='MessageId')   
class AbstractMessageStructure(AbstractBasicStructure):
    message_id: str

    def __init__(self, **arguments):
        super().__init__(**arguments)

        self.message_id = None

"""@attributes(value='@value')
class TestSubClassStructure(AbstractBasicStructure):
    value: str

    def __init__(self, **arguments):
        super().__init__(**arguments)

        self.value = 'DefaultValue'

@attributes(sub='SubElement')
class TestParentClassStructure(AbstractBasicStructure):
    sub: TestSubClassStructure"""