"""
Kho Kho Rules Engine — KKFI (Kho Kho Federation of India) compliant.

Court geometry (X = cross-lane axis / lengthwise, Y = central lane axis / widthwise):
  Total court: 27m x 16m.
  Central lane: runs along X axis, centered at Y = 8.0m, width 0.30m.
  Cross lanes: 8 lanes at X = 1.5, 4.5, 7.5, 10.5, 13.5, 16.5, 19.5, 22.5m.
  Posts: at (X=1.5, Y=8.0) and (X=22.5, Y=8.0).
  Free Zones: X in [0, 1.5] behind left post, X in [22.5, 27] behind right post.
  Chaser squares: 0.30m x 0.30m at each (cross_lane_x, Y=8.0) intersection.
    Square index 0 -> X=1.5, square 7 -> X=22.5.
  Sitting chasers alternate direction (facing +Y or -Y from their square).
"""
from __future__ import annotations

import math
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
# Constants
# ---------------------------------------------------------------------------

CROSS_LANE_X_POSITIONS = [1.5, 4.5, 7.5, 10.5, 13.5, 16.5, 19.5, 22.5]
CENTRAL_LANE_Y = 8.0
CENTRAL_LANE_HALF_WIDTH = 0.15   # 30cm total width
SQUARE_HALF_SIZE = 0.15           # 30cm square
FREE_ZONE_LEFT_MAX_X = 1.5
FREE_ZONE_RIGHT_MIN_X = 22.5
KHO_TOUCH_PROXIMITY_M = 0.50     # Max distance for valid Kho transfer
RUNNER_TAG_PROXIMITY_M = 0.30    # Max distance for runner dismissed


# ---------------------------------------------------------------------------
# Main Analyzer
# ---------------------------------------------------------------------------

