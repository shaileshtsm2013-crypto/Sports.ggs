"""Sports Analytics & Reports API Endpoints.
Provides endpoints for match dashboards, individual player performance reports,
time-series chart datasets, video replay markers, and exports (JSON, CSV, HTML).
"""
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.app.api.camera import get_pipeline
from backend.app.database.database import get_db
from backend.app.database.models import Match, Player, SportsEvent
from backend.app.analytics.reports import ReportGenerator, MatchReport, PlayerReport

logger = logging.getLogger("sports_analyzer.api.reports")
router = APIRouter(prefix="/api/reports", tags=["reports"])
report_generator = ReportGenerator()


@router.get("/match/live")
async def get_live_match_report() -> Dict[str, Any]:
    """Returns real-time match report aggregating active players, kinematics, and events."""
    pipeline = get_pipeline()
    report = report_generator.generate_live_match_report(pipeline)
    return report.to_dict()


@router.get("/match/{match_id}")
async def get_match_report(match_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns match report for a saved match session or live match."""
    if match_id.lower() in ["live", "current", "live_session"]:
        pipeline = get_pipeline()
        report = report_generator.generate_live_match_report(pipeline)
        return report.to_dict()

    # Query match from database
    try:
        m_id = int(match_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid match_id format")

    match = db.query(Match).filter(Match.id == m_id).first()
    if not match:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

    # If active live session matches this ID
    pipeline = get_pipeline()
    if pipeline and pipeline.is_running:
        report = report_generator.generate_live_match_report(pipeline)
        rep_dict = report.to_dict()
        rep_dict["match_id"] = str(match.id)
        rep_dict["title"] = match.title
        return rep_dict

    # Return summary from DB record
    players_data = []
    total_dist_km = 0.0
    total_jumps = 0
    max_speed = 0.0

    for p in match.players:
        players_data.append({
            "player_id": p.tracker_id,
            "jersey_number": p.jersey_number or f"#{p.tracker_id}",
            "team": p.team or "Team A",
            "role": "player",
            "total_distance_m": round(p.total_distance_m or 0.0, 2),
            "max_speed_mps": round(p.max_speed_mps or 0.0, 2),
            "avg_speed_mps": round(p.avg_speed_mps or 0.0, 2),
            "max_acceleration_mps2": round(p.max_accel_mps2 or 0.0, 2),
            "jumps_count": p.jump_count or 0,
            "highest_jump_cm": round(p.max_jump_height_cm or 0.0, 1),
            "avg_jump_height_cm": round(p.avg_jump_height_cm or 0.0, 1),
            "court_coverage_pct": round(p.court_coverage_pct or 0.0, 1),
            "movement_state": "standing",
            "direction_changes": 0
        })
        total_dist_km += (p.total_distance_m or 0.0) / 1000.0
        total_jumps += (p.jump_count or 0)
        if (p.max_speed_mps or 0.0) > max_speed:
            max_speed = p.max_speed_mps

    events_data = [
        {
            "timestamp": ev.timestamp,
            "formatted_time": f"{int(ev.timestamp)//60:02d}:{int(ev.timestamp)%60:02d}",
            "event_type": ev.event_type,
            "player_id": ev.player_id,
            "details": str(ev.metadata_json or ""),
            "confidence": ev.confidence
        }
        for ev in match.events
    ]

    return {
        "match_id": str(match.id),
        "title": match.title,
        "sport": match.sport_type,
        "status": match.status,
        "started_at": str(match.started_at),
        "ended_at": str(match.ended_at) if match.ended_at else None,
        "duration_sec": match.duration_sec,
        "duration_formatted": f"{int(match.duration_sec)//3600:02d}:{(int(match.duration_sec)%3600)//60:02d}:{int(match.duration_sec)%60:02d}",
        "fps": match.fps,
        "players_detected": len(players_data),
        "active_players": len(players_data),
        "total_distance_km": round(total_dist_km, 2),
        "total_jumps": total_jumps,
        "max_speed_mps": round(max_speed, 2),
        "avg_speed_mps": 0.0,
        "sport_summary": {},
        "players": players_data,
        "events": events_data,
        "timeline_markers": [
            {
                "timestamp": ev["timestamp"],
                "formatted_time": ev["formatted_time"],
                "event_type": ev["event_type"],
                "player_id": ev["player_id"],
                "description": ev["details"] or ev["event_type"],
                "confidence": ev["confidence"]
            }
            for ev in events_data
        ]
    }


@router.get("/player/live/{player_id}")
async def get_live_player_report(player_id: int) -> Dict[str, Any]:
    """Returns detailed player report with speed, distance, jump, and acceleration time-series."""
    pipeline = get_pipeline()
    report = report_generator.generate_live_player_report(pipeline, player_id)
    return report.to_dict()


@router.get("/replay/{match_id}/timeline")
async def get_replay_timeline(match_id: str, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Returns timestamped video replay timeline markers (jumps, spikes, tackles, faults, rallies)."""
    match_data = await get_match_report(match_id, db=db)
    return match_data.get("timeline_markers", [])


# ── EXPORT ENDPOINTS ──────────────────────────────────────────────────────────

@router.get("/export/match/{match_id}/json")
async def export_match_json(match_id: str, db: Session = Depends(get_db)):
    """Exports match analysis report as a downloadable JSON file."""
    data = await get_match_report(match_id, db=db)
    filename = f"match_report_{match_id}.json"
    json_str = json.dumps(data, indent=2)
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/match/{match_id}/csv")
async def export_match_csv(match_id: str, db: Session = Depends(get_db)):
    """Exports match player statistics and events log as CSV."""
    pipeline = get_pipeline()
    report = report_generator.generate_live_match_report(pipeline)
    csv_str = report_generator.export_match_csv(report)
    filename = f"match_report_{match_id}.csv"
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/match/{match_id}/html", response_class=HTMLResponse)
async def export_match_html(match_id: str, db: Session = Depends(get_db)):
    """Renders modern printable HTML match report suitable for browser printing / PDF saving."""
    pipeline = get_pipeline()
    report = report_generator.generate_live_match_report(pipeline)
    return HTMLResponse(content=report_generator.export_html_report(report))


@router.get("/export/player/{player_id}/csv")
async def export_player_csv(player_id: int):
    """Exports individual player time-series performance data as CSV."""
    pipeline = get_pipeline()
    report = report_generator.generate_live_player_report(pipeline, player_id)
    csv_str = report_generator.export_player_csv(report)
    filename = f"player_{player_id}_report.csv"
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
