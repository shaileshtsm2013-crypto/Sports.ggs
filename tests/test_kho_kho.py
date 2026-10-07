"""Automated tests for Phase 5 Kho Kho Rules Engine, Violations, Events, and API Endpoints."""
import time
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.sports.kho_kho import (
    KhoKhoAnalyzer,
    CENTRAL_LANE_Y,
    CROSS_LANE_X_POSITIONS,
    get_confidence_level,
)

client = TestClient(app)


def test_kho_kho_analyzer_initialization():
    analyzer = KhoKhoAnalyzer()
    assert analyzer.sport_name == "kho_kho"
    assert analyzer.court_dimensions_meters["length"] == 27.0
    assert analyzer.court_dimensions_meters["width"] == 16.0
    assert analyzer.court_dimensions_meters["central_lane_y"] == CENTRAL_LANE_Y
    assert analyzer.runners_remaining == 3
    assert analyzer.runners_in_batch == 3
    assert analyzer.active_chaser_id is None


def test_confidence_level_helper():
    assert get_confidence_level(0.95) == "High"
    assert get_confidence_level(0.80) == "High"
    assert get_confidence_level(0.65) == "Medium"
    assert get_confidence_level(0.50) == "Medium"
    assert get_confidence_level(0.35) == "Low"
    assert get_confidence_level(0.0) == "Unknown"


def test_track_active_chaser():
    analyzer = KhoKhoAnalyzer()
    players = [
        {"player_id": 1, "confidence": 0.9, "kinematics": {"court_position": {"x_m": 10.0, "y_m": 8.5}, "instant_speed_mps": 2.5}},
        {"player_id": 2, "confidence": 0.9, "kinematics": {"court_position": {"x_m": 12.0, "y_m": 8.0}, "instant_speed_mps": 0.1}},
        {"player_id": 3, "role": "runner", "confidence": 0.9, "kinematics": {"court_position": {"x_m": 5.0, "y_m": 5.0}, "instant_speed_mps": 3.0}},
    ]
    # Player 1 has speed 2.5 m/s and is not a runner -> active chaser
    chaser_info = analyzer.track_active_chaser(players)
    assert chaser_info is not None
    assert chaser_info["player_id"] == 1


def test_chaser_square_detection():
    analyzer = KhoKhoAnalyzer()
    # First square center is (1.5, 8.0)
    sq0 = analyzer.get_chaser_square(1.5, 8.0)
    assert sq0 == 0

    # Second square center is (4.5, 8.0)
    sq1 = analyzer.get_chaser_square(4.55, 8.05)
    assert sq1 == 1

    # Outside square
    sq_none = analyzer.get_chaser_square(3.0, 8.0)
    assert sq_none is None


def test_free_zone_detection():
    analyzer = KhoKhoAnalyzer()
    assert analyzer.is_in_free_zone(1.0) is True
    assert analyzer.is_in_free_zone(1.5) is True
    assert analyzer.is_in_free_zone(10.0) is False
    assert analyzer.is_in_free_zone(22.5) is True
    assert analyzer.is_in_free_zone(24.0) is True


def test_direction_fault():
    analyzer = KhoKhoAnalyzer()
    # Continuing in committed direction ("right", curr_x > prev_x) is valid
    fault_none = analyzer.check_active_chaser_direction(
        chaser_id=1, curr_x=10.5, prev_x=10.2, committed_direction="right"
    )
    assert fault_none is None

    # Reversing direction outside free zone (moving left while committed to "right") triggers fault
    fault = analyzer.check_active_chaser_direction(
        chaser_id=1, curr_x=10.0, prev_x=10.3, committed_direction="right"
    )
    assert fault is not None
    assert fault["violation_type"] == "DIRECTION_FAULT"


def test_central_lane_crossing():
    analyzer = KhoKhoAnalyzer()
    # Crossing across central lane: from Y=7.5 (below 7.85) to Y=8.3 (above 8.15)
    v_cross = analyzer.check_central_lane_crossing(chaser_id=1, prev_y=7.5, curr_y=8.3)
    assert v_cross is not None
    assert v_cross["violation_type"] == "CENTRAL_LANE_CROSSING"

    # Staying on same side is valid
    assert analyzer.check_central_lane_crossing(chaser_id=1, prev_y=7.5, curr_y=7.6) is None


