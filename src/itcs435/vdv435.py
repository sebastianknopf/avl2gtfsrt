import json

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
        
        json: str = self.json()
        data: dict = json.loads(json)

        xml: str = unparse({data}, pretty=True)
        return xml
    
    def json(self):
        attributes: dict = getattr(self.__class__, "_attributes", {})
        
        data:dict = {}
        for attr, alias_name in attributes.items():
            data[alias_name] = getattr(self, attr)

        class_name: str = self.__class__.__name__
        class_name = class_name.replace('Structure', '')

        json: str = json.dumps({class_name: data}, indent=4, ensure_ascii=False)

        return json

    @classmethod
    def load(cls, raw: str):
        try:
            data: dict = json.loads(raw)
        except json.JSONDecodeError:
            data: dict = parse(raw)
        
        class_name: str = next(iter(data))
        if not class_name.endswith('Structure'):
            class_name = f"{class_name}Structure"
        
        cls = globals()[class_name]

        data = data[class_name]
        
        attributes:dict = getattr(cls, "_attributes", {})
        arguments:dict = {attr: data[alias] for attr, alias in attributes.items() if alias in data}

        return cls(**arguments)

@attributes(message_id='MessageId')   
class AbstractMessageStructure(AbstractBasicStructure):
    message_id: str