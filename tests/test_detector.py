"""Unit tests for the PersonDetector module."""
import numpy as np
import pytest
from backend.app.vision.detector import PersonDetector, Detection


def test_detection_properties():
    """Test Detection box conversion properties."""
    det = Detection(box=[100.0, 100.0, 200.0, 300.0], confidence=0.9, class_id=0, class_name="person")
    assert det.width == 100.0
    assert det.height == 200.0
    assert det.cx == 150.0
    assert det.cy == 200.0
    assert det.area == 20000.0


def test_detector_fallback_detect(dummy_frame):
    """Test detection on blank frame executes without crashing."""
    detector = PersonDetector(confidence_threshold=0.5, use_fallback_only=True)
    detections = detector.detect(dummy_frame)
    assert isinstance(detections, list)
