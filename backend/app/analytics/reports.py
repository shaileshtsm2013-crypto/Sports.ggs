"""Sports Analytics & Match Reporting Engine.
Generates comprehensive match reports, individual player performance breakdowns,
time-series charts data, video replay timeline markers, and export formats (JSON, CSV, HTML).
"""
import io
import csv
import json
import logging
import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("sports_analyzer.analytics.reports")


def format_duration(seconds: float) -> str:
    """Formats duration in seconds to HH:MM:SS."""
    sec = int(max(0.0, seconds))
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_timestamp_mm_ss(seconds: float) -> str:
    """Formats a timestamp in seconds to MM:SS."""
    sec = int(max(0.0, seconds))
    m = sec // 60
    s = sec % 60
    return f"{m:02d}:{s:02d}"


@dataclass
class PlayerReport:
    """Detailed performance and biomechanical report for an individual player."""
    player_id: int
    jersey_number: str
    team: str
    sport: str
    total_distance_m: float
    max_speed_mps: float
    avg_speed_mps: float
    max_acceleration_mps2: float
    jumps_count: int
    highest_jump_cm: float
    avg_jump_height_cm: float
    court_coverage_pct: float
    direction_changes: int
    movement_state: str
    # Time-series datasets for charts
    speed_over_time: List[Dict[str, Any]] = field(default_factory=list)
    acceleration_over_time: List[Dict[str, Any]] = field(default_factory=list)
    distance_over_time: List[Dict[str, Any]] = field(default_factory=list)
    jump_timeline: List[Dict[str, Any]] = field(default_factory=list)
    event_timeline: List[Dict[str, Any]] = field(default_factory=list)
    movement_map: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MatchReport:
    """Comprehensive match analysis and summary report."""
    match_id: str
    title: str
    sport: str
    status: str
    started_at: str
    ended_at: Optional[str]
    duration_sec: float
    duration_formatted: str
    fps: float
    players_detected: int
    active_players: int
    total_distance_km: float
    total_jumps: int
    max_speed_mps: float
    avg_speed_mps: float
    sport_summary: Dict[str, Any]
    players: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    timeline_markers: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReportGenerator:
    """
    Builds structured match & player reports from active VisionPipeline
    or persisted database records.
    """

    def generate_live_match_report(self, pipeline: Any) -> MatchReport:
        """Generates a complete match analysis report from the running pipeline."""
        if pipeline is None:
            return self._empty_match_report()

        telemetry = pipeline.get_latest_telemetry() or {}
        elapsed = telemetry.get("elapsed_time", 0.0)
        fps = telemetry.get("fps", 0.0)
        sport = getattr(pipeline, "sport", "volleyball")

        # Players data from kinematics engine
        players_summary: List[Dict[str, Any]] = []
        total_dist_m = 0.0
        total_jumps = 0
        overall_max_speed = 0.0
        speed_sum = 0.0
        active_count = 0

        kinematics = pipeline.kinematics_engine
        raw_players = telemetry.get("players", [])

        # Map tracked player IDs
        team_map = {}
        for p in raw_players:
            pid = p.get("player_id", 0)
            team_map[pid] = {
                "team": p.get("team", "Team A"),
                "jersey": p.get("jersey_number") or f"#{pid}",
                "role": p.get("role", "player")
            }

        # Query all players in kinematics engine
        for pid, player_kin in kinematics.players.items():
            snap = player_kin.get_snapshot()
            info = team_map.get(pid, {"team": "Team A", "jersey": f"#{pid}", "role": "player"})
            
            p_dict = {
                "player_id": pid,
                "jersey_number": info["jersey"],
                "team": info["team"],
                "role": info["role"],
                "total_distance_m": round(snap.total_distance_m, 2),
                "max_speed_mps": round(snap.max_speed_mps, 2),
                "avg_speed_mps": round(snap.avg_speed_mps, 2),
                "max_acceleration_mps2": round(snap.max_acceleration_mps2, 2),
                "jumps_count": snap.jumps_count,
                "highest_jump_cm": round(snap.highest_jump_cm, 1),
                "avg_jump_height_cm": round(snap.avg_jump_height_cm, 1),
                "court_coverage_pct": round(snap.court_coverage_pct, 1),
                "movement_state": snap.movement_state,
                "direction_changes": snap.direction_changes
            }
            players_summary.append(p_dict)

            total_dist_m += snap.total_distance_m
            total_jumps += snap.jumps_count
            if snap.max_speed_mps > overall_max_speed:
                overall_max_speed = snap.max_speed_mps
            speed_sum += snap.avg_speed_mps
            active_count += 1

        overall_avg_speed = round(speed_sum / max(1, active_count), 2)
        total_dist_km = round(total_dist_m / 1000.0, 2)

        # Sport-specific metrics
        sport_summary: Dict[str, Any] = {}
        events_list: List[Dict[str, Any]] = []

        if sport == "volleyball" and pipeline.volleyball_analyzer:
            vb = pipeline.volleyball_analyzer
            recent_list = list(vb.recent_events) if hasattr(vb, "recent_events") else []
            spikes = sum(1 for e in recent_list if str(e.get("type", e.get("event_type", ""))).upper() == "SPIKE")
            blocks = sum(1 for e in recent_list if str(e.get("type", e.get("event_type", ""))).upper() == "BLOCK")
            sport_summary = {
                "rally_state": getattr(vb.rally_state, "value", str(vb.rally_state)),
                "total_rallies": getattr(vb, "total_rallies", 1),
                "total_spikes": getattr(vb, "spike_count", spikes),
                "total_blocks": getattr(vb, "block_count", blocks),
                "total_violations": len(vb.all_violations)
            }
            # Collect events
            for ev in recent_list:
                ev_type = ev.get("type") or ev.get("event_type") or "event"
                events_list.append({
                    "timestamp": round(ev.get("timestamp", 0.0), 2),
                    "formatted_time": format_timestamp_mm_ss(ev.get("timestamp", 0.0)),
                    "event_type": ev_type,
                    "player_id": ev.get("player_id"),
                    "details": ev.get("details", ev.get("description", "")),
                    "confidence": ev.get("confidence", 0.85)
                })

            for viol in vb.all_violations:
                events_list.append({
                    "timestamp": round(viol.get("timestamp", 0.0), 2),
                    "formatted_time": format_timestamp_mm_ss(viol.get("timestamp", 0.0)),
                    "event_type": "violation",
                    "player_id": viol.get("player_id"),
                    "details": viol.get("type", "fault"),
                    "confidence": viol.get("confidence", 0.9)
                })

        elif sport == "kabaddi" and pipeline.kabaddi_analyzer:
            kb = pipeline.kabaddi_analyzer
            sport_summary = {
                "raid_state": getattr(kb.raid_state, "value", str(kb.raid_state)),
                "team_a_score": kb.team_a_score,
                "team_b_score": kb.team_b_score,
                "active_raider_id": kb.active_raider_id,
                "total_raids": kb.total_raids,
                "total_tackles": kb.total_tackles,
                "super_tackles": kb.super_tackles,
                "all_outs": kb.all_outs_team_a + kb.all_outs_team_b
            }

            for ev in kb.get_events():
                events_list.append({
                    "timestamp": round(ev.get("timestamp", 0.0), 2),
                    "formatted_time": format_timestamp_mm_ss(ev.get("timestamp", 0.0)),
                    "event_type": ev.get("type", "raid_event"),
                    "player_id": ev.get("raider_id") or ev.get("defender_id"),
                    "details": ev.get("details", ""),
                    "confidence": ev.get("confidence", 0.88)
                })

        elif sport == "kho_kho" and pipeline.kho_kho_analyzer:
            kk = pipeline.kho_kho_analyzer
            sport_summary = {
                "active_chasers": kk.active_chasers,
                "runners_out": kk.runners_out,
                "total_khos": kk.total_khos,
                "direction_faults": kk.direction_faults,
                "central_lane_faults": kk.central_lane_faults
            }
            for ev in kk.get_events():
                events_list.append({
                    "timestamp": round(ev.get("timestamp", 0.0), 2),
                    "formatted_time": format_timestamp_mm_ss(ev.get("timestamp", 0.0)),
                    "event_type": ev.get("type", "kho_event"),
                    "player_id": ev.get("chaser_id") or ev.get("runner_id"),
                    "details": ev.get("details", ""),
                    "confidence": ev.get("confidence", 0.85)
                })

        # Sort events chronologically
        events_list.sort(key=lambda x: x["timestamp"])

        # Generate timeline markers for video replay
        timeline_markers = self._build_timeline_markers(events_list, kinematics)

        return MatchReport(
            match_id="live_session",
            title=f"Live {sport.replace('_', ' ').title()} Match Session",
            sport=sport,
            status="active" if pipeline.is_running else "paused",
            started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            ended_at=None,
            duration_sec=round(elapsed, 2),
            duration_formatted=format_duration(elapsed),
            fps=round(fps, 1),
            players_detected=len(players_summary),
            active_players=active_count,
            total_distance_km=total_dist_km,
            total_jumps=total_jumps,
            max_speed_mps=round(overall_max_speed, 2),
            avg_speed_mps=overall_avg_speed,
            sport_summary=sport_summary,
            players=players_summary,
            events=events_list,
            timeline_markers=timeline_markers
        )

    def generate_live_player_report(self, pipeline: Any, player_id: int) -> PlayerReport:
        """Generates detailed individual player report with charts datasets."""
        sport = getattr(pipeline, "sport", "volleyball") if pipeline else "volleyball"
        kin = pipeline.kinematics_engine.players.get(player_id) if pipeline and pipeline.kinematics_engine else None

        if kin is None:
            return PlayerReport(
                player_id=player_id,
                jersey_number=f"#{player_id}",
                team="Team A",
                sport=sport,
                total_distance_m=0.0,
                max_speed_mps=0.0,
                avg_speed_mps=0.0,
                max_acceleration_mps2=0.0,
                jumps_count=0,
                highest_jump_cm=0.0,
                avg_jump_height_cm=0.0,
                court_coverage_pct=0.0,
                direction_changes=0,
                movement_state="standing"
            )

        snap = kin.get_snapshot()
        time_series = kin.time_series

        speed_chart = [{"timestamp": pt["timestamp"], "speed_mps": pt["speed_mps"]} for pt in time_series]
        accel_chart = [{"timestamp": pt["timestamp"], "acceleration_mps2": pt["acceleration_mps2"]} for pt in time_series]
        dist_chart = [{"timestamp": pt["timestamp"], "distance_m": pt["distance_m"]} for pt in time_series]
        movement_map = [
            {"court_x_m": pt["court_x_m"], "court_y_m": pt["court_y_m"], "timestamp": pt["timestamp"]}
            for pt in time_series
        ]

        jump_timeline = [
            {
                "timestamp": round(j.get("takeoff_time") or j.get("timestamp", 0.0), 2),
                "formatted_time": format_timestamp_mm_ss(j.get("takeoff_time") or j.get("timestamp", 0.0)),
                "height_cm": round(j.get("estimated_height_cm", 0.0), 1),
                "type": j.get("jump_type", "jump"),
                "confidence": j.get("confidence", 0.8)
            }
            for j in kin.jumps_detected
        ]

        # Filter events for this player
        events_timeline: List[Dict[str, Any]] = []
        if pipeline:
            match_rep = self.generate_live_match_report(pipeline)
            events_timeline = [ev for ev in match_rep.events if ev.get("player_id") == player_id]

        return PlayerReport(
            player_id=player_id,
            jersey_number=f"#{player_id}",
            team="Team A",
            sport=sport,
            total_distance_m=round(snap.total_distance_m, 2),
            max_speed_mps=round(snap.max_speed_mps, 2),
            avg_speed_mps=round(snap.avg_speed_mps, 2),
            max_acceleration_mps2=round(snap.max_acceleration_mps2, 2),
            jumps_count=snap.jumps_count,
            highest_jump_cm=round(snap.highest_jump_cm, 1),
            avg_jump_height_cm=round(snap.avg_jump_height_cm, 1),
            court_coverage_pct=round(snap.court_coverage_pct, 1),
            direction_changes=snap.direction_changes,
            movement_state=snap.movement_state,
            speed_over_time=speed_chart,
            acceleration_over_time=accel_chart,
            distance_over_time=dist_chart,
            jump_timeline=jump_timeline,
            event_timeline=events_timeline,
            movement_map=movement_map
        )

    def _build_timeline_markers(self, events: List[Dict[str, Any]], kinematics: Any) -> List[Dict[str, Any]]:
        """Constructs replay timeline markers for jumps, spikes, tackles, faults, etc."""
        markers: List[Dict[str, Any]] = []

        # Events from sport analyzers
        for ev in events:
            markers.append({
                "timestamp": ev["timestamp"],
                "formatted_time": ev["formatted_time"],
                "event_type": ev["event_type"],
                "player_id": ev.get("player_id"),
                "description": ev.get("details", ev["event_type"]),
                "confidence": ev.get("confidence", 0.85)
            })

        # Add significant jumps from players
        if kinematics:
            for pid, pkin in kinematics.players.items():
                for jmp in pkin.jumps_detected:
                    t = round(jmp.get("takeoff_time") or jmp.get("timestamp", 0.0), 2)
                    h = round(jmp.get("estimated_height_cm", 0.0), 1)
                    markers.append({
                        "timestamp": t,
                        "formatted_time": format_timestamp_mm_ss(t),
                        "event_type": "jump",
                        "player_id": pid,
                        "description": f"Player #{pid} Jump: {h}cm",
                        "confidence": jmp.get("confidence", 0.8)
                    })

        # Deduplicate and sort chronologically
        markers.sort(key=lambda m: m["timestamp"])
        return markers

    def _empty_match_report(self) -> MatchReport:
        return MatchReport(
            match_id="none",
            title="No Active Match",
            sport="volleyball",
            status="idle",
            started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            ended_at=None,
            duration_sec=0.0,
            duration_formatted="00:00:00",
            fps=0.0,
            players_detected=0,
            active_players=0,
            total_distance_km=0.0,
            total_jumps=0,
            max_speed_mps=0.0,
            avg_speed_mps=0.0,
            sport_summary={}
        )

    # ── EXPORT FORMATS ────────────────────────────────────────────────────────

    def export_match_json(self, report: MatchReport) -> str:
        """Serializes the complete match report to formatted JSON."""
        return json.dumps(report.to_dict(), indent=2)

    def export_match_csv(self, report: MatchReport) -> str:
        """Exports player summary statistics and events log to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Match Header
        writer.writerow(["=== MATCH ANALYSIS REPORT ==="])
        writer.writerow(["Title", report.title])
        writer.writerow(["Sport", report.sport])
        writer.writerow(["Duration", report.duration_formatted])
        writer.writerow(["Total Distance (km)", report.total_distance_km])
        writer.writerow(["Total Jumps", report.total_jumps])
        writer.writerow(["Max Recorded Speed (m/s)", report.max_speed_mps])
        writer.writerow([])

        # Player Performance Table
        writer.writerow(["=== PLAYER PERFORMANCE ==="])
        writer.writerow([
            "Player ID", "Jersey", "Team", "Role", "Distance (m)", "Max Speed (m/s)",
            "Avg Speed (m/s)", "Max Accel (m/s2)", "Jumps", "Max Jump (cm)",
            "Avg Jump (cm)", "Court Coverage (%)", "Direction Changes"
        ])
        for p in report.players:
            writer.writerow([
                p.get("player_id"), p.get("jersey_number"), p.get("team"), p.get("role"),
                p.get("total_distance_m"), p.get("max_speed_mps"), p.get("avg_speed_mps"),
                p.get("max_acceleration_mps2"), p.get("jumps_count"), p.get("highest_jump_cm"),
                p.get("avg_jump_height_cm"), p.get("court_coverage_pct"), p.get("direction_changes")
            ])
        writer.writerow([])

        # Events Log Table
        writer.writerow(["=== MATCH EVENTS LOG ==="])
        writer.writerow(["Timestamp (s)", "Time (MM:SS)", "Event Type", "Player ID", "Details", "Confidence"])
        for ev in report.events:
            writer.writerow([
                ev.get("timestamp"), ev.get("formatted_time"), ev.get("event_type"),
                ev.get("player_id"), ev.get("details"), ev.get("confidence")
            ])

        return output.getvalue()

    def export_player_csv(self, report: PlayerReport) -> str:
        """Exports individual player time-series history to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([f"=== PLAYER {report.jersey_number} PERFORMANCE REPORT ==="])
        writer.writerow(["Sport", report.sport])
        writer.writerow(["Team", report.team])
        writer.writerow(["Total Distance (m)", report.total_distance_m])
        writer.writerow(["Max Speed (m/s)", report.max_speed_mps])
        writer.writerow(["Avg Speed (m/s)", report.avg_speed_mps])
        writer.writerow(["Max Accel (m/s2)", report.max_acceleration_mps2])
        writer.writerow(["Jumps", report.jumps_count])
        writer.writerow(["Max Jump (cm)", report.highest_jump_cm])
        writer.writerow(["Avg Jump (cm)", report.avg_jump_height_cm])
        writer.writerow(["Court Coverage (%)", report.court_coverage_pct])
        writer.writerow([])

        writer.writerow(["=== TIME SERIES SAMPLES ==="])
        writer.writerow(["Timestamp (s)", "Speed (m/s)", "Acceleration (m/s2)", "Distance (m)", "Court X (m)", "Court Y (m)"])
        for pt in report.speed_over_time:
            t = pt.get("timestamp", 0.0)
            writer.writerow([t, pt.get("speed_mps", 0.0)])

        return output.getvalue()

    def export_html_report(self, report: MatchReport) -> str:
        """Generates modern, self-contained, responsive HTML printable match report."""
        players_rows = ""
        for p in report.players:
            players_rows += f"""
            <tr>
                <td><strong>{p.get('jersey_number', f"#{p.get('player_id')}")}</strong></td>
                <td>{p.get('team', '-')}</td>
                <td>{p.get('total_distance_m', 0.0)} m</td>
                <td>{p.get('max_speed_mps', 0.0)} m/s</td>
                <td>{p.get('avg_speed_mps', 0.0)} m/s</td>
                <td>{p.get('max_acceleration_mps2', 0.0)} m/s²</td>
                <td>{p.get('jumps_count', 0)}</td>
                <td>{p.get('highest_jump_cm', 0.0)} cm</td>
                <td>{p.get('avg_jump_height_cm', 0.0)} cm</td>
                <td>{p.get('court_coverage_pct', 0.0)}%</td>
            </tr>
            """

        events_rows = ""
        for ev in report.events:
            events_rows += f"""
            <tr>
                <td><code>{ev.get('formatted_time', '00:00')}</code></td>
                <td><span class="badge">{ev.get('event_type', '').upper()}</span></td>
                <td>Player #{ev.get('player_id', '-')}</td>
                <td>{ev.get('details', '-')}</td>
                <td>{int((ev.get('confidence', 0.8) or 0.8) * 100)}%</td>
            </tr>
            """

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report.title} - Sports Analyzer AI Report</title>
    <style>
        :root {{
            --bg: #0f172a;
            --card-bg: #1e293b;
            --border: #334155;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #06b6d4;
            --primary-light: #38bdf8;
            --accent: #10b981;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 30px;
            line-height: 1.5;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid var(--border);
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{ margin: 0 0 8px 0; font-size: 26px; color: var(--primary-light); }}
        .header .meta {{ color: var(--text-muted); font-size: 14px; }}
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
        }}
        .card .title {{ font-size: 12px; color: var(--text-muted); text-transform: uppercase; margin-bottom: 6px; }}
        .card .value {{ font-size: 24px; font-weight: bold; color: var(--text); }}
        .section-title {{
            font-size: 18px;
            margin: 24px 0 12px 0;
            color: var(--primary);
            border-left: 4px solid var(--primary);
            padding-left: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--card-bg);
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 30px;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
            font-size: 13px;
        }}
        th {{ background: #0f172a; color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 11px; }}
        tr:hover {{ background: rgba(255, 255, 255, 0.02); }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            background: rgba(6, 182, 212, 0.15);
            color: var(--primary-light);
            border: 1px solid rgba(6, 182, 212, 0.3);
        }}
        .print-btn {{
            background: var(--primary);
            color: #000;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
        }}
        @media print {{
            .print-btn {{ display: none; }}
            body {{ background: #fff; color: #000; }}
            .card, table {{ border-color: #ddd; background: #fff; color: #000; }}
            th {{ background: #f0f0f0; color: #333; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>{report.title}</h1>
            <div class="meta">Sport: <strong>{report.sport.upper()}</strong> | Duration: <strong>{report.duration_formatted}</strong> | Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
        </div>
        <button class="print-btn" onclick="window.print()">Print / Export PDF</button>
    </div>

    <div class="cards-grid">
        <div class="card">
            <div class="title">Match Duration</div>
            <div class="value">{report.duration_formatted}</div>
        </div>
        <div class="card">
            <div class="title">Active Players</div>
            <div class="value">{report.active_players} / {report.players_detected}</div>
        </div>
        <div class="card">
            <div class="title">Total Distance</div>
            <div class="value">{report.total_distance_km} km</div>
        </div>
        <div class="card">
            <div class="title">Total Jumps</div>
            <div class="value">{report.total_jumps}</div>
        </div>
        <div class="card">
            <div class="title">Max Recorded Speed</div>
            <div class="value">{report.max_speed_mps} m/s</div>
        </div>
        <div class="card">
            <div class="title">Average Speed</div>
            <div class="value">{report.avg_speed_mps} m/s</div>
        </div>
    </div>

    <div class="section-title">Player Performance Analysis</div>
    <table>
        <thead>
            <tr>
                <th>Jersey</th>
                <th>Team</th>
                <th>Distance</th>
                <th>Max Speed</th>
                <th>Avg Speed</th>
                <th>Max Accel</th>
                <th>Jumps</th>
                <th>Max Jump</th>
                <th>Avg Jump</th>
                <th>Court Coverage</th>
            </tr>
        </thead>
        <tbody>
            {players_rows}
        </tbody>
    </table>

    <div class="section-title">Match Events & Replay Timeline</div>
    <table>
        <thead>
            <tr>
                <th>Time</th>
                <th>Event Type</th>
                <th>Player</th>
                <th>Details</th>
                <th>Confidence</th>
            </tr>
        </thead>
        <tbody>
            {events_rows if events_rows else "<tr><td colspan='5' style='text-align: center;'>No events recorded yet.</td></tr>"}
        </tbody>
    </table>

    <footer style="text-align: center; color: var(--text-muted); font-size: 11px; margin-top: 40px;">
        Sports Analyzer AI — Offline Computer Vision & Kinematics Engine
    </footer>
</body>
</html>
"""
        return html
