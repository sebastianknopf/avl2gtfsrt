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

class Serializable:

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _create_dict(self):
        attributes: dict = getattr(self.__class__, "_attributes", {})
        data: dict = {}
        for attr, alias_name in attributes.items():
            value = getattr(self, attr)
            # Serialisiere weiter, wenn value Instanz von object ist (und nicht None)
            if isinstance(value, Serializable) and value is not None:
                # Versuche rekursive Serialisierung, falls möglich
                if hasattr(value, '_create_dict') and callable(value._create_dict):
                    data[alias_name] = value._create_dict()
                else:
                    # Fallback: __dict__ verwenden
                    data[alias_name] = value.__dict__
            else:
                data[alias_name] = value

        return data
    
    def json(self):
        class_name: str = self.__class__.__name__.replace('Structure', '')
        json_str: str = json.dumps({class_name: self._create_dict()}, indent=4, ensure_ascii=False)
        return json_str

    def xml(self):
        data: dict = json.loads(self.json())
        xml: str = unparse(data, pretty=True)
        return xml
    
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
        data = next(iter(data.values()))
        
        attributes:dict = getattr(cls, "_attributes", {})
        arguments:dict = {attr: data[alias] for attr, alias in attributes.items() if alias in data}

        return cls(**arguments)

@attributes(timestamp='Timestamp', version='@version')
class AbstractBasicStructure(Serializable):
    version: str
    timestamp: str    

@attributes(message_id='MessageId')   
class AbstractMessageStructure(AbstractBasicStructure):
    message_id: str

@attributes(value='@value')
class TestSubClass(AbstractBasicStructure):
    value: str

@attributes(sub='SubElement')
class TestParentClass(AbstractBasicStructure):
    sub: TestSubClass