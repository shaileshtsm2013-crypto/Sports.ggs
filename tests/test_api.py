"""API integration tests using FastAPI TestClient."""
import time
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.database import init_db

# Initialize database tables for testing
init_db()
client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns project metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "volleyball" in data["supported_sports"]


def test_health_endpoint():
    """Test healthcheck endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_camera_sources():
    """Test camera sources endpoint returns synthetic demo."""
    response = client.get("/api/camera/sources")
    assert response.status_code == 200
    sources = response.json()
    assert any(s["id"] == "synthetic" for s in sources)


def test_chat_message():
    """Test offline rules chatbot response."""
    payload = {
        "messages": [
            {"role": "user", "content": "How many points to win a set?"}
        ],
        "sport": "volleyball"
    }
    response = client.post("/api/chat/message", json=payload)
    assert response.status_code == 200
    res_json = response.json()
    assert "response" in res_json
    assert len(res_json["response"]) > 0


def test_create_and_list_matches():
    """Test match session creation and retrieval."""
    match_payload = {
        "sport_type": "kabaddi",
        "title": "Championship Raid Session"
    }
    create_res = client.post("/api/matches/", json=match_payload)
    assert create_res.status_code == 200
    match_data = create_res.json()
    assert match_data["sport_type"] == "kabaddi"
    match_id = match_data["id"]

    # List matches
    list_res = client.get("/api/matches/")
    assert list_res.status_code == 200
    matches = list_res.json()
    assert any(m["id"] == match_id for m in matches)


def test_analysis_settings_and_pipeline():
    """Test updating visualization settings and checking pipeline status."""
    # Start pipeline with synthetic source
    start_res = client.post("/api/camera/start", json={"source": "synthetic", "sport": "volleyball"})
    assert start_res.status_code == 200

    time.sleep(0.5)

    # Test settings update
    settings_res = client.post("/api/analysis/settings", json={
        "show_skeleton": True,
        "show_boxes": True,
        "show_trails": False
    })
    assert settings_res.status_code == 200
    s_data = settings_res.json()
    assert s_data["show_skeleton"] is True
    assert s_data["show_trails"] is False

    # Check status endpoint
    status_res = client.get("/api/analysis/status")
    assert status_res.status_code == 200
    assert status_res.json()["is_running"] is True

    # Stop pipeline
    stop_res = client.post("/api/camera/stop")
    assert stop_res.status_code == 200


def test_calibration_and_heatmap_endpoints():
    """Test court calibration and tactical heatmap endpoints."""
    # Start pipeline
    start_res = client.post("/api/camera/start", json={"source": "synthetic", "sport": "volleyball"})
    assert start_res.status_code == 200

    time.sleep(0.5)

    # 1. Test set calibration
    calib_payload = {
        "corners": [
            [100.0, 100.0],
            [1100.0, 100.0],
            [1100.0, 600.0],
            [100.0, 600.0]
        ]
    }
    set_calib_res = client.post("/api/calibration/volleyball", json=calib_payload)
    assert set_calib_res.status_code == 200
    assert set_calib_res.json()["is_calibrated"] is True

    # 2. Test get calibration status
    get_calib_res = client.get("/api/calibration/volleyball")
    assert get_calib_res.status_code == 200
    assert get_calib_res.json()["is_calibrated"] is True

    # 3. Test top-down tactical court view
    topdown_res = client.get("/api/analysis/court/topdown")
    assert topdown_res.status_code == 200
    assert "topdown_image_base64" in topdown_res.json()
    assert topdown_res.json()["topdown_image_base64"].startswith("data:image/png;base64,")

    # 4. Test team heatmap
    heatmap_res = client.get("/api/analysis/heatmap/team?mode=court")
    assert heatmap_res.status_code == 200
    assert "heatmap_image_base64" in heatmap_res.json()

    # Stop pipeline
    client.post("/api/camera/stop")