def test_kho_validity():
    analyzer = KhoKhoAnalyzer()
    # Active chaser near sitting chaser seated in square (dist <= 0.50m)
    evt_kho = analyzer.check_kho_validity(
        giver_id=1,
        receiver_id=2,
        giver_pos=(4.6, 8.1),
        receiver_pos=(4.5, 8.0),
        receiver_in_square=True,
    )
    assert evt_kho is not None
    assert evt_kho["event_type"] == "KHO_GIVEN"
    assert evt_kho["valid"] is True

    # Receiver not in square -> FALSE_KHO
    evt_false = analyzer.check_kho_validity(
        giver_id=1,
        receiver_id=2,
        giver_pos=(4.6, 8.1),
        receiver_pos=(4.5, 8.0),
        receiver_in_square=False,
    )
    assert evt_false is not None
    assert evt_false["event_type"] == "FALSE_KHO"
    assert evt_false["valid"] is False


def test_runner_tagged():
    analyzer = KhoKhoAnalyzer()
    # Active chaser at (10.0, 7.0), runner at (10.1, 7.0) -> distance 0.10m (< 0.30m)
    evt_tag = analyzer.check_runner_tagged(
        chaser_id=1,
        runner_id=10,
        chaser_pos=(10.0, 7.0),
        runner_pos=(10.1, 7.0),
    )
    assert evt_tag is not None
    assert evt_tag["event_type"] == "RUNNER_TAGGED"
    assert evt_tag["runner_id"] == 10


def test_chaser_seating():
    analyzer = KhoKhoAnalyzer()
    # Square 1 is at X=4.5, Y=8.0. Tolerance is 0.3m.
    # Seated properly
    assert analyzer.check_chaser_seating(chaser_id=2, x_m=4.55, y_m=8.0, assigned_square_idx=1) is None

    # Moved out of square to X=5.5
    fault = analyzer.check_chaser_seating(chaser_id=2, x_m=5.5, y_m=8.0, assigned_square_idx=1)
    assert fault is not None
    assert fault["violation_type"] == "CHASER_OUT_OF_SQUARE"


def test_analyze_frame_and_turn_reset():
    analyzer = KhoKhoAnalyzer()
    players = [
        {"player_id": 1, "confidence": 0.9, "kinematics": {"court_position": {"x_m": 10.0, "y_m": 8.5}, "instant_speed_mps": 2.0}},
        {"player_id": 10, "role": "runner", "confidence": 0.9, "kinematics": {"court_position": {"x_m": 10.1, "y_m": 8.5}, "instant_speed_mps": 0.5}},
    ]
    res = analyzer.analyze_frame(frame_idx=1, timestamp=0.033, players=players)
    assert res["sport"] == "kho_kho"
    assert res["active_chaser_id"] == 1
    assert analyzer.runners_remaining == 2

    # Reset turn
    analyzer.reset_turn()
    assert analyzer.active_chaser_id is None
    assert analyzer.runners_remaining == 3


def test_kho_kho_api_endpoints():
    res_reset = client.post("/api/analysis/kho_kho/reset-turn")
    assert res_reset.status_code == 200
    assert "status" in res_reset.json()

    res_status = client.get("/api/analysis/kho_kho/status")
    assert res_status.status_code == 200
    assert "runners_remaining" in res_status.json()

    res_events = client.get("/api/analysis/kho_kho/events")
    assert res_events.status_code == 200
    assert "events" in res_events.json()

    res_violations = client.get("/api/analysis/kho_kho/violations")
    assert res_violations.status_code == 200
    assert "violations" in res_violations.json()

    # Test with active pipeline
    start_res = client.post("/api/camera/start", json={"source": "synthetic", "sport": "kho_kho"})
    assert start_res.status_code == 200
    time.sleep(0.5)

    run_status = client.get("/api/analysis/kho_kho/status")
    assert run_status.status_code == 200

    stop_res = client.post("/api/camera/stop")
    assert stop_res.status_code == 200
