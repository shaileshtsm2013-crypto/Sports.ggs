"""Automated tests for Phase 4 Volleyball Rules Engine, Violations, Events, and API Endpoints."""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.sports.volleyball import VolleyballAnalyzer, get_confidence_level
from backend.app.vision.pipeline import VisionPipeline


client = TestClient(app)


def test_volleyball_analyzer_initialization():
    analyzer = VolleyballAnalyzer(net_gender="men")
    assert analyzer.sport_name == "volleyball"
    assert analyzer.court_dimensions_meters["length"] == 18.0
    assert analyzer.court_dimensions_meters["width"] == 9.0
    assert analyzer.court_dimensions_meters["center_x"] == 9.0
    assert analyzer.court_dimensions_meters["team_a_attack_x"] == 6.0
    assert analyzer.court_dimensions_meters["team_b_attack_x"] == 12.0
    assert analyzer.court_dimensions_meters["selected_net_height"] == 2.43

    analyzer.set_net_height("women")
    assert analyzer.court_dimensions_meters["selected_net_height"] == 2.24


def test_court_side_classification():
    analyzer = VolleyballAnalyzer()
    assert analyzer.classify_court_side(4.5) == "Team A"
    assert analyzer.classify_court_side(8.9) == "Team A"
    assert analyzer.classify_court_side(9.0) == "Team A"
    assert analyzer.classify_court_side(9.1) == "Team B"
    assert analyzer.classify_court_side(14.0) == "Team B"


def test_zone_and_row_classification():
    analyzer = VolleyballAnalyzer()

    # Team A front-row (X >= 6.0m)
    zone_4, row_4 = analyzer.classify_zone(7.5, 1.5, "Team A")
    assert zone_4 == 4
    assert row_4 == "front"

    zone_3, row_3 = analyzer.classify_zone(7.5, 4.5, "Team A")
    assert zone_3 == 3
    assert row_3 == "front"

    zone_2, row_2 = analyzer.classify_zone(7.5, 7.5, "Team A")
    assert zone_2 == 2
    assert row_2 == "front"

    # Team A back-row (X < 6.0m)
    zone_5, row_5 = analyzer.classify_zone(3.0, 1.5, "Team A")
    assert zone_5 == 5
    assert row_5 == "back"

    zone_6, row_6 = analyzer.classify_zone(3.0, 4.5, "Team A")
    assert zone_6 == 6
    assert row_6 == "back"

    zone_1, row_1 = analyzer.classify_zone(3.0, 7.5, "Team A")
    assert zone_1 == 1
    assert row_1 == "back"

    # Team B front-row (X <= 12.0m)
    zone_b2, row_b2 = analyzer.classify_zone(10.5, 1.5, "Team B")
    assert zone_b2 == 2
    assert row_b2 == "front"

    zone_b4, row_b4 = analyzer.classify_zone(10.5, 7.5, "Team B")
    assert zone_b4 == 4
    assert row_b4 == "front"

    # Team B back-row (X > 12.0m)
    zone_b1, row_b1 = analyzer.classify_zone(15.0, 1.5, "Team B")
    assert zone_b1 == 1
    assert row_b1 == "back"


def test_center_line_penetration_detection():
    analyzer = VolleyballAnalyzer()

    # Legal play: Team A player at X = 8.5m
    legal = analyzer.check_center_line_penetration(player_id=1, team="Team A", x_m=8.5)
    assert legal is None

    # Illegal penetration: Team A player crosses over center line into Team B (X = 9.35m > 9.15m)
    foul_a = analyzer.check_center_line_penetration(
        player_id=1,
        team="Team A",
        x_m=9.35,
        pose_keypoints={"left_ankle": {"confidence": 0.88}, "right_ankle": {"confidence": 0.90}}
    )
    assert foul_a is not None
    assert foul_a["violation_type"] == "CENTER_LINE_PENETRATION"
    assert foul_a["team"] == "Team A"
    assert foul_a["penetration_meters"] == 0.35
    assert foul_a["confidence_level"] == "High"

    # Illegal penetration: Team B player crosses over into Team A (X = 8.60m < 8.85m)
    foul_b = analyzer.check_center_line_penetration(player_id=2, team="Team B", x_m=8.60)
    assert foul_b is not None
    assert foul_b["violation_type"] == "CENTER_LINE_PENETRATION"
    assert foul_b["team"] == "Team B"
    assert foul_b["penetration_meters"] == 0.40


