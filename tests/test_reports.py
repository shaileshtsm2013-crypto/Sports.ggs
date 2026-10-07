"""Unit and integration tests for Match Reports, Player Reports, Video Replay, and Export (Phase 8)."""
import json
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.analytics.reports import (
    ReportGenerator,
    MatchReport,
    PlayerReport,
    format_duration,
    format_timestamp_mm_ss,
)
from backend.app.analytics.kinematics import KinematicsEngine, PlayerKinematics


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def report_generator():
    return ReportGenerator()


# ── UTILITY TESTS ─────────────────────────────────────────────────────────────

def test_format_duration():
    assert format_duration(0.0) == "00:00:00"
    assert format_duration(59.0) == "00:00:59"
    assert format_duration(3665.0) == "01:01:05"
    assert format_duration(5072.0) == "01:24:32"


def test_format_timestamp_mm_ss():
    assert format_timestamp_mm_ss(0.0) == "00:00"
    assert format_timestamp_mm_ss(45.0) == "00:45"
    assert format_timestamp_mm_ss(125.0) == "02:05"
    assert format_timestamp_mm_ss(754.0) == "12:34"


# ── REPORT GENERATOR UNIT TESTS ───────────────────────────────────────────────

def test_empty_match_report(report_generator):
    report = report_generator.generate_live_match_report(None)
    assert report.match_id == "none"
    assert report.duration_formatted == "00:00:00"
    assert report.total_distance_km == 0.0
    assert report.players_detected == 0
    assert len(report.players) == 0


def test_player_kinematics_with_time_series_and_jumps():
    """Verify PlayerKinematics samples time-series and calculates court coverage."""
    pkin = PlayerKinematics(player_id=7, pixels_to_meters=0.02)

    # Simulate movements across court
    for i in range(15):
        t = i * 0.25
        pkin.update(center_x=100.0 + i * 20, center_y=150.0 + (i % 3) * 30, timestamp=t)

    snapshot = pkin.get_snapshot()
    assert snapshot.total_distance_m > 0
    assert snapshot.court_coverage_pct > 0.0
    assert len(pkin.time_series) >= 5
    assert "court_x_m" in pkin.time_series[0]


def test_generate_live_player_report(report_generator):
    """Test individual player report generation with all chart datasets."""
    # Mock pipeline with populated kinematics
    mock_pipeline = MagicMock()
    mock_pipeline.sport = "volleyball"
    mock_pipeline.volleyball_analyzer = None
    mock_pipeline.is_running = True
    mock_pipeline.get_latest_telemetry.return_value = {"elapsed_time": 60.0, "fps": 30.0, "players": []}

    engine = KinematicsEngine(pixels_to_meters=0.02)
    pkin = PlayerKinematics(player_id=7, pixels_to_meters=0.02)
    for i in range(10):
        pkin.update(center_x=200.0 + i * 10, center_y=300.0, timestamp=i * 0.25)
    engine.players[7] = pkin
    mock_pipeline.kinematics_engine = engine

    player_rep = report_generator.generate_live_player_report(mock_pipeline, player_id=7)
    assert player_rep.player_id == 7
    assert player_rep.total_distance_m > 0
    assert len(player_rep.speed_over_time) >= 3
    assert len(player_rep.acceleration_over_time) >= 3
    assert len(player_rep.distance_over_time) >= 3
    assert len(player_rep.movement_map) >= 3


