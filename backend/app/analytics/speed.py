import math
from typing import List, Tuple, Dict, Any
import numpy as np


def compute_speed_and_acceleration(
    timed_points: List[Tuple[float, float, float]],  # (x, y, timestamp)
    pixels_to_meters: float = 0.02
) -> Dict[str, Any]:
    """
    Computes instantaneous, average, maximum speed (m/s) and acceleration (m/s^2).
    """
    if len(timed_points) < 2:
        return {
            "instant_speed_mps": 0.0,
            "avg_speed_mps": 0.0,
            "max_speed_mps": 0.0,
            "max_accel_mps2": 0.0
        }

    speeds: List[float] = []
    
    for i in range(1, len(timed_points)):
        p1 = timed_points[i - 1]
        p2 = timed_points[i]
        dt = p2[2] - p1[2]
        
        if dt > 0.001:
            dist_px = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            dist_m = dist_px * pixels_to_meters
            speed = dist_m / dt
            # Cap unrealistic speed spikes from vision noise
            if speed < 12.0:  # Bolt-speed limit
                speeds.append(speed)

    if not speeds:
        return {
            "instant_speed_mps": 0.0,
            "avg_speed_mps": 0.0,
            "max_speed_mps": 0.0,
            "max_accel_mps2": 0.0
        }

    instant_speed = speeds[-1]
    avg_speed = float(np.mean(speeds))
    max_speed = float(np.max(speeds))

    # Accelerations
    accels: List[float] = []
    for i in range(1, len(speeds)):
        dt = timed_points[i + 1][2] - timed_points[i][2]
        if dt > 0.001:
            dv = speeds[i] - speeds[i - 1]
            accel = dv / dt
            if abs(accel) < 15.0:
                accels.append(abs(accel))

    max_accel = float(np.max(accels)) if accels else 0.0

    return {
        "instant_speed_mps": round(instant_speed, 2),
        "avg_speed_mps": round(avg_speed, 2),
        "max_speed_mps": round(max_speed, 2),
        "max_accel_mps2": round(max_accel, 2)
    }
