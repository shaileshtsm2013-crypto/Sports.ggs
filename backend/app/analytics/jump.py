import enum
from typing import Dict, Any, List, Optional
import numpy as np


class JumpPhase(enum.Enum):
    STANDING = "standing"
    PREPARATION = "preparation"
    TAKEOFF = "takeoff"
    AIRBORNE = "airborne"
    PEAK = "peak"
    LANDING = "landing"


class JumpDetector:
    """
    Temporal Jump Detection using vertical displacement and velocity profiles.
    Estimated jump height labeled with appropriate confidence levels.
    """

    def __init__(self, pixels_to_cm: float = 0.5):
        self.pixels_to_cm = pixels_to_cm
        self.current_phase = JumpPhase.STANDING
        self.jumps_detected: List[Dict[str, Any]] = []
        self.baseline_ankle_y: Optional[float] = None
        self.min_y: Optional[float] = None
        self.takeoff_time: Optional[float] = None

    def update(self, center_y: float, timestamp: float) -> Optional[Dict[str, Any]]:
        """
        Updates jump detector state with player vertical center position.
        Returns a completed jump dict if landing occurred.
        """
        if self.baseline_ankle_y is None:
            self.baseline_ankle_y = center_y
            return None

        # State transitions
        diff_y = self.baseline_ankle_y - center_y  # Positive when moving upward

        if self.current_phase == JumpPhase.STANDING:
            if diff_y > 25:  # Significant upward movement
                self.current_phase = JumpPhase.AIRBORNE
                self.takeoff_time = timestamp
                self.min_y = center_y

        elif self.current_phase == JumpPhase.AIRBORNE:
            if center_y < self.min_y:
                self.min_y = center_y
                
            # Returning close to baseline
            if diff_y < 10 and self.takeoff_time is not None:
                duration = max(0.1, timestamp - self.takeoff_time)
                max_displacement_px = self.baseline_ankle_y - (self.min_y or center_y)
                
                # Formula based on flight time: h = 1/2 * g * (t/2)^2
                time_height_cm = (0.5 * 980.0 * ((duration / 2.0) ** 2))
                px_height_cm = max_displacement_px * self.pixels_to_cm
                
                # Blend with moderate confidence
                est_height_cm = round(float(0.6 * px_height_cm + 0.4 * time_height_cm), 1)
                
                jump_info = {
                    "timestamp": round(timestamp, 2),
                    "duration_sec": round(duration, 2),
                    "estimated_height_cm": min(120.0, max(15.0, est_height_cm)),
                    "confidence": "Medium" if duration < 1.2 else "Low",
                    "type": "vertical_jump"
                }
                
                self.jumps_detected.append(jump_info)
                self.current_phase = JumpPhase.STANDING
                self.takeoff_time = None
                self.min_y = None
                return jump_info

        return None
