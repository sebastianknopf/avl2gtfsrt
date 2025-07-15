import json

from pydantic import BaseModel
from xmltodict import parse, unparse

__registry: dict = {}

class Serializable(BaseModel):

    def __init_subclass__(cls, **arguments):
        super().__init_subclass__(**arguments)

        globals()['__registry'][cls.__name__] = cls
    
    def json(self):
        class_name: str = self.__class__.__name__
        json_str: str = json.dumps({
            class_name: self.model_dump(by_alias=True, exclude_none=True)
        }, indent=4, ensure_ascii=False)

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

        cls = globals()['__registry'][class_name]
        data = next(iter(data.values()))

        return cls(**data)