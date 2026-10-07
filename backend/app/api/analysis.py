"""Live analysis API — MJPEG streaming, WebSocket telemetry, status, and visualization settings."""
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.app.api.camera import get_pipeline

logger = logging.getLogger("sports_analyzer.api.analysis")
router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class AnalysisSettingsRequest(BaseModel):
    show_skeleton: Optional[bool] = None
    show_boxes: Optional[bool] = None
    show_trails: Optional[bool] = None


@router.get("/feed/mjpeg")
async def mjpeg_feed():
    """Returns a multipart MJPEG stream of the annotated video feed."""
    pipeline = get_pipeline()
    if pipeline is None or not pipeline.is_running:
        return {"error": "No active pipeline. Start the camera first via POST /api/camera/start"}

    return StreamingResponse(
        pipeline.mjpeg_stream_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.websocket("/ws/live")
async def websocket_live_telemetry(websocket: WebSocket):
    """WebSocket endpoint streaming real-time player tracking, pose, and kinematics telemetry."""
    await websocket.accept()
    logger.info("WebSocket client connected for live telemetry.")

    try:
        while True:
            pipeline = get_pipeline()
            if pipeline is not None and pipeline.is_running:
                telemetry = pipeline.get_latest_telemetry()
                if telemetry:
                    await websocket.send_json(telemetry)
            else:
                await websocket.send_json({
                    "type": "status",
                    "message": "Pipeline not running",
                    "players_count": 0,
                    "fps": 0.0
                })
            await asyncio.sleep(0.033)  # ~30 Hz update rate
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")


@router.get("/status")
async def analysis_status() -> Dict[str, Any]:
    """Returns current pipeline operational status and active display options."""
    pipeline = get_pipeline()
    if pipeline is None:
        return {
            "is_running": False,
            "is_paused": False,
            "fps": 0.0,
            "frame_index": 0,
            "players_count": 0,
            "sport": "none",
            "show_skeleton": True,
            "show_boxes": True,
            "show_trails": True
        }

    telemetry = pipeline.get_latest_telemetry()
    return {
        "is_running": pipeline.is_running,
        "is_paused": pipeline.is_paused,
        "fps": round(pipeline.current_fps, 1),
        "frame_index": pipeline.frame_index,
        "players_count": telemetry.get("players_count", 0),
        "sport": pipeline.sport,
        "frame_dimensions": {
            "width": pipeline.frame_width,
            "height": pipeline.frame_height
        },
        "show_skeleton": pipeline.show_skeleton,
        "show_boxes": pipeline.show_boxes,
        "show_trails": pipeline.show_trails
    }


@router.post("/settings")
async def update_analysis_settings(req: AnalysisSettingsRequest) -> Dict[str, Any]:
    """Updates overlay display options dynamically."""
    pipeline = get_pipeline()
    if pipeline is None:
        return {"status": "error", "message": "No pipeline running to apply settings."}

    pipeline.set_overlay_options(
        show_skeleton=req.show_skeleton,
        show_boxes=req.show_boxes,
        show_trails=req.show_trails
    )

    return {
        "status": "updated",
        "show_skeleton": pipeline.show_skeleton,
        "show_boxes": pipeline.show_boxes,
        "show_trails": pipeline.show_trails
    }


@router.get("/heatmap/player/{player_id}")
async def get_player_heatmap(player_id: int, mode: str = "court") -> Dict[str, Any]:
    """Generates a 2D top-down or perspective heatmap for a specific player."""
    pipeline = get_pipeline()
    if pipeline is None or not pipeline.is_running:
        return {"error": "No active pipeline running."}

    b64_img = pipeline.get_heatmap_base64(player_id=player_id, mode=mode)
    return {
        "player_id": player_id,
        "mode": mode,
        "sport": pipeline.sport,
        "heatmap_image_base64": b64_img
    }


@router.get("/heatmap/team")
async def get_team_heatmap(mode: str = "court") -> Dict[str, Any]:
    """Generates an aggregate 2D court coverage heatmap for the entire team."""
    pipeline = get_pipeline()
    if pipeline is None or not pipeline.is_running:
        return {"error": "No active pipeline running."}

    b64_img = pipeline.get_heatmap_base64(player_id=None, mode=mode)
    return {
        "team": "all_players",
        "mode": mode,
        "sport": pipeline.sport,
        "heatmap_image_base64": b64_img
    }


@router.get("/court/topdown")
async def get_topdown_tactical_view() -> Dict[str, Any]:
    """Returns the 2D vector top-down court map with live athlete positions."""
    pipeline = get_pipeline()
    if pipeline is None or not pipeline.is_running:
        return {"error": "No active pipeline running."}

    img = pipeline.get_topdown_tactical_image()
    b64 = pipeline.court_renderer.to_base64_png(img)
    return {
        "sport": pipeline.sport,
        "court_dimensions": pipeline.calibrator.get_court_dimensions(),
        "is_calibrated": pipeline.calibrator.is_calibrated,
        "topdown_image_base64": b64
    }


@router.get("/volleyball/events")
async def get_volleyball_events() -> Dict[str, Any]:
    """Returns detected volleyball action events (serves, spikes, blocks)."""
    pipeline = get_pipeline()
    if pipeline is None:
        return {"events": [], "count": 0, "message": "No active pipeline running."}

    events = pipeline.get_volleyball_events()
    return {
        "sport": "volleyball",
        "count": len(events),
        "events": events
    }


@router.get("/volleyball/violations")
async def get_volleyball_violations() -> Dict[str, Any]:
    """Returns all logged volleyball rule violations and fouls."""
    pipeline = get_pipeline()
    if pipeline is None:
        return {"violations": [], "count": 0, "message": "No active pipeline running."}

    violations = pipeline.get_volleyball_violations()
    return {
        "sport": "volleyball",
        "count": len(violations),
        "violations": violations
    }


@router.get("/volleyball/status")
async def get_volleyball_status() -> Dict[str, Any]:
    """Returns real-time rally status, serving team, and active fouls."""
    pipeline = get_pipeline()
    if pipeline is None or pipeline.volleyball_analyzer is None:
        return {
            "rally_state": "IDLE",
            "rally_duration_seconds": 0.0,
            "contacts_count": 0,
            "serving_team": None,
            "active_violations": []
        }

    va = pipeline.volleyball_analyzer
    return {
        "rally_state": va.rally_state,
        "rally_duration_seconds": va.rally_duration,
        "contacts_count": va.contacts_count,
        "serving_team": va.serving_team,
        "active_violations": va.active_violations
    }


@router.post("/volleyball/reset-rally")
async def reset_volleyball_rally() -> Dict[str, Any]:
    """Resets the current rally to IDLE."""
    pipeline = get_pipeline()
    if pipeline is not None:
        pipeline.reset_rally()
    return {"status": "success", "rally_state": "IDLE"}


# ---------------------------------------------------------------------------
# Kabaddi Specific Endpoints
# ---------------------------------------------------------------------------

@router.get("/kabaddi/events")
async def get_kabaddi_events() -> Dict[str, Any]:
    """Returns detected kabaddi action events (raids, tackles, bonus line touches)."""
    pipeline = get_pipeline()
    if pipeline is None:
        return {"events": [], "count": 0, "message": "No active pipeline running."}

    events = pipeline.get_kabaddi_events()
    return {
        "sport": "kabaddi",
        "count": len(events),
        "events": events
    }


@router.get("/kabaddi/violations")
async def get_kabaddi_violations() -> Dict[str, Any]:
    """Returns all logged kabaddi rule violations and fouls."""
    pipeline = get_pipeline()
    if pipeline is None:
        return {"violations": [], "count": 0, "message": "No active pipeline running."}

    violations = pipeline.get_kabaddi_violations()
    return {
        "sport": "kabaddi",
        "count": len(violations),
        "violations": violations
    }


@router.get("/kabaddi/status")
async def get_kabaddi_status() -> Dict[str, Any]:
    """Returns real-time kabaddi status, raid state, active raider, and Do-or-Die status."""
    pipeline = get_pipeline()
    if pipeline is None or pipeline.kabaddi_analyzer is None:
        return {
            "raid_state": "WAITING",
            "active_raider_id": None,
            "raiding_team": None,
            "raid_points": 0,
            "consecutive_empty_raids": {"Team A": 0, "Team B": 0},
            "do_or_die_active": False,
            "active_violations": []
        }

    ka = pipeline.kabaddi_analyzer
    return {
        "raid_state": ka.raid_state,
        "active_raider_id": ka.active_raider_id,
        "raiding_team": ka.raiding_team,
        "raid_points": ka.raid_points,
        "consecutive_empty_raids": dict(ka._consecutive_empty_raids),
        "do_or_die_active": ka._do_or_die_active,
        "active_violations": ka.get_violations()[-5:] if ka.get_violations() else []
    }


@router.post("/kabaddi/reset-raid")
async def reset_kabaddi_raid() -> Dict[str, Any]:
    """Resets the current raid to WAITING."""
    pipeline = get_pipeline()
    if pipeline is not None:
        pipeline.reset_raid()
    return {"status": "success", "raid_state": "WAITING"}


# ---------------------------------------------------------------------------
# Kho Kho Specific Endpoints
# ---------------------------------------------------------------------------

@router.get("/kho_kho/events")
async def get_kho_kho_events() -> Dict[str, Any]:
    """Returns detected kho kho action events (khos, runner dismissals)."""
    pipeline = get_pipeline()
    if pipeline is None:
        return {"events": [], "count": 0, "message": "No active pipeline running."}

    events = pipeline.get_kho_kho_events()
    return {
        "sport": "kho_kho",
        "count": len(events),
        "events": events
    }


@router.get("/kho_kho/violations")
async def get_kho_kho_violations() -> Dict[str, Any]:
    """Returns all logged kho kho rule violations and fouls."""
    pipeline = get_pipeline()
    if pipeline is None:
        return {"violations": [], "count": 0, "message": "No active pipeline running."}

    violations = pipeline.get_kho_kho_violations()
    return {
        "sport": "kho_kho",
        "count": len(violations),
        "violations": violations
    }


@router.get("/kho_kho/status")
async def get_kho_kho_status() -> Dict[str, Any]:
    """Returns real-time kho kho status, active chaser, and runners remaining."""
    pipeline = get_pipeline()
    if pipeline is None or pipeline.kho_kho_analyzer is None:
        return {
            "active_chaser_id": None,
            "chaser_committed_direction": None,
            "runners_remaining": 3,
            "runners_in_batch": 3,
            "sitting_chasers": {},
            "active_violations": []
        }

    kka = pipeline.kho_kho_analyzer
    return {
        "active_chaser_id": kka.active_chaser_id,
        "chaser_committed_direction": kka._chaser_committed_direction,
        "runners_remaining": kka.runners_remaining,
        "runners_in_batch": kka.runners_in_batch,
        "sitting_chasers": dict(kka._sitting_chasers),
        "active_violations": kka.get_violations()[-5:] if kka.get_violations() else []
    }


@router.post("/kho_kho/reset-turn")
async def reset_kho_kho_turn() -> Dict[str, Any]:
    """Resets the current kho kho chase turn."""
    pipeline = get_pipeline()
    if pipeline is not None:
        pipeline.reset_kho_kho_turn()
    return {"status": "success", "message": "Kho Kho turn reset"}


