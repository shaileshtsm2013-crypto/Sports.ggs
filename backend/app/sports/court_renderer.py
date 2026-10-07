"""Top-Down 2D Tactical Court Renderer — projects player positions onto vector court diagrams."""
import io
import base64
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
import cv2

from backend.app.vision.calibration import COURT_METRIC_DIMENSIONS


class CourtRenderer:
    """
    Renders high-resolution 2D bird's-eye tactical court layouts
    and plots athlete positions onto court coordinates.
    """

    def __init__(self, sport: str = "volleyball", canvas_width: int = 900, canvas_height: int = 480):
        self.sport = sport.lower()
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.padding = 40

        self.dims = COURT_METRIC_DIMENSIONS.get(self.sport, {"length": 18.0, "width": 9.0})
        self.court_len = self.dims["length"]
        self.court_wid = self.dims["width"]

        # Scaling factors
        self.draw_w = canvas_width - 2 * self.padding
        self.draw_h = canvas_height - 2 * self.padding
        self.scale_x = self.draw_w / self.court_len
        self.scale_y = self.draw_h / self.court_wid

    def metric_to_canvas(self, xm: float, ym: float) -> Tuple[int, int]:
        """Converts metric court meters (X, Y) to canvas pixels (cx, cy)."""
        cx = int(self.padding + xm * self.scale_x)
        cy = int(self.padding + ym * self.scale_y)
        cx = max(10, min(self.canvas_width - 10, cx))
        cy = max(10, min(self.canvas_height - 10, cy))
        return cx, cy

    def render_court_base(self) -> np.ndarray:
        """Draws the clean vector 2D court layout according to official regulations."""
        # Dark athletic background
        img = np.full((self.canvas_height, self.canvas_width, 3), (25, 30, 40), dtype=np.uint8)

        # Court surface
        x1, y1 = self.metric_to_canvas(0.0, 0.0)
        x2, y2 = self.metric_to_canvas(self.court_len, self.court_wid)

        if self.sport == "volleyball":
            # Amber wooden floor
            cv2.rectangle(img, (x1, y1), (x2, y2), (40, 75, 140), -1)
            cv2.rectangle(img, (x1, y1), (x2, y2), (240, 240, 240), 2)

            # Net line (9m - center)
            nx, _ = self.metric_to_canvas(9.0, 0.0)
            cv2.line(img, (nx, y1), (nx, y2), (0, 220, 255), 3)

            # Attack lines (3m from net: 6m and 12m)
            ax1, _ = self.metric_to_canvas(6.0, 0.0)
            ax2, _ = self.metric_to_canvas(12.0, 0.0)
            cv2.line(img, (ax1, y1), (ax1, y2), (220, 220, 220), 2)
            cv2.line(img, (ax2, y1), (ax2, y2), (220, 220, 220), 2)

            # Team Zone Labels
            cv2.putText(img, "TEAM A (LEFT)", (x1 + 30, y1 - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 180, 200), 1, cv2.LINE_AA)
            cv2.putText(img, "TEAM B (RIGHT)", (x2 - 130, y1 - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 180, 200), 1, cv2.LINE_AA)

        elif self.sport == "kabaddi":
            # Matted green surface
            cv2.rectangle(img, (x1, y1), (x2, y2), (45, 80, 50), -1)
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), 2)

            # Midline (6.5m)
            mx, _ = self.metric_to_canvas(6.5, 0.0)
            cv2.line(img, (mx, y1), (mx, y2), (0, 255, 255), 3)

            # Baulk lines (3.75m from midline: 2.75m and 10.25m)
            bx1, _ = self.metric_to_canvas(2.75, 0.0)
            bx2, _ = self.metric_to_canvas(10.25, 0.0)
            cv2.line(img, (bx1, y1), (bx1, y2), (240, 240, 240), 2)
            cv2.line(img, (bx2, y1), (bx2, y2), (240, 240, 240), 2)

            # Bonus lines (4.75m from midline: 1.75m and 11.25m)
            bonus1, _ = self.metric_to_canvas(1.75, 0.0)
            bonus2, _ = self.metric_to_canvas(11.25, 0.0)
            cv2.line(img, (bonus1, y1), (bonus1, y2), (0, 180, 255), 2)
            cv2.line(img, (bonus2, y1), (bonus2, y2), (0, 180, 255), 2)

        elif self.sport == "kho_kho":
            # Traditional Kho Kho court
            cv2.rectangle(img, (x1, y1), (x2, y2), (50, 70, 70), -1)
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), 2)

            # Central lane (running length-wise between posts)
            cy_mid = int((y1 + y2) / 2)
            cv2.line(img, (x1 + 30, cy_mid), (x2 - 30, cy_mid), (0, 220, 255), 3)

            # Posts at ends
            cv2.circle(img, (x1 + 30, cy_mid), 6, (0, 0, 255), -1)
            cv2.circle(img, (x2 - 30, cy_mid), 6, (0, 0, 255), -1)

            # 8 Cross lanes
            step = (self.court_len - 3.0) / 9.0
            for i in range(1, 9):
                cl_x, _ = self.metric_to_canvas(1.5 + i * step, 0.0)
                cv2.line(img, (cl_x, y1), (cl_x, y2), (200, 200, 200), 1)

        return img

    def render_tactical_view(self, player_positions: List[Dict[str, Any]]) -> np.ndarray:
        """
        Draws the 2D top-down tactical court with all live player dots and ID badges.
        player_positions: list of dicts with keys: 'player_id', 'x_m', 'y_m', 'team', 'speed'
        """
        img = self.render_court_base()

        for p in player_positions:
            xm = float(p.get("x_m", 0.0))
            ym = float(p.get("y_m", 0.0))
            pid = p.get("player_id", 0)
            team = p.get("team", "Team A")
            speed = float(p.get("speed", 0.0))

            cx, cy = self.metric_to_canvas(xm, ym)

            # Color by team or speed
            color = (255, 140, 0) if "A" in str(team).upper() else (0, 200, 255)

            # Player halo & circle
            cv2.circle(img, (cx, cy), 13, (0, 0, 0), -1)
            cv2.circle(img, (cx, cy), 11, color, -1)
            cv2.circle(img, (cx, cy), 12, (255, 255, 255), 1)

            # Player ID number
            id_text = str(pid)
            (tw, th), _ = cv2.getTextSize(id_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.putText(img, id_text, (cx - tw // 2, cy + th // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

            # Speed label above
            if speed > 0.5:
                speed_str = f"{speed:.1f}m/s"
                cv2.putText(img, speed_str, (cx - 16, cy - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 240, 255), 1, cv2.LINE_AA)

        return img

    def to_base64_png(self, img: np.ndarray) -> str:
        """Encodes numpy frame to base64 PNG data URI string."""
        ret, buf = cv2.imencode('.png', img)
        if not ret:
            return ""
        b64 = base64.b64encode(buf).decode('utf-8')
        return f"data:image/png;base64,{b64}"
