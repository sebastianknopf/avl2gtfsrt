from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class GnssPosition:
    latitude: float
    longitude: float
    timestamp: int

@dataclass
class Vehicle:
    vehicle_ref: str
    is_technically_logged_on: bool = False
    is_operationally_logged_on: bool = False

@dataclass
class VehicleActivity:
    vehicle_ref: str
    gnss_positions: list[GnssPosition] = field(default_factory=list)
    trip_descriptor: TripDescriptor|None = None
    trip_metrics: TripMetrics|None = None

@dataclass
class TripDescriptor:
    trip_id: str|None = None
    route_id: str|None = None
    direction_id: str|None = None
    start_date: str|None = None
    start_time: str|None = None
    schedule_relationship: str|None = None

@dataclass
class TripMetrics:
    current_stop_id: str|None = None
    next_stop_id: str|None = None
    delay: int|None = None