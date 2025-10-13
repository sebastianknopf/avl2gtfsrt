from datetime import datetime

def get_operation_day(operation_day: str) -> int:
    
    # remove hyphens (-) and convert result to int
    return int(operation_day.replace("-", ""))

def get_operation_time(operation_day: str, iso_timestamp: str) -> str:
    
    # calculate difference between operation day start and trip start timestamp
    dt: datetime = datetime.fromisoformat(iso_timestamp)
    ref: datetime = datetime.fromisoformat(operation_day).replace(tzinfo=dt.tzinfo)

    diff_seconds: int = (dt - ref).total_seconds()

    # re-calculate operation day start time
    hours = int(diff_seconds // 3600)
    minutes = int((diff_seconds % 3600) // 60)
    seconds = int(diff_seconds % 60)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"