from xmltodict import parse, unparse

def attributes(**attributes):
    def decorator(cls):
        base_attributes:dict = {}
        for base in cls.__bases__:
            base_attributes.update(getattr(base, "_attributes", {}))

        cls._attributes = {**base_attributes, **attributes}
        return cls
    
    return decorator

@attributes(timestamp='Timestamp', version='@version')
class AbstractBasicStructure():
    version: str
    timestamp: str

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def xml(self):
        attributes: dict = getattr(self.__class__, "_attributes", {})
        
        data:dict = {}
        for attr, alias_name in attributes.items():
            data[alias_name] = getattr(self, attr)

        class_name: str = self.__class__.__name__
        class_name = class_name.replace('Structure', '')

        xml: str = unparse({class_name: data}, pretty=True)

        return xml
    
    @classmethod
    def load(cls, xml: str):
        data: dict = parse(xml)
        
        class_name: str = next(iter(data))
        if not class_name.endswith('Structure'):
            class_name = f"{class_name}Structure"
        
        cls = globals()[class_name]

        data = data[class_name.replace('Structure', '')]

        attributes:dict = getattr(cls, "_attributes", {})
        arguments:dict = {attr: data[alias] for attr, alias in attributes.items() if alias in data}

        return cls(**arguments)

@attributes(message_id='MessageId')   
class AbstractMessageStructure(AbstractBasicStructure):
    message_id: str