def test_generate_live_match_report_volleyball(report_generator):
    """Test volleyball live match report with events and markers."""
    mock_pipeline = MagicMock()
    mock_pipeline.sport = "volleyball"
    mock_pipeline.is_running = True
    mock_pipeline.get_latest_telemetry.return_value = {
        "elapsed_time": 300.0,
        "fps": 29.8,
        "players": [{"player_id": 1, "team": "Team A", "jersey_number": "#10"}]
    }

    engine = KinematicsEngine(pixels_to_meters=0.02)
    pkin = PlayerKinematics(player_id=1, pixels_to_meters=0.02)
    for i in range(5):
        pkin.update(center_x=100.0, center_y=100.0 + i * 15, timestamp=i * 0.3)
    engine.players[1] = pkin
    mock_pipeline.kinematics_engine = engine

    vb_mock = MagicMock()
    vb_mock.rally_state.value = "RALLY"
    vb_mock.total_rallies = 14
    vb_mock.spike_count = 8
    vb_mock.block_count = 5
    vb_mock.recent_events = [
        {"timestamp": 12.5, "type": "spike", "player_id": 1, "details": "Overhead spike", "confidence": 0.88}
    ]
    vb_mock.all_violations = [
        {"timestamp": 45.0, "type": "net_touch", "player_id": 1, "confidence": 0.92}
    ]
    mock_pipeline.volleyball_analyzer = vb_mock

    report = report_generator.generate_live_match_report(mock_pipeline)
    assert report.sport == "volleyball"
    assert report.duration_formatted == "00:05:00"
    assert report.sport_summary["total_spikes"] == 8
    assert len(report.events) >= 2
    assert len(report.timeline_markers) >= 2


def test_generate_live_match_report_kabaddi(report_generator):
    """Test kabaddi live match report."""
    mock_pipeline = MagicMock()
    mock_pipeline.sport = "kabaddi"
    mock_pipeline.is_running = True
    mock_pipeline.get_latest_telemetry.return_value = {"elapsed_time": 120.0, "fps": 30.0, "players": []}

    engine = KinematicsEngine(pixels_to_meters=0.02)
    mock_pipeline.kinematics_engine = engine

    kb_mock = MagicMock()
    kb_mock.raid_state.value = "RAID_ACTIVE"
    kb_mock.team_a_score = 15
    kb_mock.team_b_score = 12
    kb_mock.active_raider_id = 3
    kb_mock.total_raids = 20
    kb_mock.total_tackles = 7
    kb_mock.super_tackles = 2
    kb_mock.all_outs_team_a = 1
    kb_mock.all_outs_team_b = 0
    kb_mock.get_events.return_value = [
        {"timestamp": 35.0, "type": "bonus_point", "raider_id": 3, "details": "Bonus crossed", "confidence": 0.95}
    ]
    mock_pipeline.kabaddi_analyzer = kb_mock

    report = report_generator.generate_live_match_report(mock_pipeline)
    assert report.sport == "kabaddi"
    assert report.sport_summary["team_a_score"] == 15
    assert report.sport_summary["total_tackles"] == 7
    assert len(report.events) == 1


# ── EXPORT TESTS ──────────────────────────────────────────────────────────────

def test_export_match_json(report_generator):
    mock_rep = MatchReport(
        match_id="test_1",
        title="Test Match",
        sport="volleyball",
        status="completed",
        started_at="2026-09-27T10:00:00",
        ended_at="2026-09-27T10:30:00",
        duration_sec=1800.0,
        duration_formatted="00:30:00",
        fps=30.0,
        players_detected=6,
        active_players=6,
        total_distance_km=2.4,
        total_jumps=42,
        max_speed_mps=6.8,
        avg_speed_mps=3.2,
        sport_summary={"total_spikes": 12},
        players=[{"player_id": 1, "jersey_number": "#7", "team": "Team A", "total_distance_m": 400.0}],
        events=[{"timestamp": 10.0, "formatted_time": "00:10", "event_type": "spike", "details": "Spike"}],
        timeline_markers=[{"timestamp": 10.0, "formatted_time": "00:10", "event_type": "spike"}]
    )

    json_str = report_generator.export_match_json(mock_rep)
    data = json.loads(json_str)
    assert data["match_id"] == "test_1"
    assert data["total_jumps"] == 42
    assert len(data["players"]) == 1


