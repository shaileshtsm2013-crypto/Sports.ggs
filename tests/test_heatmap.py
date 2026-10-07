"""Unit tests for heatmap generation and tactical court rendering."""
import numpy as np
import pytest
from backend.app.analytics.heatmap import (
    generate_court_heatmap,
    generate_topdown_court_heatmap,
    heatmap_to_base64_png
)
from backend.app.sports.court_renderer import CourtRenderer


def test_court_renderer_layouts():
    """Test court base layout rendering for Volleyball, Kabaddi, and Kho Kho."""
    for sport in ["volleyball", "kabaddi", "kho_kho"]:
        renderer = CourtRenderer(sport=sport, canvas_width=600, canvas_height=320)
        img = renderer.render_court_base()
        assert img.shape == (320, 600, 3)
        assert img.dtype == np.uint8

        # Test tactical view with player dots
        tactical = renderer.render_tactical_view([
            {"player_id": 1, "x_m": 4.5, "y_m": 4.5, "team": "Team A", "speed": 3.2},
            {"player_id": 2, "x_m": 12.0, "y_m": 5.0, "team": "Team B", "speed": 1.5}
        ])
        assert tactical.shape == (320, 600, 3)

        b64 = renderer.to_base64_png(tactical)
        assert b64.startswith("data:image/png;base64,")


def test_topdown_heatmap_generation():
    """Test generating top-down 2D court heatmap from metric trajectory points."""
    metric_pts = [(4.0, 4.0), (4.5, 4.2), (5.0, 4.5), (9.0, 4.5), (9.5, 5.0)]
    heatmap_img = generate_topdown_court_heatmap(metric_pts, sport="volleyball", canvas_width=600, canvas_height=320)
    assert heatmap_img.shape == (320, 600, 3)

    b64 = heatmap_to_base64_png(heatmap_img)
    assert b64.startswith("data:image/png;base64,")


def test_empty_heatmap_handling():
    """Verify empty coordinate list generates base court without errors."""
    heatmap_img = generate_topdown_court_heatmap([], sport="volleyball")
    assert heatmap_img is not None
    assert len(heatmap_img.shape) == 3
