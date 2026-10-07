"""Pytest configuration and test fixtures for Sports Analyzer AI."""
import pytest
import numpy as np


@pytest.fixture
def dummy_frame():
    """Returns a dummy blank 1280x720 RGB frame for testing."""
    return np.zeros((720, 1280, 3), dtype=np.uint8)


@pytest.fixture
def sample_detection():
    """Returns sample player bounding box detection."""
    from backend.app.vision.detector import Detection
    return Detection(
        box=[100.0, 100.0, 200.0, 300.0],
        confidence=0.85,
        class_id=0,
        class_name="person"
    )
