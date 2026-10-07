"""Unit tests for the 17-keypoint PoseEstimator module."""
import numpy as np
import pytest
from backend.app.vision.pose import PoseEstimator, Keypoint, PoseResult, COCO_KEYPOINTS, SKELETON_CONNECTIONS
from backend.app.vision.detector import Detection


def test_keypoint_properties():
    """Test Keypoint serialization and normalization."""
    kpt = Keypoint(name="nose", x=640.0, y=360.0, norm_x=0.5, norm_y=0.5, confidence=0.92)
    d = kpt.to_dict()
    assert d["name"] == "nose"
    assert d["x"] == 640.0
    assert d["y"] == 360.0
    assert d["confidence"] == 0.92


def test_skeleton_connections_validity():
    """Verify all skeleton connections reference valid COCO keypoints."""
    keypoint_set = set(COCO_KEYPOINTS)
    assert len(COCO_KEYPOINTS) == 17
    for k1, k2 in SKELETON_CONNECTIONS:
        assert k1 in keypoint_set, f"Unknown keypoint {k1} in connection"
        assert k2 in keypoint_set, f"Unknown keypoint {k2} in connection"


def test_pose_estimator_fallback(dummy_frame):
    """Test fallback heuristic pose estimator constructs all 17 landmarks."""
    estimator = PoseEstimator(use_fallback_only=True)
    
    det = Detection(box=[100.0, 100.0, 200.0, 300.0], confidence=0.85)
    poses = estimator.estimate(dummy_frame, [det])
    
    assert len(poses) == 1
    pose = poses[0]
    assert len(pose.keypoints) == 17
    assert "left_shoulder" in pose.keypoints
    assert "right_ankle" in pose.keypoints
    assert pose.get_keypoint("nose") is not None
    
    # Test drawing skeleton onto frame executes cleanly
    annotated = estimator.draw_skeleton(dummy_frame.copy(), pose)
    assert annotated.shape == dummy_frame.shape
