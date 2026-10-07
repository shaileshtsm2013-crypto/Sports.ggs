"""Unit tests for the CourtCalibrator and homography perspective transformation."""
import os
import tempfile
import pytest
from backend.app.vision.calibration import CourtCalibrator, COURT_METRIC_DIMENSIONS


def test_calibrator_initialization():
    """Verify court dimensions are correctly loaded for all supported sports."""
    vb_calib = CourtCalibrator(sport="volleyball")
    assert vb_calib.get_court_dimensions()["length"] == 18.0
    assert vb_calib.get_court_dimensions()["width"] == 9.0

    kb_calib = CourtCalibrator(sport="kabaddi")
    assert kb_calib.get_court_dimensions()["length"] == 13.0
    assert kb_calib.get_court_dimensions()["width"] == 10.0

    kk_calib = CourtCalibrator(sport="kho_kho")
    assert kk_calib.get_court_dimensions()["length"] == 27.0
    assert kk_calib.get_court_dimensions()["width"] == 16.0


def test_homography_and_coordinate_transforms():
    """Test 4-corner homography calculation and bidirectional point mapping."""
    calib = CourtCalibrator(sport="volleyball")

    # Image quad: [TL, TR, BR, BL]
    image_corners = [
        (100.0, 100.0),
        (1100.0, 100.0),
        (1100.0, 600.0),
        (100.0, 600.0)
    ]

    success = calib.set_calibration_corners(image_corners)
    assert success is True
    assert calib.is_calibrated is True

    # Check that image corners map accurately to world metric corners
    # TL (100, 100) -> (0, 0)
    xm_tl, ym_tl = calib.image_to_court(100.0, 100.0)
    assert xm_tl == pytest.approx(0.0, abs=0.1)
    assert ym_tl == pytest.approx(0.0, abs=0.1)

    # TR (1100, 100) -> (18, 0)
    xm_tr, ym_tr = calib.image_to_court(1100.0, 100.0)
    assert xm_tr == pytest.approx(18.0, abs=0.1)
    assert ym_tr == pytest.approx(0.0, abs=0.1)

    # BR (1100, 600) -> (18, 9)
    xm_br, ym_br = calib.image_to_court(1100.0, 600.0)
    assert xm_br == pytest.approx(18.0, abs=0.1)
    assert ym_br == pytest.approx(9.0, abs=0.1)

    # Cycle consistency: court_to_image of (18, 9) should return (1100, 600)
    u, v = calib.court_to_image(18.0, 9.0)
    assert u == pytest.approx(1100.0, abs=1.0)
    assert v == pytest.approx(600.0, abs=1.0)


def test_calibration_save_and_load(tmp_path):
    """Test JSON persistence for calibration configurations."""
    calib = CourtCalibrator(sport="volleyball")
    image_corners = [(100.0, 100.0), (1000.0, 100.0), (1000.0, 500.0), (100.0, 500.0)]
    calib.set_calibration_corners(image_corners)

    save_path = str(tmp_path / "test_calibration_volleyball.json")
    assert calib.save_calibration(save_path) is True

    # Load in new instance
    new_calib = CourtCalibrator(sport="volleyball")
    assert new_calib.load_calibration(save_path) is True
    assert new_calib.is_calibrated is True
    assert new_calib.image_corners == image_corners
