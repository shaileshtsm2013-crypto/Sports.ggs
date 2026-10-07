"""Match management API — CRUD operations for match sessions."""
import logging
import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database.database import get_db
from backend.app.database.models import Match

logger = logging.getLogger("sports_analyzer.api.matches")
router = APIRouter(prefix="/api/matches", tags=["matches"])


class CreateMatchRequest(BaseModel):
    sport_type: str = "volleyball"
    title: str = "New Match Session"


@router.post("/")
async def create_match(req: CreateMatchRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Creates a new match session record."""
    match = Match(
        sport_type=req.sport_type,
        title=req.title,
        started_at=datetime.datetime.now(datetime.timezone.utc),
        status="active"
    )
    db.add(match)
    db.commit()
    db.refresh(match)

    logger.info(f"Match created: id={match.id}, sport={match.sport_type}")
    return {
        "id": match.id,
        "sport_type": match.sport_type,
        "title": match.title,
        "started_at": str(match.started_at),
        "status": match.status
    }


@router.get("/")
async def list_matches(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Returns all saved match sessions."""
    matches = db.query(Match).order_by(Match.started_at.desc()).all()
    return [
        {
            "id": m.id,
            "sport_type": m.sport_type,
            "title": m.title,
            "started_at": str(m.started_at),
            "ended_at": str(m.ended_at) if m.ended_at else None,
            "status": m.status,
            "total_players": m.total_players,
            "fps": m.fps
        }
        for m in matches
    ]


@router.get("/{match_id}")
async def get_match(match_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns details for a specific match."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    return {
        "id": match.id,
        "sport_type": match.sport_type,
        "title": match.title,
        "started_at": str(match.started_at),
        "ended_at": str(match.ended_at) if match.ended_at else None,
        "duration_sec": match.duration_sec,
        "status": match.status,
        "total_players": match.total_players,
        "fps": match.fps,
        "notes": match.notes
    }


@router.delete("/{match_id}")
async def delete_match(match_id: int, db: Session = Depends(get_db)) -> Dict[str, str]:
    """Deletes a match and all associated data."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    db.delete(match)
    db.commit()
    logger.info(f"Match deleted: id={match_id}")
    return {"status": "deleted", "match_id": str(match_id)}