class KhoKhoAnalyzer(SportsAnalyzer):
    """
    Full Kho Kho rules engine.

    Court: 27m x 16m. Central lane along X, centered at Y=8m.
    9 chasers: 1 active (running) + 8 sitting in alternating squares.
    3 runners per batch try to survive.
    """

    def __init__(self):
        super().__init__("kho_kho")
        self.court_dimensions_meters: Dict[str, Any] = {
            "length": 27.0,
            "width": 16.0,
            "central_lane_y": CENTRAL_LANE_Y,
            "central_lane_width": 0.30,
            "cross_lane_x_positions": CROSS_LANE_X_POSITIONS,
            "posts": [
                {"x": FREE_ZONE_LEFT_MAX_X, "y": CENTRAL_LANE_Y},
                {"x": FREE_ZONE_RIGHT_MIN_X, "y": CENTRAL_LANE_Y},
            ],
            "free_zone_left_max_x": FREE_ZONE_LEFT_MAX_X,
            "free_zone_right_min_x": FREE_ZONE_RIGHT_MIN_X,
        }

        # Active chaser state
        self.active_chaser_id: Optional[int] = None
        self._chaser_committed_direction: Optional[str] = None   # "left" or "right"
        self._chaser_prev_positions: Dict[int, Tuple[float, float]] = {}

        # Sitting chaser states: player_id -> square_index
        self._sitting_chasers: Dict[int, int] = {}

        # Batch tracking
        self.runners_in_batch: int = 3
        self.runners_remaining: int = 3

        # Logs
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
            "sport": "kho_kho",
            "dimensions_meters": self.court_dimensions_meters,
            "key_lines": [
                "Central Lane (Y=8m, width=30cm)",
                "8 Cross Lanes at X = 1.5, 4.5, 7.5, 10.5, 13.5, 16.5, 19.5, 22.5m",
                "Posts at (1.5, 8.0) and (22.5, 8.0)",
                "Free Zones: X<1.5m (left) and X>22.5m (right)",
                "8 Chaser Squares (30cm x 30cm) at intersections",
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

        # 1. Identify active chaser (fastest mover among chasers)
        active = self.track_active_chaser(players)
        if active:
            self.active_chaser_id = active["player_id"]

        # 2. Active chaser direction & central lane checks
        if self.active_chaser_id is not None:
            chaser_player = next(
                (p for p in players if p.get("player_id") == self.active_chaser_id), None
            )
            if chaser_player:
                curr_x, curr_y = self._get_position(chaser_player)
                prev_pos = self._chaser_prev_positions.get(self.active_chaser_id)

                if prev_pos is not None:
                    prev_x, prev_y = prev_pos

                    # Infer committed direction from first significant movement
                    if self._chaser_committed_direction is None:
                        dx = curr_x - prev_x
                        if abs(dx) > 0.1:
                            self._chaser_committed_direction = "right" if dx > 0 else "left"

                    # Direction fault check
                    dir_fault = self.check_active_chaser_direction(
                        self.active_chaser_id, curr_x, prev_x, self._chaser_committed_direction
                    )
                    if dir_fault:
                        frame_violations.append(dir_fault)

                    # Central lane crossing check
                    lane_cross = self.check_central_lane_crossing(
                        self.active_chaser_id, prev_y, curr_y
                    )
                    if lane_cross:
                        frame_violations.append(lane_cross)

                self._chaser_prev_positions[self.active_chaser_id] = (curr_x, curr_y)

        # 3. Check runner tags
        runners = [p for p in players if p.get("role") == "runner"]
        if self.active_chaser_id is not None:
            chaser_player = next(
                (p for p in players if p.get("player_id") == self.active_chaser_id), None
            )
            if chaser_player:
                cx, cy = self._get_position(chaser_player)
                for runner in runners:
                    rx, ry = self._get_position(runner)
                    tag_evt = self.check_runner_tagged(
                        self.active_chaser_id,
                        runner.get("player_id", -1),
                        (cx, cy),
                        (rx, ry),
                    )
                    if tag_evt:
                        frame_events.append(tag_evt)
                        self.runners_remaining = max(0, self.runners_remaining - 1)

        # 4. Chaser seating checks
        sitting_players = [p for p in players if p.get("player_id") in self._sitting_chasers]
        for sp in sitting_players:
            sx, sy = self._get_position(sp)
            sq_idx = self._sitting_chasers[sp["player_id"]]
            seat_viol = self.check_chaser_seating(sp["player_id"], sx, sy, sq_idx)
            if seat_viol:
                frame_violations.append(seat_viol)

        self._events.extend(frame_events)
        self._violations.extend(frame_violations)

        return {
            "sport": "kho_kho",
            "frame_idx": frame_idx,
            "timestamp": timestamp,
            "active_chaser_id": self.active_chaser_id,
            "committed_direction": self._chaser_committed_direction,
            "runners_remaining": self.runners_remaining,
            "events": frame_events,
            "violations": frame_violations,
        }

    # ------------------------------------------------------------------
    # Detection Methods
    # ------------------------------------------------------------------

    def track_active_chaser(
        self, players: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Identify the active chaser using speed heuristic:
        active chaser = fastest moving player among all non-runner players.
        """
        max_speed = 0.0
        active = None
        for player in players:
            if player.get("role") == "runner":
                continue
            kin = player.get("kinematics", {})
            speed = float(kin.get("instant_speed_mps", 0.0))
            if speed > max_speed:
                max_speed = speed
                active = {
                    "player_id": player.get("player_id"),
                    "speed_mps": speed,
                    "confidence": player.get("confidence", 0.0),
                }
        return active if max_speed > 0.5 else None  # Require min movement to assign

    def get_chaser_square(self, x_m: float, y_m: float) -> Optional[int]:
        """
        Return the square index (0-7) if (x_m, y_m) is within a chaser square.
        Returns None if not inside any square.
        """
        for idx, sq_x in enumerate(CROSS_LANE_X_POSITIONS):
            if (
                abs(x_m - sq_x) <= SQUARE_HALF_SIZE
                and abs(y_m - CENTRAL_LANE_Y) <= SQUARE_HALF_SIZE
            ):
                return idx
        return None

    def is_in_free_zone(self, x_m: float) -> bool:
        """Returns True if position is within the free zone behind either post."""
        return x_m <= FREE_ZONE_LEFT_MAX_X or x_m >= FREE_ZONE_RIGHT_MIN_X

    def check_active_chaser_direction(
        self,
        chaser_id: int,
        curr_x: float,
        prev_x: float,
        committed_direction: Optional[str],
        confidence: float = 0.78,
    ) -> Optional[Dict[str, Any]]:
        """
        Direction Fault: active chaser reverses direction before reaching the free zone.
        committed_direction: 'left' (decreasing X) or 'right' (increasing X).
        """
        if committed_direction is None:
            return None
        dx = curr_x - prev_x
        if abs(dx) < 0.05:
            return None  # Negligible movement

        reversed_dir = (committed_direction == "right" and dx < -0.15) or \
                       (committed_direction == "left" and dx > 0.15)

        if reversed_dir and not self.is_in_free_zone(curr_x):
            return {
                "violation_type": "DIRECTION_FAULT",
                "chaser_id": chaser_id,
                "committed_direction": committed_direction,
                "movement_delta_x": round(dx, 3),
                "description": (
                    f"Direction Fault! Chaser reversed direction (was going '{committed_direction}') "
                    f"outside the free zone."
                ),
                "confidence": confidence,
                "confidence_level": get_confidence_level(confidence),
            }
        return None

    def check_central_lane_crossing(
        self,
        chaser_id: int,
        prev_y: float,
        curr_y: float,
        confidence: float = 0.82,
    ) -> Optional[Dict[str, Any]]:
        """
        Central Lane Crossing Violation: active chaser crosses to the other side
        of the central lane (from Y < 7.85 to Y > 8.15, or vice versa).
        This is only a fault if they didn't loop around the post (simplified: detect cross).
        """
        lane_low = CENTRAL_LANE_Y - CENTRAL_LANE_HALF_WIDTH
        lane_high = CENTRAL_LANE_Y + CENTRAL_LANE_HALF_WIDTH

        was_below = prev_y < lane_low
        now_above = curr_y > lane_high
        was_above = prev_y > lane_high
        now_below = curr_y < lane_low

        if (was_below and now_above) or (was_above and now_below):
            return {
                "violation_type": "CENTRAL_LANE_CROSSING",
                "chaser_id": chaser_id,
                "prev_y": round(prev_y, 3),
                "curr_y": round(curr_y, 3),
                "description": (
                    "Central Lane Crossing! Chaser crossed the central lane "
                    "without going around the post."
                ),
                "confidence": confidence,
                "confidence_level": get_confidence_level(confidence),
            }
        return None

    def check_kho_validity(
        self,
        giver_id: int,
        receiver_id: int,
        giver_pos: Tuple[float, float],
        receiver_pos: Tuple[float, float],
        receiver_in_square: bool,
        confidence: float = 0.75,
    ) -> Dict[str, Any]:
        """
        Check if a Kho transfer is valid.
        Valid Kho: giver within KHO_TOUCH_PROXIMITY_M of receiver AND receiver is seated in a square.
        Returns event dict with 'valid' flag.
        """
        dist = math.hypot(giver_pos[0] - receiver_pos[0], giver_pos[1] - receiver_pos[1])
        is_close = dist <= KHO_TOUCH_PROXIMITY_M
        is_valid = is_close and receiver_in_square

        event: Dict[str, Any] = {
            "event_type": "KHO_GIVEN" if is_valid else "FALSE_KHO",
            "giver_id": giver_id,
            "receiver_id": receiver_id,
            "distance_m": round(dist, 3),
            "receiver_in_square": receiver_in_square,
            "valid": is_valid,
            "description": (
                f"Valid Kho from player {giver_id} to {receiver_id}."
                if is_valid
                else (
                    "False Kho! Receiver not seated in square."
                    if is_close and not receiver_in_square
                    else f"False Kho! Giver too far from receiver ({dist:.2f}m)."
                )
            ),
            "confidence": confidence,
            "confidence_level": get_confidence_level(confidence),
        }
        return event

    def check_runner_tagged(
        self,
        chaser_id: int,
        runner_id: int,
        chaser_pos: Tuple[float, float],
        runner_pos: Tuple[float, float],
        confidence: float = 0.85,
    ) -> Optional[Dict[str, Any]]:
        """Returns RUNNER_TAGGED event if active chaser is within tag proximity of a runner."""
        dist = math.hypot(chaser_pos[0] - runner_pos[0], chaser_pos[1] - runner_pos[1])
        if dist <= RUNNER_TAG_PROXIMITY_M:
            return {
                "event_type": "RUNNER_TAGGED",
                "chaser_id": chaser_id,
                "runner_id": runner_id,
                "distance_m": round(dist, 3),
                "description": f"Runner {runner_id} tagged by chaser {chaser_id}!",
                "confidence": confidence,
                "confidence_level": get_confidence_level(confidence),
            }
        return None

    def check_chaser_seating(
        self,
        chaser_id: int,
        x_m: float,
        y_m: float,
        assigned_square_idx: int,
        confidence: float = 0.70,
    ) -> Optional[Dict[str, Any]]:
        """Returns CHASER_OUT_OF_SQUARE violation if sitting chaser leaves their square."""
        sq_x = CROSS_LANE_X_POSITIONS[assigned_square_idx]
        out_of_square = (
            abs(x_m - sq_x) > SQUARE_HALF_SIZE * 2
            or abs(y_m - CENTRAL_LANE_Y) > SQUARE_HALF_SIZE * 2
        )
        if out_of_square:
            return {
                "violation_type": "CHASER_OUT_OF_SQUARE",
                "chaser_id": chaser_id,
                "square_idx": assigned_square_idx,
                "expected_x": sq_x,
                "actual_x": round(x_m, 3),
                "actual_y": round(y_m, 3),
                "description": (
                    f"Sitting chaser {chaser_id} left assigned square {assigned_square_idx}."
                ),
                "confidence": confidence,
                "confidence_level": get_confidence_level(confidence),
            }
        return None

    def assign_chaser_to_square(self, chaser_id: int, square_idx: int) -> None:
        """Register a sitting chaser to a specific square (called on Kho transfer)."""
        self._sitting_chasers[chaser_id] = square_idx

    def reset_batch(self) -> None:
        """Reset runner batch (called between runner batches)."""
        self.runners_remaining = 3
        self.runners_in_batch = 3

    def reset_turn(self) -> None:
        """Reset all state for a new chase turn."""
        self.active_chaser_id = None
        self._chaser_committed_direction = None
        self._chaser_prev_positions.clear()
        self._sitting_chasers.clear()
        self.runners_remaining = 3
        self.runners_in_batch = 3

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

    @staticmethod
    def _get_position(player: Dict[str, Any]) -> Tuple[float, float]:
        kin = player.get("kinematics", {})
        pos = kin.get("court_position", {})
        return float(pos.get("x_m", 0.0)), float(pos.get("y_m", 0.0))
