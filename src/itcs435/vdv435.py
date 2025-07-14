from xmltodict import unparse

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
    timestamp: str
    version: str

    def xml(self):
        attributes: dict = getattr(self.__class__, "_attributes", {})
        
        data:dict = {}
        for attr, alias_name in attributes.items():
            data[alias_name] = getattr(self, attr)

        class_name: str = self.__class__.__name__
        class_name = class_name.replace('Structure', '')

        xml: str = unparse({class_name: data}, pretty=True)

        return xml

@attributes(message_id='MessageId')   
class AbstractMessageStructure(AbstractBasicStructure):
    message_id: str