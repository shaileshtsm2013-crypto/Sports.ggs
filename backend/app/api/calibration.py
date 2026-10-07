"""Court Calibration API — perspective transformation and corner point configuration."""
import os
import logging
from typing import Dict, Any, List, Tuple
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.api.camera import get_pipeline
from backend.app.vision.calibration import CourtCalibrator, COURT_METRIC_DIMENSIONS

logger = logging.getLogger("sports_analyzer.api.calibration")
router = APIRouter(prefix="/api/calibration", tags=["calibration"])


class CalibrationCornersRequest(BaseModel):
    corners: List[Tuple[float, float]]  # [TL, TR, BR, BL]


def _get_calibration_filepath(sport: str) -> str:
    return os.path.join(settings.DATA_DIR, f"calibration_{sport.lower()}.json")


@router.get("/{sport}")
async def get_calibration_status(sport: str) -> Dict[str, Any]:
    """Returns current calibration status and corner points for a sport."""
    sport_key = sport.lower()
    if sport_key not in COURT_METRIC_DIMENSIONS:
        raise HTTPException(status_code=404, detail=f"Sport '{sport}' not supported.")

    pipeline = get_pipeline()
    if pipeline is not None and pipeline.sport.lower() == sport_key:
        return pipeline.calibrator.to_dict()

    # Fallback to saved disk calibration
    calibrator = CourtCalibrator(sport=sport_key)
    calibrator.load_calibration(_get_calibration_filepath(sport_key))
    return calibrator.to_dict()


@router.post("/{sport}")
async def set_calibration_corners(sport: str, req: CalibrationCornersRequest) -> Dict[str, Any]:
    """Sets 4 manual image corner points [TL, TR, BR, BL] and computes homography."""
    sport_key = sport.lower()
    if len(req.corners) != 4:
        raise HTTPException(status_code=400, detail="Exactly 4 corner points [TL, TR, BR, BL] required.")

    pipeline = get_pipeline()
    calibrator = pipeline.calibrator if pipeline is not None and pipeline.sport.lower() == sport_key else CourtCalibrator(sport=sport_key)

    success = calibrator.set_calibration_corners(req.corners)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to compute perspective homography matrix from given corners.")

    # Save to disk
    filepath = _get_calibration_filepath(sport_key)
    calibrator.save_calibration(filepath)

    return {
        "status": "success",
        "sport": sport_key,
        "is_calibrated": True,
        "image_corners": req.corners,
        "message": f"Court calibration saved for {sport_key}."
    }


@router.post("/{sport}/auto")
async def auto_detect_court(sport: str) -> Dict[str, Any]:
    """Runs automated edge and line detection on the latest frame to propose court corners."""
    sport_key = sport.lower()
    pipeline = get_pipeline()
    if pipeline is None or pipeline.latest_raw_frame is None:
        raise HTTPException(status_code=400, detail="No active camera feed to detect court lines from.")

    calibrator = pipeline.calibrator
    proposed = calibrator.auto_detect_corners(pipeline.latest_raw_frame)
    if not proposed:
        raise HTTPException(status_code=500, detail="Could not reliably detect court lines.")

    return {
        "status": "detected",
        "sport": sport_key,
        "proposed_corners": proposed
    }
