"""Kinematics Engine — real-time athletic speed, acceleration, distance, and jump analysis with perspective calibration."""
import math
import time
import enum
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

from backend.app.analytics.jump import JumpDetector


class MovementState(str, enum.Enum):
    STANDING = "standing"
    WALKING = "walking"
    RUNNING = "running"
    SPRINTING = "sprinting"
    AIRBORNE = "airborne"


@dataclass
class KinematicsSnapshot:
    """Read-only view of a player's kinematic state for serialization."""
    player_id: int
    instant_speed_mps: float
    avg_speed_mps: float
    max_speed_mps: float
    acceleration_mps2: float
    max_acceleration_mps2: float
    total_distance_m: float
    total_distance_px: float
    direction_changes: int
    jumps_count: int
    highest_jump_cm: float
    last_jump: Optional[Dict[str, Any]]
    movement_state: str
    velocity: Tuple[float, float]
    court_position: Tuple[float, float] = (0.0, 0.0)
    avg_jump_height_cm: float = 0.0
    court_coverage_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "instant_speed_mps": round(self.instant_speed_mps, 2),
            "avg_speed_mps": round(self.avg_speed_mps, 2),
            "max_speed_mps": round(self.max_speed_mps, 2),
            "acceleration_mps2": round(self.acceleration_mps2, 2),
            "max_acceleration_mps2": round(self.max_acceleration_mps2, 2),
            "total_distance_m": round(self.total_distance_m, 2),
            "total_distance_px": round(self.total_distance_px, 1),
            "direction_changes": self.direction_changes,
            "jumps_count": self.jumps_count,
            "highest_jump_cm": round(self.highest_jump_cm, 1),
            "avg_jump_height_cm": round(self.avg_jump_height_cm, 1),
            "court_coverage_pct": round(self.court_coverage_pct, 1),
            "last_jump": self.last_jump,
            "movement_state": self.movement_state,
            "velocity": (round(self.velocity[0], 2), round(self.velocity[1], 2)),
            "court_position": {"x_m": round(self.court_position[0], 2), "y_m": round(self.court_position[1], 2)}
        }


