import math
from typing import List, Tuple, Dict, Any
import numpy as np


def smooth_trajectory(points: List[Tuple[float, float]], window_size: int = 5) -> List[Tuple[float, float]]:
    """Applies moving average filter to smooth jittery vision coordinates."""
    if len(points) < window_size:
        return points

    arr = np.array(points)
    smoothed = np.zeros_like(arr)
    
    for i in range(len(arr)):
        start_idx = max(0, i - window_size // 2)
        end_idx = min(len(arr), i + window_size // 2 + 1)
        smoothed[i] = np.mean(arr[start_idx:end_idx], axis=0)

    return [(float(pt[0]), float(pt[1])) for pt in smoothed]


def calculate_cumulative_distance(points: List[Tuple[float, float]], pixels_to_meters: float = 0.02) -> float:
    """Calculates total distance traveled in meters from a list of coordinate points."""
    if len(points) < 2:
        return 0.0

    total_px = 0.0
    for i in range(1, len(points)):
        dx = points[i][0] - points[i - 1][0]
        dy = points[i][1] - points[i - 1][1]
        dist = math.hypot(dx, dy)
        if dist < 200:  # Ignore unnatural tracking teleports
            total_px += dist

    return round(total_px * pixels_to_meters, 2)


def count_direction_changes(points: List[Tuple[float, float]], angle_threshold_deg: float = 60.0) -> int:
    """Counts significant changes in movement direction (> angle_threshold_deg)."""
    if len(points) < 3:
        return 0

    changes = 0
    thresh_rad = math.radians(angle_threshold_deg)

    for i in range(1, len(points) - 1):
        v1 = (points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1])
        v2 = (points[i + 1][0] - points[i][0], points[i + 1][1] - points[i][1])

        mag1 = math.hypot(v1[0], v1[1])
        mag2 = math.hypot(v2[0], v2[1])

        if mag1 > 3.0 and mag2 > 3.0:  # Ignore micro-jitters
            dot = v1[0] * v2[0] + v1[1] * v2[1]
            cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
            angle = math.acos(cos_angle)
            if angle > thresh_rad:
                changes += 1

    return changes
