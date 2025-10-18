from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

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
    activity: Optional[VehicleActivity] = None

@dataclass
class VehicleActivity:
    gnss_positions: list[GnssPosition] = field(default_factory=list)
    trip_candidate_convergence: bool = False
    trip_candidate_probabilities: dict = field(default_factory=dict)
    trip_candidate_failures: int = 0
    trip_descriptor: Optional[TripDescriptor] = None
    trip_metrics: Optional[TripMetrics] = None

@dataclass
class Stop:
    stop_id: str
    latitude: float
    longitude: float
    name: Optional[str] = None

@dataclass
class StopTime:
    arrival_timestamp: int 
    departure_timestamp: int
    stop_sequence: int
    stop: Stop

@dataclass
class Trip:
    descriptor: TripDescriptor
    stop_times: list[StopTime] = field(default_factory=list)
    shape_polyline: str

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
    current_stop_sequence: Optional[int] = None
    current_stop_id: Optional[str] = None
    next_stop_sequence: Optional[int] = None
    next_stop_id: Optional[str] = None
    current_stop_status: Optional[str] = None
    current_delay: Optional[int] = None