class PlayerKinematics:
    """
    Maintains time-series position history and computes biomechanical kinematics:
    velocity, acceleration, total distance, direction reversals, and vertical jumps.
    Supports both pixel-space and metric court-space (homography calibrated) coordinates.
    """

    def __init__(
        self,
        player_id: int,
        pixels_to_meters: float = 0.02,
        history_maxlen: int = 90
    ):
        self.player_id = player_id
        self.pixels_to_meters = pixels_to_meters
        self.history: deque = deque(maxlen=history_maxlen)        # [(x, y, timestamp)]
        self.metric_history: deque = deque(maxlen=history_maxlen) # [(xm, ym, timestamp)]
        self.speed_history: deque = deque(maxlen=history_maxlen)

        # Kinematic state
        self.instant_speed_mps: float = 0.0
        self.avg_speed_mps: float = 0.0
        self.max_speed_mps: float = 0.0
        self.acceleration_mps2: float = 0.0
        self.max_acceleration_mps2: float = 0.0
        self.total_distance_px: float = 0.0
        self.total_distance_m: float = 0.0
        self.velocity: Tuple[float, float] = (0.0, 0.0)
        self.direction_changes: int = 0
        self.state: MovementState = MovementState.STANDING
        self.current_court_pos: Tuple[float, float] = (0.0, 0.0)

        # Jump tracking
        self.jump_detector = JumpDetector(pixels_to_cm=0.5)
        self.jumps_detected: List[Dict[str, Any]] = []
        self.highest_jump_cm: float = 0.0
        self.last_jump: Optional[Dict[str, Any]] = None

        # Long-term analytics & time series for reports
        self.time_series: List[Dict[str, Any]] = []
        self._last_sample_t: float = -1.0
        self.visited_grid_cells: set = set()

    def update(
        self,
        center_x: float,
        center_y: float,
        timestamp: float,
        bottom_y: Optional[float] = None,
        court_x_m: Optional[float] = None,
        court_y_m: Optional[float] = None
    ) -> KinematicsSnapshot:
        """
        Ingests latest player position (and optional calibrated metric coordinates)
        and computes speed, acceleration, distance, direction changes, and jumps.
        """
        # Jump detection
        y_for_jump = bottom_y if bottom_y is not None else center_y
        jump_event = self.jump_detector.update(center_y=y_for_jump, timestamp=timestamp)
        if jump_event:
            self.jumps_detected.append(jump_event)
            self.last_jump = jump_event
            jump_h = jump_event.get("estimated_height_cm", 0.0)
            if jump_h > self.highest_jump_cm:
                self.highest_jump_cm = jump_h

        current_pt = (center_x, center_y, timestamp)
        
        # Metric court coordinates
        xm = court_x_m if court_x_m is not None else center_x * self.pixels_to_meters
        ym = court_y_m if court_y_m is not None else center_y * self.pixels_to_meters
        self.current_court_pos = (xm, ym)
        current_metric_pt = (xm, ym, timestamp)
        self.visited_grid_cells.add((round(xm, 1), round(ym, 1)))

        if len(self.history) >= 1:
            prev_pt = self.history[-1]
            prev_metric = self.metric_history[-1] if self.metric_history else (prev_pt[0] * self.pixels_to_meters, prev_pt[1] * self.pixels_to_meters, prev_pt[2])
            dt = timestamp - prev_pt[2]

            if dt > 0.005:
                dx = center_x - prev_pt[0]
                dy = center_y - prev_pt[1]
                dist_px = math.hypot(dx, dy)

                dx_m = xm - prev_metric[0]
                dy_m = ym - prev_metric[1]
                dist_m = math.hypot(dx_m, dy_m)

                # Ignore teleportation jumps (> 300px per frame)
                if dist_px < 300.0:
                    self.total_distance_px += dist_px
                    self.total_distance_m += dist_m

                    # Velocity & Speed computed from calibrated metric displacement if available
                    vx = dx_m / dt
                    vy = dy_m / dt
                    self.velocity = (vx, vy)
                    speed = math.hypot(vx, vy)

                    # Cap realistic human running speed (< 15 m/s)
                    if speed < 15.0:
                        prev_speed = self.instant_speed_mps
                        self.instant_speed_mps = speed
                        self.speed_history.append(speed)

                        if speed > self.max_speed_mps:
                            self.max_speed_mps = speed

                        # Acceleration
                        accel = (speed - prev_speed) / dt
                        if abs(accel) < 25.0:
                            self.acceleration_mps2 = accel
                            if abs(accel) > self.max_acceleration_mps2:
                                self.max_acceleration_mps2 = abs(accel)

                        # Average speed
                        if self.speed_history:
                            self.avg_speed_mps = float(np.mean(self.speed_history))

                    # Direction changes (acute angle reversal > 60 degrees)
                    if len(self.history) >= 2:
                        p_old = self.history[-2]
                        v1 = (prev_pt[0] - p_old[0], prev_pt[1] - p_old[1])
                        v2 = (dx, dy)
                        mag1 = math.hypot(v1[0], v1[1])
                        mag2 = math.hypot(v2[0], v2[1])

                        if mag1 > 2.0 and mag2 > 2.0:
                            dot = v1[0] * v2[0] + v1[1] * v2[1]
                            cos_val = max(-1.0, min(1.0, dot / (mag1 * mag2)))
                            if math.acos(cos_val) > math.radians(60.0):
                                self.direction_changes += 1

        self.history.append(current_pt)
        self.metric_history.append(current_metric_pt)
        self._classify_movement_state()

        # Sample time-series log every 0.2 seconds for reporting charts
        if self._last_sample_t < 0 or (timestamp - self._last_sample_t) >= 0.2:
            self.time_series.append({
                "timestamp": round(timestamp, 2),
                "speed_mps": round(self.instant_speed_mps, 2),
                "acceleration_mps2": round(self.acceleration_mps2, 2),
                "distance_m": round(self.total_distance_m, 2),
                "court_x_m": round(xm, 2),
                "court_y_m": round(ym, 2)
            })
            if len(self.time_series) > 5000:
                self.time_series = self.time_series[-5000:]
            self._last_sample_t = timestamp

        return self.get_snapshot()

    def _classify_movement_state(self):
        if self.jump_detector.current_phase.value != "standing":
            self.state = MovementState.AIRBORNE
        elif self.instant_speed_mps < 0.4:
            self.state = MovementState.STANDING
        elif self.instant_speed_mps < 2.5:
            self.state = MovementState.WALKING
        elif self.instant_speed_mps < 5.5:
            self.state = MovementState.RUNNING
        else:
            self.state = MovementState.SPRINTING

    def get_snapshot(self) -> KinematicsSnapshot:
        # Calculate average jump height
        jump_heights = [j.get("estimated_height_cm", 0.0) for j in self.jumps_detected if j.get("estimated_height_cm")]
        avg_jump_cm = float(np.mean(jump_heights)) if jump_heights else 0.0

        # Estimate court coverage percentage based on 1m x 1m visited areas (standard ~162m² court)
        coverage_pct = 0.0
        if self.visited_grid_cells:
            coverage_pct = min(100.0, max(1.0, round((len(self.visited_grid_cells) / 162.0) * 100.0, 1)))

        return KinematicsSnapshot(
            player_id=self.player_id,
            instant_speed_mps=self.instant_speed_mps,
            avg_speed_mps=self.avg_speed_mps,
            max_speed_mps=self.max_speed_mps,
            acceleration_mps2=self.acceleration_mps2,
            max_acceleration_mps2=self.max_acceleration_mps2,
            total_distance_m=self.total_distance_m,
            total_distance_px=self.total_distance_px,
            direction_changes=self.direction_changes,
            jumps_count=len(self.jumps_detected),
            highest_jump_cm=self.highest_jump_cm,
            avg_jump_height_cm=avg_jump_cm,
            court_coverage_pct=coverage_pct,
            last_jump=self.last_jump,
            movement_state=self.state.value,
            velocity=self.velocity,
            court_position=self.current_court_pos
        )



