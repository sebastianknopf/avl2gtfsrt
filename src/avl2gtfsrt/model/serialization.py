from dataclasses import asdict
from dacite import from_dict

def serialize(obj):
    return asdict(obj)

def deserialize(cls, data):
    return from_dict(cls, data)