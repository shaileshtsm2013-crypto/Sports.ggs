"""Hardware Acceleration & Optimization API Endpoints (Phase 9).
Provides hardware auto-detection, performance tuning profiles (low-power, balanced,
max-performance), benchmarking, and offline operation status.
"""
import os
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.hardware import hardware_manager, PREDEFINED_PROFILES, PerformanceProfile
from backend.app.api.camera import get_pipeline
from backend.app.core.config import settings

logger = logging.getLogger("sports_analyzer.api.optimization")
router = APIRouter(prefix="/api/optimization", tags=["optimization"])


class ProfileUpdateRequest(BaseModel):
    profile_name: str  # "low_power", "balanced", "max_performance", "custom"
    frame_skip: Optional[int] = None
    pose_cadence: Optional[int] = None
    input_size: Optional[int] = None
    target_fps: Optional[float] = None
    fp16: Optional[bool] = None
    auto_throttle: Optional[bool] = None


@router.get("/hardware")
async def get_hardware_specs() -> Dict[str, Any]:
    """Returns detected compute hardware, acceleration backends, and OS environment."""
    return hardware_manager.specs.to_dict()


@router.get("/profile")
async def get_performance_profile() -> Dict[str, Any]:
    """Returns currently active tuning profile and available predefined profiles."""
    pipeline = get_pipeline()
    active = pipeline.get_performance_profile() if pipeline else hardware_manager.active_profile
    return {
        "active_profile": active.to_dict(),
        "available_profiles": {k: v.to_dict() for k, v in PREDEFINED_PROFILES.items()}
    }


@router.post("/profile")
async def set_performance_profile(req: ProfileUpdateRequest) -> Dict[str, Any]:
    """Switches the active performance profile and updates running pipeline live."""
    overrides = {
        "frame_skip": req.frame_skip,
        "pose_cadence": req.pose_cadence,
        "input_size": req.input_size,
        "target_fps": req.target_fps,
        "fp16": req.fp16,
        "auto_throttle": req.auto_throttle
    }
    # Filter out None values
    overrides = {k: v for k, v in overrides.items() if v is not None}

    new_profile = hardware_manager.set_profile(req.profile_name, overrides=overrides)

    # If pipeline is running, update it dynamically
    pipeline = get_pipeline()
    if pipeline:
        pipeline.set_performance_profile(new_profile)

    return {
        "status": "updated",
        "profile": new_profile.to_dict()
    }


@router.get("/benchmark")
async def run_hardware_benchmark(frames: int = 10) -> Dict[str, Any]:
    """Executes a synthetic processing benchmark to measure latency and estimated FPS."""
    clamped_frames = max(3, min(30, frames))
    result = hardware_manager.run_benchmark(frames_count=clamped_frames)
    return result


@router.get("/offline-status")
async def get_offline_status() -> Dict[str, Any]:
    """Verifies that all AI models, rules, and vision engines are operational without internet."""
    yolo_model_path = os.path.join(settings.BASE_DIR, "yolov8n.pt")
    pose_model_path = os.path.join(settings.BASE_DIR, "yolov8n-pose.pt")
    rules_path = settings.RULES_DIR

    yolo_present = os.path.exists(yolo_model_path)
    pose_present = os.path.exists(pose_model_path)
    rules_present = os.path.exists(rules_path) and os.path.isdir(rules_path)

    all_offline_ready = yolo_present and pose_present and rules_present

    return {
        "offline_ready": all_offline_ready,
        "models": {
            "yolov8n_detector": {"path": yolo_model_path, "available": yolo_present},
            "yolov8n_pose": {"path": pose_model_path, "available": pose_present}
        },
        "knowledge_base": {
            "rules_directory": rules_path,
            "available": rules_present
        },
        "network_required": False,
        "privacy_guarantee": "Zero automatic cloud video uploads. All detections run locally on device."
    }
