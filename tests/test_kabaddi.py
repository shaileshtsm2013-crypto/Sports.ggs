"""Automated tests for Phase 5 Kabaddi Rules Engine, Violations, Events, and API Endpoints."""
import time
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.sports.kabaddi import KabaddiAnalyzer, get_confidence_level

client = TestClient(app)


def test_kabaddi_analyzer_initialization():
    analyzer = KabaddiAnalyzer()
    assert analyzer.sport_name == "kabaddi"
    assert analyzer.court_dimensions_meters["length"] == 13.0
    assert analyzer.court_dimensions_meters["width"] == 10.0
    assert analyzer.court_dimensions_meters["midline_x"] == 6.5
    assert analyzer.court_dimensions_meters["team_a_baulk_x"] == 10.25
    assert analyzer.court_dimensions_meters["team_a_bonus_x"] == 11.25
    assert analyzer.court_dimensions_meters["team_b_baulk_x"] == 2.75
    assert analyzer.court_dimensions_meters["team_b_bonus_x"] == 1.75
    assert analyzer.raid_state == "WAITING"
    assert analyzer.active_raider_id is None
    assert analyzer.raid_points == 0


def test_confidence_level_helper():
    assert get_confidence_level(0.95) == "High"
    assert get_confidence_level(0.80) == "High"
    assert get_confidence_level(0.65) == "Medium"
    assert get_confidence_level(0.50) == "Medium"
    assert get_confidence_level(0.35) == "Low"
    assert get_confidence_level(0.0) == "Unknown"
    assert get_confidence_level(None) == "Unknown"


def test_raider_identification():
    analyzer = KabaddiAnalyzer()
    players = [
        {"player_id": 1, "confidence": 0.9, "kinematics": {"court_position": {"x_m": 8.0, "y_m": 5.0}}},
        {"player_id": 2, "confidence": 0.9, "kinematics": {"court_position": {"x_m": 3.0, "y_m": 4.0}}},
        {"player_id": 3, "confidence": 0.9, "kinematics": {"court_position": {"x_m": 3.5, "y_m": 6.0}}},
    ]
    # Player 1 is on right half (X > 6.5) while players 2 and 3 are on left half (X < 6.5)
    raider_info = analyzer.check_raider_identification(players)
    assert raider_info is not None
    assert raider_info["player_id"] == 1
    assert raider_info["raiding_team"] == "Team A"


def test_baulk_line_crossing():
    analyzer = KabaddiAnalyzer()
    # Team A raiding to the right needs X >= 10.25
    evt_none = analyzer.check_baulk_line_crossing(raider_id=1, raiding_team="Team A", x_m=9.5)
    assert evt_none is None

    evt_crossed = analyzer.check_baulk_line_crossing(raider_id=1, raiding_team="Team A", x_m=10.3)
    assert evt_crossed is not None
    assert evt_crossed["event_type"] == "BAULK_CROSSED"
    assert evt_crossed["raider_id"] == 1

    # Team B raiding to the left needs X <= 2.75
    evt_b = analyzer.check_baulk_line_crossing(raider_id=2, raiding_team="Team B", x_m=2.5)
    assert evt_b is not None
    assert evt_b["event_type"] == "BAULK_CROSSED"


def test_bonus_line_touch():
    analyzer = KabaddiAnalyzer()
    # Bonus line requires >= 6 defenders
    evt_few_defenders = analyzer.check_bonus_line_touch(
        raider_id=1, raiding_team="Team A", x_m=11.3, defenders_on_court=5
    )
    assert evt_few_defenders is None

    # With >= 6 defenders and crossing X >= 11.25
    evt_bonus = analyzer.check_bonus_line_touch(
        raider_id=1, raiding_team="Team A", x_m=11.3, defenders_on_court=6
    )
    assert evt_bonus is not None
    assert evt_bonus["event_type"] == "BONUS_POINT"
    assert evt_bonus["bonus_points"] == 1

    # Team B bonus line: X <= 1.75
    evt_bonus_b = analyzer.check_bonus_line_touch(
        raider_id=2, raiding_team="Team B", x_m=1.5, defenders_on_court=7
    )
    assert evt_bonus_b is not None
    assert evt_bonus_b["event_type"] == "BONUS_POINT"


def test_out_of_bounds_detection():
    analyzer = KabaddiAnalyzer()
    assert analyzer.check_out_of_bounds(player_id=1, x_m=6.0, y_m=5.0) is None

    v_out_x = analyzer.check_out_of_bounds(player_id=2, x_m=13.5, y_m=5.0)
    assert v_out_x is not None
    assert v_out_x["violation_type"] == "OUT_OF_BOUNDS"

    # Without lobby contact, Y=10.5 is out of bounds
    v_out_y = analyzer.check_out_of_bounds(player_id=3, x_m=6.0, y_m=10.5, lobby_active=False)
    assert v_out_y is not None
    assert v_out_y["violation_type"] == "OUT_OF_BOUNDS"

    # With lobby contact active, Y=10.5 is inside lobby (lobby extends to Y=11.0)
    assert analyzer.check_out_of_bounds(player_id=3, x_m=6.0, y_m=10.5, lobby_active=True) is None


