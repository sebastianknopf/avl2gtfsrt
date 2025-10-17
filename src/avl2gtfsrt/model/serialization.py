from dataclasses import asdict, fields, is_dataclass

def serialize(obj):
    return asdict(obj)

def deserialize(cls, data):
    args = {}
    for f in fields(cls):
        val = data.get(f.name)
        
        if is_dataclass(f.type) and isinstance(val, dict):
            val = deserialize(f.type, val)
        elif getattr(f.type, "__origin__", None) is list and hasattr(f.type.__args__[0], "__dataclass_fields__"):
            val = [deserialize(f.type.__args__[0], v) for v in val]
        
        args[f.name] = val

    return cls(**args)