"""Camera management API — source discovery, feed start/stop/pause/resume."""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import cv2

from backend.app.vision.pipeline import VisionPipeline

logger = logging.getLogger("sports_analyzer.api.camera")
router = APIRouter(prefix="/api/camera", tags=["camera"])

# Module-level pipeline singleton
_pipeline: Optional[VisionPipeline] = None


def get_pipeline() -> Optional[VisionPipeline]:
    """Returns the current global VisionPipeline instance."""
    return _pipeline


class StartRequest(BaseModel):
    source: str = "synthetic"
    sport: str = "volleyball"


@router.get("/sources")
async def list_camera_sources() -> List[Dict[str, Any]]:
    """Discovers available camera sources by probing device indices."""
    sources: List[Dict[str, Any]] = []

    # Always include synthetic demo
    sources.append({"id": "synthetic", "name": "Demo Mode (Synthetic Court)", "available": True})

    # Probe USB/webcam indices 0..4
    for idx in range(5):
        try:
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap is not None and cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                sources.append({
                    "id": str(idx),
                    "name": f"Camera {idx} ({w}x{h})",
                    "available": True
                })
                cap.release()
        except Exception:
            pass

    return sources


@router.post("/start")
async def start_camera(req: StartRequest) -> Dict[str, Any]:
    """Starts the vision pipeline with the given source and sport."""
    global _pipeline

    if _pipeline is not None and _pipeline.is_running:
        _pipeline.stop()

    _pipeline = VisionPipeline(
        source=req.source,
        sport=req.sport,
        confidence_threshold=0.40
    )
    _pipeline.start()

    logger.info(f"Pipeline started: source={req.source}, sport={req.sport}")
    return {
        "status": "started",
        "source": req.source,
        "sport": req.sport,
        "message": f"Vision pipeline running on {req.source} for {req.sport}"
    }


@router.post("/stop")
async def stop_camera() -> Dict[str, str]:
    """Stops the current vision pipeline."""
    global _pipeline
    if _pipeline is not None:
        _pipeline.stop()
        _pipeline = None
        return {"status": "stopped", "message": "Pipeline stopped."}
    return {"status": "not_running", "message": "No pipeline was active."}


@router.post("/pause")
async def pause_camera() -> Dict[str, str]:
    if _pipeline is not None and _pipeline.is_running:
        _pipeline.pause()
        return {"status": "paused"}
    return {"status": "error", "message": "No active pipeline to pause."}


@router.post("/resume")
async def resume_camera() -> Dict[str, str]:
    if _pipeline is not None:
        _pipeline.resume()
        return {"status": "resumed"}
    return {"status": "error", "message": "No active pipeline to resume."}
