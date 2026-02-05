def get_operating_day_time_str(seconds_after_midnight: int) -> str:

    # re-calculate operation day start time
    hours = int(seconds_after_midnight // 3600)
    minutes = int((seconds_after_midnight % 3600) // 60)
    seconds = int(seconds_after_midnight % 60)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def get_operating_day_seconds(operating_day_time_str: str) -> int:
    parts = operating_day_time_str.split(':')
    if len(parts) != 3:
        raise ValueError(f"Invalid operating day time string: {operating_day_time_str}")

    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = int(parts[2])

    return hours * 3600 + minutes * 60 + seconds