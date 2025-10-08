import os

from datetime import datetime

def is_set(variable_name: str) -> bool:
    variable_value: str = os.getenv(variable_name, 'false').lower().strip()
    return variable_value == 'true' or variable_value == '1'

def is_debug() -> bool:
    return is_set('A2G_DEBUG')