def test_export_match_csv(report_generator):
    mock_rep = MatchReport(
        match_id="test_1",
        title="Test Match",
        sport="volleyball",
        status="completed",
        started_at="2026-09-27T10:00:00",
        ended_at=None,
        duration_sec=600.0,
        duration_formatted="00:10:00",
        fps=30.0,
        players_detected=2,
        active_players=2,
        total_distance_km=0.8,
        total_jumps=10,
        max_speed_mps=5.5,
        avg_speed_mps=2.8,
        sport_summary={},
        players=[
            {"player_id": 7, "jersey_number": "#7", "team": "Team A", "role": "spiker",
             "total_distance_m": 420.0, "max_speed_mps": 5.5, "avg_speed_mps": 2.8,
             "max_acceleration_mps2": 3.1, "jumps_count": 10, "highest_jump_cm": 45.0,
             "avg_jump_height_cm": 38.0, "court_coverage_pct": 65.0, "direction_changes": 8}
        ],
        events=[{"timestamp": 12.0, "formatted_time": "00:12", "event_type": "spike", "player_id": 7, "details": "Spike", "confidence": 0.85}]
    )

    csv_str = report_generator.export_match_csv(mock_rep)
    assert "=== MATCH ANALYSIS REPORT ===" in csv_str
    assert "=== PLAYER PERFORMANCE ===" in csv_str
    assert "#7" in csv_str
    assert "=== MATCH EVENTS LOG ===" in csv_str


def test_export_html_report(report_generator):
    mock_rep = MatchReport(
        match_id="test_1",
        title="Championship Final",
        sport="volleyball",
        status="active",
        started_at="2026-09-27T10:00:00",
        ended_at=None,
        duration_sec=3600.0,
        duration_formatted="01:00:00",
        fps=30.0,
        players_detected=12,
        active_players=12,
        total_distance_km=5.2,
        total_jumps=183,
        max_speed_mps=7.1,
        avg_speed_mps=3.4,
        sport_summary={},
        players=[{"player_id": 7, "jersey_number": "#7", "team": "Team A", "total_distance_m": 824.0, "max_speed_mps": 6.2, "avg_speed_mps": 3.1, "max_acceleration_mps2": 3.8, "jumps_count": 24, "highest_jump_cm": 51.0, "avg_jump_height_cm": 38.0, "court_coverage_pct": 89.0}],
        events=[{"timestamp": 754.0, "formatted_time": "12:34", "event_type": "spike", "player_id": 7, "details": "Attack spike", "confidence": 0.78}]
    )

    html = report_generator.export_html_report(mock_rep)
    assert "<!DOCTYPE html>" in html
    assert "Championship Final" in html
    assert "824.0 m" in html
    assert "Print / Export PDF" in html


# ── FASTAPI ENDPOINT TESTS ───────────────────────────────────────────────────

def test_api_reports_match_live(client):
    res = client.get("/api/reports/match/live")
    assert res.status_code == 200
    data = res.json()
    assert "match_id" in data
    assert "players" in data
    assert "timeline_markers" in data


def test_api_reports_player_live(client):
    res = client.get("/api/reports/player/live/7")
    assert res.status_code == 200
    data = res.json()
    assert data["player_id"] == 7
    assert "speed_over_time" in data
    assert "jump_timeline" in data
    assert "distance_over_time" in data


def test_api_reports_replay_timeline(client):
    res = client.get("/api/reports/replay/live/timeline")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_api_export_match_json(client):
    res = client.get("/api/reports/export/match/live/json")
    assert res.status_code == 200
    assert "application/json" in res.headers["content-type"]
    data = json.loads(res.text)
    assert "match_id" in data


def test_api_export_match_csv(client):
    res = client.get("/api/reports/export/match/live/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "=== MATCH ANALYSIS REPORT ===" in res.text


def test_api_export_match_html(client):
    res = client.get("/api/reports/export/match/live/html")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "<!DOCTYPE html>" in res.text


def test_api_export_player_csv(client):
    res = client.get("/api/reports/export/player/7/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "PERFORMANCE REPORT" in res.text
