from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

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
    gnss_positions: List[GnssPosition] = field(default_factory=List)
    trip_descriptor: Optional[TripDescriptor] = None
    trip_metrics: Optional[TripMetrics] = None

@dataclass
class TripDescriptor:
    trip_id: Optional[str] = None
    route_id: Optional[str] = None
    direction_id: Optional[str] = None
    start_date: Optional[str] = None
    start_time: Optional[str] = None
    schedule_relationship: Optional[str] = None

@dataclass
class TripMetrics:
    current_stop_id: Optional[str] = None
    next_stop_id: Optional[str] = None
    delay: Optional[str] = None