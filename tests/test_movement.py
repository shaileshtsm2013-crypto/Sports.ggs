"""Unit tests for analytics movement, speed, and jump calculations."""
import pytest
from backend.app.analytics.movement import (
    calculate_cumulative_distance,
    count_direction_changes,
    smooth_trajectory,
)
from backend.app.analytics.speed import compute_speed_and_acceleration
from backend.app.analytics.jump import JumpDetector, JumpPhase


def test_cumulative_distance():
    """Test 3-4-5 triangle path distance."""
    # (0, 0) -> (3, 0) is 3; (3, 0) -> (3, 4) is 4. Total = 7.
    points = [(0.0, 0.0), (3.0, 0.0), (3.0, 4.0)]
    dist = calculate_cumulative_distance(points, pixels_to_meters=1.0)
    assert dist == pytest.approx(7.0)


def test_direction_changes():
    """Test acute angle direction reversal detection."""
    # Moving right, then reversing back left
    points = [(0.0, 0.0), (10.0, 0.0), (20.0, 0.0), (5.0, 0.0)]
    turns = count_direction_changes(points, angle_threshold_deg=60.0)
    assert turns >= 1


def test_speed_computation():
    """Test speed calculation with constant linear movement."""
    # 10 pixels per frame at 30 fps
    timed_points = [(float(i * 10), 0.0, float(i * (1.0 / 30.0))) for i in range(10)]
    stats = compute_speed_and_acceleration(timed_points)
    assert stats["avg_speed_mps"] > 0
    assert stats["max_speed_mps"] > 0


def test_jump_detector():
    """Test jump detection state machine on synthetic vertical oscillation."""
    detector = JumpDetector(pixels_to_cm=0.5)
    # Simulate athlete standing at y=300, jumping up to y=200, landing back at y=300
    y_profile = [300, 300, 270, 240, 210, 200, 220, 260, 300, 300]
    jumps = []
    for t, y in enumerate(y_profile):
        event = detector.update(center_y=float(y), timestamp=float(t * 0.033))
        if event:
            jumps.append(event)
    
    assert len(jumps) >= 1
    assert jumps[0]["estimated_height_cm"] >= 15.0
