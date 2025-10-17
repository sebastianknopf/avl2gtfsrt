import math

from avl2gtfsrt.model.types import GnssPosition


class SpatialVector:

    def __init__(self, gnss_position_start: GnssPosition, gnss_position_end: GnssPosition):
        self.start = gnss_position_start
        self.end = gnss_position_end

        self._cached_length: float|None = None
        self._cached_bearing: float|None = None

    def length(self) -> float:
        if self._cached_length is None:
            self._cached_length = self._haversine_distance(
                (self.start.latitude, self.start.longitude),
                (self.end.latitude, self.end.longitude)
            )
        
        return self._cached_length

    def bearing(self) -> float:
        if self._cached_bearing is None:
            self._cached_bearing = self._calculate_bearing(
                (self.start.latitude, self.start.longitude),
                (self.end.latitude, self.end.longitude)
            )

        return self._cached_bearing

    def _haversine_distance(self, coord1: tuple[float, float], coord2: tuple[float, float]) -> float:
        lat1, lon1 = map(math.radians, coord1)
        lat2, lon2 = map(math.radians, coord2)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return 6371000 * c
    
    def _calculate_bearing(self, coord1: tuple[float, float], coord2: tuple[float, float]) -> float:
        lat1, lon1 = map(math.radians, coord1)
        lat2, lon2 = map(math.radians, coord2)

        dlon = lon2 - lon1

        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)

        bearing_rad = math.atan2(x, y)
        bearing_deg = math.degrees(bearing_rad)

        return (bearing_deg + 360) % 360
    

class SpatialVectorCollection:

    def __init__(self, gnss_positions: list[GnssPosition]) -> None:
        self.spatial_vectors: list[SpatialVector] = []

        if len(gnss_positions) < 2:
            raise ValueError('At least 2 GNSS positions are required for creating a vector or vector collection!')

        for p in range(0, len(gnss_positions) - 1):
            pos1: GnssPosition = gnss_positions[p]
            pos2: GnssPosition = gnss_positions[p + 1]

            self.spatial_vectors.append(
                SpatialVector(pos1, pos2)
            )

    def length(self) -> float:
        total_length: float = sum([v.length() for v in self.spatial_vectors])
        return total_length
    
    def bearing(self) -> float:
        bearing_vector: SpatialVector = SpatialVector(
            self.spatial_vectors[0].start,
            self.spatial_vectors[-1].end
        )

        return bearing_vector.bearing()

    def is_movement(self, min_distance: int = 50) -> bool:
        total_distance: float = self.length()
        direct_distance: float = SpatialVector(
            self.spatial_vectors[0].start,
            self.spatial_vectors[-1].end
        ).length()

        if total_distance < min_distance:
            return False
        
        linearity: float = direct_distance / total_distance if total_distance > 0 else 0

        return linearity > 0.35