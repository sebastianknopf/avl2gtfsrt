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

    def __init__(self, **arguments):
        for key, value in arguments.items():
            setattr(self, key, value)

    def _create_dict(self) -> dict:
        attributes: dict = getattr(self.__class__, "_attributes", {})
        data: dict = {}
        for attr, alias_name in attributes.items():
            value = getattr(self, attr)
            if isinstance(value, Serializable) and value is not None:
                if hasattr(value, '_create_dict') and callable(value._create_dict):
                    data[alias_name] = value._create_dict()
            else:
                data[alias_name] = value

        return data
    
    def json(self):
        class_name: str = self.__class__.__name__
        json_str: str = json.dumps({class_name: self._create_dict()}, indent=4, ensure_ascii=False)
        return json_str

    def xml(self):
        data: dict = json.loads(self.json())
        xml: str = unparse(data, pretty=True)
        return xml
    
    @classmethod
    def _load_dict(cls, data: dict) -> 'Serializable':
        attributes: dict = getattr(cls, "_attributes", {})
        arguments: dict = {}
        for attr, alias_name in attributes.items():
            value = data.get(alias_name)
            
            attr_type: type = cls.__annotations__.get(attr, None)
            if isinstance(value, dict) and attr_type is not None and isinstance(attr_type, type) and issubclass(attr_type, Serializable):
                value = attr_type._load_dict(value)
            
            arguments[attr] = value

        return cls(**arguments)
    
    @classmethod
    def load(cls, raw: str):
        try:
            data: dict = json.loads(raw)
        except json.JSONDecodeError:
            data: dict = parse(raw)
        
        class_name: str = next(iter(data))
        
        cls = globals()[class_name]
        data = next(iter(data.values()))

        return cls._load_dict(data)