def test_tackle_detection():
    analyzer = KabaddiAnalyzer()
    defenders_many = [
        {"player_id": 2, "kinematics": {"court_position": {"x_m": 8.5, "y_m": 5.2}}},
        {"player_id": 3, "kinematics": {"court_position": {"x_m": 9.0, "y_m": 6.0}}},
        {"player_id": 4, "kinematics": {"court_position": {"x_m": 9.5, "y_m": 4.0}}},
        {"player_id": 5, "kinematics": {"court_position": {"x_m": 10.0, "y_m": 5.0}}},
    ]
    # Raider at (8.0, 5.0); Defender 2 is at dist ~0.54m (< 1.5m)
    evt_tackle = analyzer.check_tackle_zone(raider_id=1, raider_x=8.0, raider_y=5.0, defenders=defenders_many)
    assert evt_tackle is not None
    assert evt_tackle["event_type"] == "TACKLE_ATTEMPT"
    assert evt_tackle["points"] == 1

    # Super Tackle when <= 3 defenders total
    defenders_few = [
        {"player_id": 2, "kinematics": {"court_position": {"x_m": 8.5, "y_m": 5.2}}},
        {"player_id": 3, "kinematics": {"court_position": {"x_m": 9.0, "y_m": 6.0}}},
    ]
    evt_super = analyzer.check_tackle_zone(raider_id=1, raider_x=8.0, raider_y=5.0, defenders=defenders_few)
    assert evt_super is not None
    assert evt_super["event_type"] == "SUPER_TACKLE"
    assert evt_super["points"] == 2


def test_do_or_die_raid():
    analyzer = KabaddiAnalyzer()
    analyzer._consecutive_empty_raids["Team A"] = 2
    evt_none = analyzer.check_do_or_die_raid("Team A")
    assert evt_none is None

    analyzer._consecutive_empty_raids["Team A"] = 3
    evt_dod = analyzer.check_do_or_die_raid("Team A")
    assert evt_dod is not None
    assert evt_dod["event_type"] == "DO_OR_DIE_RAID"
    assert analyzer._do_or_die_active is True


def test_all_out():
    analyzer = KabaddiAnalyzer()
    assert analyzer.check_all_out("Team B", defenders_on_court=2) is None
    all_out_evt = analyzer.check_all_out("Team B", defenders_on_court=0)
    assert all_out_evt is not None
    assert all_out_evt["event_type"] == "ALL_OUT"
    assert all_out_evt["bonus_points"] == 2


def test_analyze_frame_and_reset():
    analyzer = KabaddiAnalyzer()
    players = [
        {"player_id": 1, "confidence": 0.9, "kinematics": {"court_position": {"x_m": 8.0, "y_m": 5.0}}},
        {"player_id": 2, "confidence": 0.9, "kinematics": {"court_position": {"x_m": 3.0, "y_m": 4.0}}},
    ]
    res1 = analyzer.analyze_frame(frame_idx=1, timestamp=0.033, players=players)
    assert res1["sport"] == "kabaddi"
    assert res1["raid_state"] == "RAID_ACTIVE"
    assert res1["active_raider_id"] == 1

    # Reset raid
    analyzer.reset_raid()
    assert analyzer.raid_state == "WAITING"
    assert analyzer.active_raider_id is None
    assert analyzer.raid_points == 0


def test_kabaddi_api_endpoints():
    # Test inactive pipeline responses
    res_reset = client.post("/api/analysis/kabaddi/reset-raid")
    assert res_reset.status_code == 200
    assert res_reset.json()["raid_state"] == "WAITING"

    res_status = client.get("/api/analysis/kabaddi/status")
    assert res_status.status_code == 200
    assert "raid_state" in res_status.json()

    res_events = client.get("/api/analysis/kabaddi/events")
    assert res_events.status_code == 200
    assert "events" in res_events.json()

    res_violations = client.get("/api/analysis/kabaddi/violations")
    assert res_violations.status_code == 200
    assert "violations" in res_violations.json()

    # Test with active pipeline
    start_res = client.post("/api/camera/start", json={"source": "synthetic", "sport": "kabaddi"})
    assert start_res.status_code == 200
    time.sleep(0.5)

    run_status = client.get("/api/analysis/kabaddi/status")
    assert run_status.status_code == 200
    assert "raid_state" in run_status.json()

    stop_res = client.post("/api/camera/stop")
    assert stop_res.status_code == 200
