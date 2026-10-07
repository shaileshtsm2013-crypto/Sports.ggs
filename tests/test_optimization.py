"""Unit and API integration tests for Hardware Acceleration, Tuning Profiles & Offline Operation (Phase 9)."""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.hardware import (
    hardware_manager,
    HardwareManager,
    PerformanceProfile,
    PREDEFINED_PROFILES
)
from backend.app.vision.pipeline import VisionPipeline


@pytest.fixture
def client():
    return TestClient(app)


# ── HARDWARE MANAGER UNIT TESTS ───────────────────────────────────────────────

def test_hardware_detection_specs():
    specs = hardware_manager.specs
    assert specs.platform in ["Windows", "Linux", "Darwin"]
    assert specs.cpu_count >= 1
    assert specs.primary_device in ["cuda", "directml", "cpu"]
    assert isinstance(specs.to_dict(), dict)


def test_predefined_profiles_integrity():
    assert "low_power" in PREDEFINED_PROFILES
    assert "balanced" in PREDEFINED_PROFILES
    assert "max_performance" in PREDEFINED_PROFILES

    low = PREDEFINED_PROFILES["low_power"]
    assert low.frame_skip >= 1
    assert low.pose_cadence >= 2
    assert low.input_size <= 480

    high = PREDEFINED_PROFILES["max_performance"]
    assert high.frame_skip == 0
    assert high.pose_cadence == 1


def test_profile_switch_and_overrides():
    mgr = HardwareManager()
    
    # Switch to low_power
    p1 = mgr.set_profile("low_power")
    assert p1.name == "low_power"
    assert p1.frame_skip == 2

    # Switch with custom overrides
    p2 = mgr.set_profile("custom", overrides={"frame_skip": 4, "target_fps": 15.0})
    assert p2.name == "custom"
    assert p2.frame_skip == 4
    assert p2.target_fps == 15.0


def test_hardware_benchmark_execution():
    mgr = HardwareManager()
    res = mgr.run_benchmark(frames_count=5)
    assert "avg_latency_ms" in res
    assert "estimated_fps" in res
    assert res["estimated_fps"] > 0
    assert res["frames_tested"] == 5


# ── VISION PIPELINE INTEGRATION TESTS ─────────────────────────────────────────

def test_pipeline_profile_switch():
    pipeline = VisionPipeline(source="synthetic", sport="volleyball", enable_pose=False)
    initial_profile = pipeline.get_performance_profile()
    assert initial_profile is not None

    custom_prof = PerformanceProfile(
        name="battery_saver",
        frame_skip=3,
        pose_cadence=4,
        input_size=320,
        target_fps=15.0,
        fp16=False,
        auto_throttle=True
    )
    pipeline.set_performance_profile(custom_prof)
    updated = pipeline.get_performance_profile()
    assert updated.name == "battery_saver"
    assert updated.frame_skip == 3


# ── FASTAPI OPTIMIZATION ENDPOINT TESTS ───────────────────────────────────────

def test_api_get_hardware_specs(client):
    res = client.get("/api/optimization/hardware")
    assert res.status_code == 200
    data = res.json()
    assert "primary_device" in data
    assert "cpu_count" in data


def test_api_get_and_set_profile(client):
    res = client.get("/api/optimization/profile")
    assert res.status_code == 200
    data = res.json()
    assert "active_profile" in data
    assert "available_profiles" in data

    # Update profile
    post_res = client.post("/api/optimization/profile", json={
        "profile_name": "low_power",
        "frame_skip": 2
    })
    assert post_res.status_code == 200
    p_data = post_res.json()
    assert p_data["profile"]["name"] == "low_power"
    assert p_data["profile"]["frame_skip"] == 2


def test_api_run_benchmark(client):
    res = client.get("/api/optimization/benchmark?frames=4")
    assert res.status_code == 200
    data = res.json()
    assert "estimated_fps" in data
    assert data["frames_tested"] == 4


def test_api_offline_status(client):
    res = client.get("/api/optimization/offline-status")
    assert res.status_code == 200
    data = res.json()
    assert "offline_ready" in data
    assert "network_required" in data
    assert data["network_required"] is False
    assert "privacy_guarantee" in data