class KinematicsEngine:
    """
    Manages kinematic state for all players across video frames,
    supporting perspective court calibration.
    """

    def __init__(self, pixels_to_meters: float = 0.02, court_calibrator: Optional[Any] = None):
        self.pixels_to_meters = pixels_to_meters
        self.court_calibrator = court_calibrator
        self.players: Dict[int, PlayerKinematics] = {}

    def set_calibrator(self, calibrator: Any):
        self.court_calibrator = calibrator

    def update(
        self,
        tracks: List[Any],
        timestamp: float,
        poses: Optional[List[Any]] = None
    ) -> Dict[int, KinematicsSnapshot]:
        pose_by_id = {}
        if poses:
            for p in poses:
                pid = getattr(p, "player_id", None)
                if pid is not None:
                    pose_by_id[pid] = p

        snapshots: Dict[int, KinematicsSnapshot] = {}

        for trk in tracks:
            pid = getattr(trk, "player_id", getattr(trk, "track_id", 0))
            box = getattr(trk, "bbox", getattr(trk, "box", (0, 0, 0, 0)))

            if pid not in self.players:
                self.players[pid] = PlayerKinematics(
                    player_id=pid,
                    pixels_to_meters=self.pixels_to_meters
                )

            cx = (box[0] + box[2]) / 2.0
            cy = (box[1] + box[3]) / 2.0
            bottom_y = float(box[3])

            if pid in pose_by_id:
                pose_res = pose_by_id[pid]
                left_ankle = pose_res.get_keypoint("left_ankle")
                right_ankle = pose_res.get_keypoint("right_ankle")
                if left_ankle and right_ankle:
                    bottom_y = (left_ankle.y + right_ankle.y) / 2.0

            # Homography coordinate projection (feet position is best on court plane)
            court_xm, court_ym = None, None
            if self.court_calibrator is not None and self.court_calibrator.is_calibrated:
                court_xm, court_ym = self.court_calibrator.image_to_court(cx, bottom_y)

            snapshot = self.players[pid].update(
                cx, cy, timestamp,
                bottom_y=bottom_y,
                court_x_m=court_xm,
                court_y_m=court_ym
            )
            snapshots[pid] = snapshot

        return snapshots

    def get_player(self, player_id: int) -> Optional[KinematicsSnapshot]:
        if player_id in self.players:
            return self.players[player_id].get_snapshot()
        return None

    def get_player_time_series(self, player_id: int) -> List[Dict[str, Any]]:
        """Returns the full sampled time-series history for a player."""
        if player_id in self.players:
            return list(self.players[player_id].time_series)
        return []

    def get_player_jumps(self, player_id: int) -> List[Dict[str, Any]]:
        """Returns all detected jumps for a player with height and timestamps."""
        if player_id in self.players:
            return list(self.players[player_id].jumps_detected)
        return []

    def get_player_movement_path(self, player_id: int) -> List[Dict[str, Any]]:
        """Returns metric path points with timestamps."""
        if player_id in self.players:
            return [
                {"court_x_m": round(pt[0], 2), "court_y_m": round(pt[1], 2), "timestamp": round(pt[2], 2)}
                for pt in self.players[player_id].metric_history
            ]
        return []

    def get_all_metric_positions(self) -> Dict[int, List[Tuple[float, float]]]:
        """Returns all recorded metric positions (X_m, Y_m) per player for heatmaps."""
        return {
            pid: [(pt[0], pt[1]) for pt in p.metric_history]
            for pid, p in self.players.items()
        }

    def reset(self):
        self.players.clear()

