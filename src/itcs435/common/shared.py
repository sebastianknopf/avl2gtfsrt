import uuid

from datetime import datetime, timezone

def isotimestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def unixtimestamp() -> int:
    timestamp: float = datetime.now(timezone.utc).timestamp()
    return int(timestamp)

def uid() -> str:
    return str(uuid.uuid4())