"""
Kabaddi Rules Engine — IKF / Pro Kabaddi League compliant.

Court geometry (X = lengthwise, Y = widthwise):
  Total: 13m x 10m
  Midline: X = 6.5m
  Team A defends left half (X in [0, 6.5]), Team B defends right half (X in [6.5, 13]).
  When Team A raids (enters right half):
    Baulk line (must cross): X = 10.25m  (6.5 + 3.75)
    Bonus line (bonus pt):   X = 11.25m  (6.5 + 4.75)
  When Team B raids (enters left half):
    Baulk line:              X =  2.75m  (6.5 - 3.75)
    Bonus line:              X =  1.75m  (6.5 - 4.75)
  Lobby: Y in [-1, 0) and Y in (10, 11] -- active only after contact.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.app.sports.base import SportsAnalyzer


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def get_confidence_level(score: Optional[float]) -> str:
    """Map numeric confidence to a human-readable label."""
    if score is None or score == 0.0:
        return "Unknown"
    if score >= 0.80:
        return "High"
    if score >= 0.50:
        return "Medium"
    return "Low"


# ---------------------------------------------------------------------------
# Main Analyzer
# ---------------------------------------------------------------------------

class KabaddiAnalyzer(SportsAnalyzer):
    """
    Full Kabaddi rules engine.

    Court: 13 m x 10 m (Men). Midline at X = 6.5 m.
    Raid state machine: WAITING -> RAID_ACTIVE -> RAID_COMPLETE
    """

    TACKLE_PROXIMITY_M: float = 1.5
    LOBBY_ACTIVE_Y_MIN: float = -1.0
    LOBBY_ACTIVE_Y_MAX: float = 11.0
    MIDLINE_X: float = 6.5
    BAULK_OFFSET: float = 3.75
    BONUS_OFFSET: float = 4.75
    RAID_TIME_LIMIT_S: float = 30.0

    def __init__(self):
        super().__init__("kabaddi")
        self.court_dimensions_meters: Dict[str, Any] = {
            "length": 13.0,
            "width": 10.0,
            "midline_x": self.MIDLINE_X,
            "team_a_baulk_x": self.MIDLINE_X + self.BAULK_OFFSET,
            "team_a_bonus_x": self.MIDLINE_X + self.BONUS_OFFSET,
            "team_b_baulk_x": self.MIDLINE_X - self.BAULK_OFFSET,
            "team_b_bonus_x": self.MIDLINE_X - self.BONUS_OFFSET,
            "lobby_y_min": self.LOBBY_ACTIVE_Y_MIN,
            "lobby_y_max": self.LOBBY_ACTIVE_Y_MAX,
        }

        # Raid state machine
        self.raid_state: str = "WAITING"
        self.active_raider_id: Optional[int] = None
        self.raiding_team: Optional[str] = None
        self.raid_start_time: Optional[float] = None
        self.raid_points: int = 0

        # Do-or-Die tracking (per team)
        self._consecutive_empty_raids: Dict[str, int] = {"Team A": 0, "Team B": 0}
        self._do_or_die_active: bool = False

        self._lobby_contact: bool = False
        self._events: List[Dict[str, Any]] = []
        self._violations: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # SportsAnalyzer interface
    # ------------------------------------------------------------------

    def calibrate_court(
        self,
        frame: np.ndarray,
        manual_points: Optional[List[Dict[str, float]]] = None,
    ) -> bool:
        self.court_calibrated = True
        return True

    def get_court_layout(self) -> Dict[str, Any]:
        return {
            "sport": "kabaddi",
            "dimensions_meters": self.court_dimensions_meters,
            "key_lines": [
                "Midline (X=6.5m)",
                "Team A Baulk line (X=10.25m)",
                "Team A Bonus line (X=11.25m)",
                "Team B Baulk line (X=2.75m)",
                "Team B Bonus line (X=1.75m)",
                "Lobby (Y=-1 to 0 and Y=10 to 11)",
            ],
        }

    def analyze_frame(
        self,
        frame_idx: int,
        timestamp: float,
        players: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Main orchestrator -- runs all checks each frame."""
        frame_events: List[Dict[str, Any]] = []
        frame_violations: List[Dict[str, Any]] = []

        # 1. Identify raider
        raider_info = self.check_raider_identification(players)
        raider_id = raider_info["player_id"] if raider_info else None
        raider_team = raider_info["raiding_team"] if raider_info else None

        # 2. Update raid state machine
        self._update_raid_state(raider_id, raider_team, timestamp)

        # 3. Per-raider checks
        if self.raid_state == "RAID_ACTIVE" and raider_id is not None:
            raider_player = next((p for p in players if p.get("player_id") == raider_id), None)
            if raider_player:
                x_m, y_m = self._get_position(raider_player)
                defenders = [p for p in players if p.get("player_id") != raider_id]
                defender_count = len(defenders)

                baulk_evt = self.check_baulk_line_crossing(raider_id, self.raiding_team, x_m)
                if baulk_evt:
                    frame_events.append(baulk_evt)

                bonus_evt = self.check_bonus_line_touch(raider_id, self.raiding_team, x_m, defender_count)
                if bonus_evt:
                    frame_events.append(bonus_evt)
                    self.raid_points += 1

                tackle_evt = self.check_tackle_zone(raider_id, x_m, y_m, defenders)
                if tackle_evt:
                    frame_events.append(tackle_evt)

                if self.raid_start_time and (timestamp - self.raid_start_time) > self.RAID_TIME_LIMIT_S:
                    frame_violations.append({
                        "violation_type": "RAID_TIMEOUT",
                        "raider_id": raider_id,
                        "team": self.raiding_team,
                        "description": "Raider exceeded 30-second raid time limit.",
                        "confidence_level": "High",
                        "timestamp": timestamp,
                        "frame_idx": frame_idx,
                    })

        # 4. Out-of-bounds for all players
        for player in players:
            x_m, y_m = self._get_position(player)
            pid = player.get("player_id", -1)
            oob = self.check_out_of_bounds(pid, x_m, y_m)
            if oob:
                frame_violations.append(oob)

        # 5. Do-or-Die check
        if raider_team and len(frame_events) == 0 and self.raid_state == "RAID_COMPLETE":
            self._consecutive_empty_raids[raider_team] = (
                self._consecutive_empty_raids.get(raider_team, 0) + 1
            )
            do_or_die = self.check_do_or_die_raid(raider_team)
            if do_or_die:
                frame_events.append(do_or_die)

        self._events.extend(frame_events)
        self._violations.extend(frame_violations)

        return {
            "sport": "kabaddi",
            "frame_idx": frame_idx,
            "timestamp": timestamp,
            "raid_state": self.raid_state,
            "active_raider_id": self.active_raider_id,
            "raiding_team": self.raiding_team,
            "raid_points": self.raid_points,
            "consecutive_empty_raids": dict(self._consecutive_empty_raids),
            "do_or_die_active": self._do_or_die_active,
            "events": frame_events,
            "violations": frame_violations,
        }

    # ------------------------------------------------------------------
    # Raid State Machine
    # ------------------------------------------------------------------

    def _update_raid_state(
        self,
        raider_id: Optional[int],
        raider_team: Optional[str],
        timestamp: float,
    ) -> None:
        if self.raid_state == "WAITING":
            if raider_id is not None:
                self.raid_state = "RAID_ACTIVE"
                self.active_raider_id = raider_id
                self.raiding_team = raider_team
                self.raid_start_time = timestamp
                self.raid_points = 0
                self._lobby_contact = False
        elif self.raid_state == "RAID_ACTIVE":
            if raider_id is None:
                self.raid_state = "RAID_COMPLETE"
        elif self.raid_state == "RAID_COMPLETE":
            self.raid_state = "WAITING"
            self.active_raider_id = None
            self.raid_start_time = None

    def reset_raid(self) -> None:
        """Reset raid state to WAITING."""
        self.raid_state = "WAITING"
        self.active_raider_id = None
        self.raiding_team = None
        self.raid_start_time = None
        self.raid_points = 0
        self._lobby_contact = False
        self._do_or_die_active = False

    # ------------------------------------------------------------------
    # Detection Methods
    # ------------------------------------------------------------------

    def check_raider_identification(
        self, players: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Identify raider = player crossing into opponent's half or designated raider."""
        if not players:
            return None

        # 1. Check for explicit role or team mismatch
        for player in players:
            x_m, _ = self._get_position(player)
            conf = player.get("confidence", 0.9)
            role = player.get("role")
            team = player.get("team")
            if role == "raider":
                r_team = team or ("Team A" if x_m > self.MIDLINE_X else "Team B")
                return {"player_id": player.get("player_id"), "raiding_team": r_team, "x_m": x_m, "confidence": conf}
            if team == "Team A" and x_m > self.MIDLINE_X:
                return {"player_id": player.get("player_id"), "raiding_team": "Team A", "x_m": x_m, "confidence": conf}
            if team == "Team B" and x_m < self.MIDLINE_X:
                return {"player_id": player.get("player_id"), "raiding_team": "Team B", "x_m": x_m, "confidence": conf}

        # 2. Check asymmetry: 1 player on one side, multiple on the other
        right_players = [p for p in players if self._get_position(p)[0] > self.MIDLINE_X]
        left_players = [p for p in players if self._get_position(p)[0] <= self.MIDLINE_X]

        if len(right_players) == 1 and len(left_players) >= 1:
            p = right_players[0]
            x_m, _ = self._get_position(p)
            return {"player_id": p.get("player_id"), "raiding_team": "Team A", "x_m": x_m, "confidence": p.get("confidence", 0.9)}

        if len(left_players) == 1 and len(right_players) >= 1:
            p = left_players[0]
            x_m, _ = self._get_position(p)
            return {"player_id": p.get("player_id"), "raiding_team": "Team B", "x_m": x_m, "confidence": p.get("confidence", 0.9)}

        # 3. Fallback: minority player group
        if 0 < len(right_players) < len(left_players):
            p = right_players[0]
            x_m, _ = self._get_position(p)
            return {"player_id": p.get("player_id"), "raiding_team": "Team A", "x_m": x_m, "confidence": p.get("confidence", 0.9)}

        if 0 < len(left_players) < len(right_players):
            p = left_players[0]
            x_m, _ = self._get_position(p)
            return {"player_id": p.get("player_id"), "raiding_team": "Team B", "x_m": x_m, "confidence": p.get("confidence", 0.9)}

        return None

    def check_baulk_line_crossing(
        self,
        raider_id: int,
        raiding_team: Optional[str],
        x_m: float,
        confidence: float = 0.85,
    ) -> Optional[Dict[str, Any]]:
        """Returns BAULK_CROSSED event if raider has crossed the baulk line."""
        if raiding_team == "Team A" and x_m >= self.MIDLINE_X + self.BAULK_OFFSET:
            return {
                "event_type": "BAULK_CROSSED",
                "raider_id": raider_id,
                "raiding_team": raiding_team,
                "baulk_x_m": self.MIDLINE_X + self.BAULK_OFFSET,
                "raider_x_m": x_m,
                "description": "Raider crossed the baulk line -- raid is now valid.",
                "confidence": confidence,
                "confidence_level": get_confidence_level(confidence),
            }
        if raiding_team == "Team B" and x_m <= self.MIDLINE_X - self.BAULK_OFFSET:
            return {
                "event_type": "BAULK_CROSSED",
                "raider_id": raider_id,
                "raiding_team": raiding_team,
                "baulk_x_m": self.MIDLINE_X - self.BAULK_OFFSET,
                "raider_x_m": x_m,
                "description": "Raider crossed the baulk line -- raid is now valid.",
                "confidence": confidence,
                "confidence_level": get_confidence_level(confidence),
            }
        return None

    def check_bonus_line_touch(
        self,
        raider_id: int,
        raiding_team: Optional[str],
        x_m: float,
        defenders_on_court: int,
        confidence: float = 0.82,
    ) -> Optional[Dict[str, Any]]:
        """Returns BONUS_POINT event if raider crosses bonus line with >=6 defenders."""
        if defenders_on_court < 6:
            return None
        crossed = False
        bonus_x = 0.0
        if raiding_team == "Team A" and x_m >= self.MIDLINE_X + self.BONUS_OFFSET:
            crossed = True
            bonus_x = self.MIDLINE_X + self.BONUS_OFFSET
        elif raiding_team == "Team B" and x_m <= self.MIDLINE_X - self.BONUS_OFFSET:
            crossed = True
            bonus_x = self.MIDLINE_X - self.BONUS_OFFSET
        if crossed:
            return {
                "event_type": "BONUS_POINT",
                "raider_id": raider_id,
                "raiding_team": raiding_team,
                "bonus_line_x_m": bonus_x,
                "raider_x_m": x_m,
                "bonus_points": 1,
                "defenders_on_court": defenders_on_court,
                "description": f"Bonus point! Raider crossed bonus line with {defenders_on_court} defenders.",
                "confidence": confidence,
                "confidence_level": get_confidence_level(confidence),
            }
        return None

    def check_out_of_bounds(
        self,
        player_id: int,
        x_m: float,
        y_m: float,
        lobby_active: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Returns OUT_OF_BOUNDS violation if player steps outside court."""
        out = False
        reason = ""
        if x_m < 0.0 or x_m > 13.0:
            out = True
            reason = f"Stepped outside endline (X={x_m:.2f}m)"
        elif not lobby_active and (y_m < 0.0 or y_m > 10.0):
            out = True
            reason = f"Stepped into lobby before contact (Y={y_m:.2f}m)"
        elif lobby_active and (y_m < self.LOBBY_ACTIVE_Y_MIN or y_m > self.LOBBY_ACTIVE_Y_MAX):
            out = True
            reason = f"Stepped outside extended lobby boundary (Y={y_m:.2f}m)"

        if out:
            return {
                "violation_type": "OUT_OF_BOUNDS",
                "player_id": player_id,
                "x_m": x_m,
                "y_m": y_m,
                "description": reason,
                "confidence_level": "High",
            }
        return None

    def check_tackle_zone(
        self,
        raider_id: int,
        raider_x: float,
        raider_y: float,
        defenders: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Detect tackle: >=1 defender within TACKLE_PROXIMITY_M. Super Tackle if <=3 defenders total."""
        close_defenders: List[int] = []
        for d in defenders:
            dx, dy = self._get_position(d)
            dist = ((dx - raider_x) ** 2 + (dy - raider_y) ** 2) ** 0.5
            if dist <= self.TACKLE_PROXIMITY_M:
                close_defenders.append(d.get("player_id", -1))

        if not close_defenders:
            return None

        is_super = len(defenders) <= 3
        return {
            "event_type": "SUPER_TACKLE" if is_super else "TACKLE_ATTEMPT",
            "raider_id": raider_id,
            "defender_ids": close_defenders,
            "defenders_on_court": len(defenders),
            "super_tackle": is_super,
            "points": 2 if is_super else 1,
            "description": (
                f"Super Tackle! Only {len(defenders)} defenders -- worth 2 points."
                if is_super
                else f"Tackle attempt by {len(close_defenders)} defender(s)."
            ),
            "confidence": 0.80,
            "confidence_level": "High" if is_super else "Medium",
        }

    def check_do_or_die_raid(self, raiding_team: str) -> Optional[Dict[str, Any]]:
        """Emit DO_OR_DIE_RAID on 3rd consecutive empty raid."""
        streak = self._consecutive_empty_raids.get(raiding_team, 0)
        if streak >= 3:
            self._do_or_die_active = True
            return {
                "event_type": "DO_OR_DIE_RAID",
                "raiding_team": raiding_team,
                "consecutive_empty_raids": streak,
                "description": (
                    f"Do-or-Die raid activated for {raiding_team} "
                    f"({streak} consecutive empty raids). Raider must score or is out."
                ),
                "confidence": 0.90,
                "confidence_level": "High",
            }
        return None

    def check_super_raid(self, raid_points: int) -> Optional[Dict[str, Any]]:
        """Super Raid = >=3 points in one raid."""
        if raid_points >= 3:
            return {
                "event_type": "SUPER_RAID",
                "raid_points": raid_points,
                "description": f"Super Raid! {raid_points} points scored in one raid.",
                "confidence": 0.95,
                "confidence_level": "High",
            }
        return None

    def check_all_out(
        self, defending_team: str, defenders_on_court: int
    ) -> Optional[Dict[str, Any]]:
        """All-Out (Lona) -- all 7 defenders dismissed; 2 bonus points awarded."""
        if defenders_on_court == 0:
            return {
                "event_type": "ALL_OUT",
                "defending_team": defending_team,
                "bonus_points": 2,
                "description": f"ALL OUT (Lona)! {defending_team} fully dismissed -- 2 bonus points awarded.",
                "confidence": 0.99,
                "confidence_level": "High",
            }
        return None

    # ------------------------------------------------------------------
    # Public accessors for pipeline
    # ------------------------------------------------------------------

    def get_events(self) -> List[Dict[str, Any]]:
        return list(self._events)

    def get_violations(self) -> List[Dict[str, Any]]:
        return list(self._violations)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _classify_court_half(self, x_m: float) -> str:
        return "Team A" if x_m <= self.MIDLINE_X else "Team B"

    @staticmethod
    def _get_position(player: Dict[str, Any]) -> Tuple[float, float]:
        kin = player.get("kinematics", {})
        pos = kin.get("court_position", {})
        return float(pos.get("x_m", 0.0)), float(pos.get("y_m", 0.0))
