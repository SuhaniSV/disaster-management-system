from core.geo import haversine_km, path_crosses_blocked_road, segments_intersect


def test_haversine_zero():
    assert haversine_km(18.52, 73.85, 18.52, 73.85) == 0


def test_haversine_pune_to_nearby():
    d = haversine_km(18.5204, 73.8567, 18.5304, 73.8667)
    assert 1.0 < d < 3.0


def test_invalid_coords_are_infinite():
    assert haversine_km("bad", 1, 2, 3) == float("inf")


def test_segment_intersection():
    assert segments_intersect(0, 0, 1, 1, 0, 1, 1, 0)
    assert not segments_intersect(0, 0, 0, 1, 1, 0, 1, 1)


def test_blocked_road_detection():
    roads = [
        {
            "id": "R-07",
            "status": "Blocked",
            "from_lat": 0.0,
            "from_lon": 0.0,
            "to_lat": 1.0,
            "to_lon": 1.0,
        }
    ]
    hit = path_crosses_blocked_road(0.0, 1.0, 1.0, 0.0, roads)
    assert hit is not None
    assert hit["id"] == "R-07"