def test_net_touch_violation_detection():
    analyzer = VolleyballAnalyzer()

    # Airborne player contacting net plane at X = 9.08m (dist to net 0.08m <= 0.25m)
    foul = analyzer.check_net_touch(
        player_id=3,
        team="Team A",
        x_m=9.08,
        is_airborne=True,
        pose_keypoints={"right_wrist": {"confidence": 0.85}}
    )
    assert foul is not None
    assert foul["violation_type"] == "NET_TOUCH"
    assert foul["contact_keypoint"] == "right_wrist"
    assert foul["confidence_level"] == "High"

    # Standing player near net: not an active jump net touch
    no_foul = analyzer.check_net_touch(
        player_id=3,
        team="Team A",
        x_m=9.08,
        is_airborne=False
    )
    assert no_foul is None

    # Airborne player away from net (X = 7.0m)
    far_foul = analyzer.check_net_touch(
        player_id=3,
        team="Team A",
        x_m=7.0,
        is_airborne=True
    )
    assert far_foul is None


def test_back_row_attack_fault():
    analyzer = VolleyballAnalyzer()

    # Illegal: Back-row player takes off inside front attack zone (X = 6.8m > 6.0m) and spikes
    foul = analyzer.check_back_row_attack(
        player_id=5,
        team="Team A",
        role="back",
        takeoff_x=6.8,
        is_spiking=True,
        confidence=0.86
    )
    assert foul is not None
    assert foul["violation_type"] == "BACK_ROW_ATTACK"
    assert foul["margin_inside_front_zone"] == 0.80
    assert foul["confidence_level"] == "High"

    # Legal: Back-row player takes off from behind attack line (X = 5.2m < 6.0m)
    legal = analyzer.check_back_row_attack(
        player_id=5,
        team="Team A",
        role="back",
        takeoff_x=5.2,
        is_spiking=True
    )
    assert legal is None

    # Legal: Front-row player attacking inside front zone
    legal_front = analyzer.check_back_row_attack(
        player_id=4,
        team="Team A",
        role="front",
        takeoff_x=7.5,
        is_spiking=True
    )
    assert legal_front is None


def test_rotational_fault_detector():
    analyzer = VolleyballAnalyzer()

    # Valid Team A formation: Front row closer to net (higher X) than back row
    valid_team_a = [
        {"player_id": 4, "zone": 4, "x_m": 7.5, "y_m": 1.5},
        {"player_id": 3, "zone": 3, "x_m": 7.5, "y_m": 4.5},
        {"player_id": 2, "zone": 2, "x_m": 7.5, "y_m": 7.5},
        {"player_id": 5, "zone": 5, "x_m": 3.0, "y_m": 1.5},
        {"player_id": 6, "zone": 6, "x_m": 3.0, "y_m": 4.5},
        {"player_id": 1, "zone": 1, "x_m": 3.0, "y_m": 7.5},
    ]
    assert analyzer.check_rotation_fault(valid_team_a, "Team A") is None

    # Rotational fault: Zone 4 (front) is behind Zone 5 (back)
    faulty_team_a = [
        {"player_id": 4, "zone": 4, "x_m": 2.5, "y_m": 1.5},  # Inverted!
        {"player_id": 3, "zone": 3, "x_m": 7.5, "y_m": 4.5},
        {"player_id": 2, "zone": 2, "x_m": 7.5, "y_m": 7.5},
        {"player_id": 5, "zone": 5, "x_m": 4.0, "y_m": 1.5},
        {"player_id": 6, "zone": 6, "x_m": 3.0, "y_m": 4.5},
        {"player_id": 1, "zone": 1, "x_m": 3.0, "y_m": 7.5},
    ]
    fault = analyzer.check_rotation_fault(faulty_team_a, "Team A")
    assert fault is not None
    assert fault["violation_type"] == "ROTATION_FAULT"
    assert "Zone 4" in fault["description"]


