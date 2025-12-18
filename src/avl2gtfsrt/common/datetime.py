from datetime import datetime

def get_operation_day_time_str(seconds_after_midnight: int) -> str:

    # re-calculate operation day start time
    hours = int(seconds_after_midnight // 3600)
    minutes = int((seconds_after_midnight % 3600) // 60)
    seconds = int(seconds_after_midnight % 60)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"