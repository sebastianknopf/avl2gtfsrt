import uuid

from datetime import datetime, timezone
from shapely.ops import transform
from pyproj import CRS, Transformer

def isotimestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def unixtimestamp(iso_str: str|None = None) -> int:
    if iso_str is not None:
        timestamp: float = datetime.fromisoformat(iso_str).timestamp()
        return int(timestamp)
    else:
        timestamp: float = datetime.now(timezone.utc).timestamp()
        return int(timestamp)

def uid() -> str:
    return str(uuid.uuid4())

def web_mercator(geometry: object) -> object:
    transformer = Transformer.from_crs(
        CRS("EPSG:4326"),
        CRS("EPSG:3857"),
        always_xy=True
    )

    return transform(transformer.transform, geometry)

def wgs_84(geometry: object) -> object:
    transformer = Transformer.from_crs(
        CRS("EPSG:3857"),
        CRS("EPSG:4326"),
        always_xy=True
    )

    return transform(transformer.transform, geometry)

def clamp(value: float|int, min_value: float|int, max_value: float|int) -> float|int:
    return max(min_value, min(max_value, value))

def strip_feed_id(id: str) -> str:
    return ':'.join(id.split(':')[1:])