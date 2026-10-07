"""Player tracking API — active players list, kinematics, pose landmarks, and trail data."""
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException

from backend.app.api.camera import get_pipeline

logger = logging.getLogger("sports_analyzer.api.players")
router = APIRouter(prefix="/api/players", tags=["players"])


@router.get("/active")
async def get_active_players() -> List[Dict[str, Any]]:
    """Returns all currently tracked active players with kinematics and pose from the vision pipeline."""
    pipeline = get_pipeline()
    if pipeline is None or not pipeline.is_running:
        return []

    telemetry = pipeline.get_latest_telemetry()
    return telemetry.get("players", [])


@router.get("/{player_id}/trail")
async def get_player_trail(player_id: int) -> Dict[str, Any]:
    """Returns the movement trail for a specific tracked player."""
    pipeline = get_pipeline()
    if pipeline is None or not pipeline.is_running:
        raise HTTPException(status_code=404, detail="Pipeline not running")

    telemetry = pipeline.get_latest_telemetry()
    players = telemetry.get("players", [])

    for p in players:
        if p.get("player_id") == player_id:
            return {
                "player_id": player_id,
                "trail": p.get("trail", []),
                "total_distance_px": p.get("total_distance_px", 0.0),
                "speed_px_per_frame": p.get("speed_px_per_frame", 0.0)
            }

    raise HTTPException(status_code=404, detail=f"Player {player_id} not found in active tracks")


@router.get("/{player_id}/kinematics")
async def get_player_kinematics(player_id: int) -> Dict[str, Any]:
    """Returns real-time kinematic profile (speed, acceleration, distance, jumps) for a specific player."""
    pipeline = get_pipeline()
    if pipeline is None or not pipeline.is_running:
        raise HTTPException(status_code=404, detail="Pipeline not running")

    snapshot = pipeline.kinematics_engine.get_player(player_id)
    if snapshot is not None:
        return snapshot.to_dict()

    # Fallback to telemetry dictionary
    telemetry = pipeline.get_latest_telemetry()
    for p in telemetry.get("players", []):
        if p.get("player_id") == player_id and "kinematics" in p:
            return p["kinematics"]

    raise HTTPException(status_code=404, detail=f"Player {player_id} kinematics not found")


@router.get("/{player_id}/pose")
async def get_player_pose(player_id: int) -> Dict[str, Any]:
    """Returns the latest 17 body landmarks and confidence scores for a specific player."""
    pipeline = get_pipeline()
    if pipeline is None or not pipeline.is_running:
        raise HTTPException(status_code=404, detail="Pipeline not running")

    telemetry = pipeline.get_latest_telemetry()
    for p in telemetry.get("players", []):
        if p.get("player_id") == player_id:
            pose_data = p.get("pose")
            if pose_data:
                return {
                    "player_id": player_id,
                    "keypoints": pose_data
                }

    raise HTTPException(status_code=404, detail=f"Player {player_id} pose not found")
