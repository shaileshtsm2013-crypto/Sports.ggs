"""Biomechanical Heatmap module — 2D Gaussian density calculation on court & camera perspectives."""
import io
import base64
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import cv2

from backend.app.sports.court_renderer import CourtRenderer


def generate_court_heatmap(
    points: List[Tuple[float, float]],
    width: int = 640,
    height: int = 360,
    sigma: int = 15
) -> np.ndarray:
    """
    Generates a 2D Gaussian density heatmap from a list of (x, y) coordinate points.
    Returns a colorized BGR image.
    """
    heatmap = np.zeros((height, width), dtype=np.float32)

    for pt in points:
        x = int(pt[0])
        y = int(pt[1])
        if 0 <= x < width and 0 <= y < height:
            heatmap[y, x] += 1.0

    if np.max(heatmap) > 0:
        ksize = sigma * 4 + 1
        heatmap = cv2.GaussianBlur(heatmap, (ksize, ksize), sigma)
        heatmap = (heatmap / np.max(heatmap) * 255).astype(np.uint8)
    else:
        heatmap = heatmap.astype(np.uint8)

    color_heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    return color_heatmap


def generate_topdown_court_heatmap(
    metric_points: List[Tuple[float, float]],
    sport: str = "volleyball",
    canvas_width: int = 900,
    canvas_height: int = 480,
    sigma: int = 22,
    alpha: float = 0.55
) -> np.ndarray:
    """
    Projects metric court positions (X_m, Y_m) onto the 2D vector court layout
    and blends a smooth Gaussian density heatmap over the sport court.
    """
    renderer = CourtRenderer(sport=sport, canvas_width=canvas_width, canvas_height=canvas_height)
    base_court = renderer.render_court_base()

    # Convert metric coordinates to canvas pixels
    canvas_pts: List[Tuple[int, int]] = []
    for xm, ym in metric_points:
        cx, cy = renderer.metric_to_canvas(xm, ym)
        canvas_pts.append((cx, cy))

    if not canvas_pts:
        return base_court

    density = np.zeros((canvas_height, canvas_width), dtype=np.float32)
    for cx, cy in canvas_pts:
        if 0 <= cx < canvas_width and 0 <= cy < canvas_height:
            density[cy, cx] += 1.0

    if np.max(density) > 0:
        ksize = sigma * 4 + 1
        density = cv2.GaussianBlur(density, (ksize, ksize), sigma)
        norm_density = (density / np.max(density) * 255).astype(np.uint8)

        # Apply JET color map
        color_map = cv2.applyColorMap(norm_density, cv2.COLORMAP_JET)

        # Mask low-density regions to keep court lines crisp and clean
        mask = norm_density > 20
        blended = base_court.copy()
        blended[mask] = cv2.addWeighted(base_court, 1.0 - alpha, color_map, alpha, 0)[mask]
        return blended
    else:
        return base_court


def heatmap_to_base64_png(heatmap_img: np.ndarray) -> str:
    """Encodes heatmap image to base64 PNG data URI string."""
    ret, png_bytes = cv2.imencode('.png', heatmap_img)
    if not ret:
        return ""
    b64 = base64.b64encode(png_bytes).decode('utf-8')
    return f"data:image/png;base64,{b64}"