def test_spike_vs_block_classification():
    analyzer = VolleyballAnalyzer()

    # Block: Close to net (within 1.2m) with dual raised wrists (smaller Y in image)
    block_evt = analyzer.classify_jump_action(
        player_id=2,
        team="Team A",
        x_m=9.15,
        is_airborne=True,
        jump_height_cm=48.0,
        pose_keypoints={
            "left_wrist": {"y": 150},
            "left_shoulder": {"y": 250},
            "right_wrist": {"y": 150},
            "right_shoulder": {"y": 250}
        }
    )
    assert block_evt is not None
    assert block_evt["event_type"] == "BLOCK"
    assert block_evt["confidence_level"] == "High"

    # Spike: Attacker near attack zone with dominant overhead arm
    spike_evt = analyzer.classify_jump_action(
        player_id=4,
        team="Team A",
        x_m=7.8,
        is_airborne=True,
        jump_height_cm=62.0,
        pose_keypoints={
            "right_wrist": {"y": 120},
            "nose": {"y": 180},
            "right_shoulder": {"y": 220},
            "left_wrist": {"y": 300},
            "left_shoulder": {"y": 220}
        }
    )
    assert spike_evt is not None
    assert spike_evt["event_type"] == "SPIKE"
    assert spike_evt["jump_height_cm"] == 62.0


def test_rally_state_machine_and_reset():
    analyzer = VolleyballAnalyzer()
    assert analyzer.rally_state == "IDLE"

    # Frame 1: Server behind baseline initiates serve
    res1 = analyzer.analyze_frame(
        frame_idx=1,
        timestamp=1.0,
        players=[{
            "player_id": 1,
            "confidence": 0.9,
            "kinematics": {"court_position": {"x_m": 0.2, "y_m": 7.5}, "instant_speed_mps": 2.0, "movement_state": "standing"},
            "pose": {"right_wrist": {"y": 100}, "right_shoulder": {"y": 200}}
        }]
    )
    assert res1["rally_state"] == "SERVE"
    assert res1["serving_team"] == "Team A"

    # Frame 2: Attacker spikes -> transitions rally to RALLY_ACTIVE
    res2 = analyzer.analyze_frame(
        frame_idx=2,
        timestamp=2.5,
        players=[{
            "player_id": 4,
            "confidence": 0.9,
            "kinematics": {"court_position": {"x_m": 7.8, "y_m": 2.0}, "instant_speed_mps": 4.5, "movement_state": "airborne", "highest_jump_cm": 55.0},
            "pose": {"right_wrist": {"y": 100}, "nose": {"y": 180}, "right_shoulder": {"y": 220}}
        }]
    )
    assert res2["rally_state"] == "RALLY_ACTIVE"
    assert res2["contacts_count"] >= 1

    # Reset rally
    analyzer.reset_rally()
    assert analyzer.rally_state == "IDLE"
    assert analyzer.rally_start_time is None
    assert analyzer.contacts_count == 0


def test_confidence_level_helper():
    assert get_confidence_level(0.95) == "High"
    assert get_confidence_level(0.80) == "High"
    assert get_confidence_level(0.65) == "Medium"
    assert get_confidence_level(0.50) == "Medium"
    assert get_confidence_level(0.35) == "Low"
    assert get_confidence_level(0.0) == "Unknown"
    assert get_confidence_level(None) == "Unknown"


def test_volleyball_api_endpoints():
    # 1. Test inactive pipeline responses
    res_reset = client.post("/api/analysis/volleyball/reset-rally")
    assert res_reset.status_code == 200
    assert res_reset.json()["rally_state"] == "IDLE"

    res_status = client.get("/api/analysis/volleyball/status")
    assert res_status.status_code == 200
    assert "rally_state" in res_status.json()

    res_events = client.get("/api/analysis/volleyball/events")
    assert res_events.status_code == 200
    assert "events" in res_events.json()

    res_violations = client.get("/api/analysis/volleyball/violations")
    assert res_violations.status_code == 200
    assert "violations" in res_violations.json()

    # 2. Test with active pipeline
    import time
    start_res = client.post("/api/camera/start", json={"source": "synthetic", "sport": "volleyball"})
    assert start_res.status_code == 200
    time.sleep(0.6)

    # Verify status while running
    run_status = client.get("/api/analysis/volleyball/status")
    assert run_status.status_code == 200
    assert "rally_state" in run_status.json()

    # Test reset rally while running
    reset_active = client.post("/api/analysis/volleyball/reset-rally")
    assert reset_active.status_code == 200
    assert reset_active.json()["rally_state"] == "IDLE"

    # Stop camera
    stop_res = client.post("/api/camera/stop")
    assert stop_res.status_code == 200

