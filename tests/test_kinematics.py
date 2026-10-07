"""Unit tests for PlayerKinematics and KinematicsEngine."""
import pytest
from backend.app.analytics.kinematics import PlayerKinematics, KinematicsEngine, MovementState
from backend.app.vision.detector import Detection


def test_player_kinematics_linear_motion():
    """Test constant velocity movement metrics."""
    kin = PlayerKinematics(player_id=1, pixels_to_meters=0.02)
    
    # 10 frames moving right at 15 px/frame (0.3m/frame at dt=0.033s -> ~9.0 m/s)
    for i in range(10):
        t = i * 0.033
        snapshot = kin.update(center_x=float(i * 15), center_y=100.0, timestamp=t)

    assert snapshot.instant_speed_mps > 0
    assert snapshot.avg_speed_mps > 0
    assert snapshot.total_distance_m > 0
    assert snapshot.movement_state in ["running", "sprinting"]


def test_player_kinematics_direction_change():
    """Test sharp reversal triggers direction change count."""
    kin = PlayerKinematics(player_id=2, pixels_to_meters=0.02)
    
    # Move right for 5 frames
    for i in range(5):
        kin.update(center_x=float(i * 10), center_y=100.0, timestamp=i * 0.033)
        
    # Reversal: move left
    for i in range(1, 5):
        snapshot = kin.update(center_x=float(40 - i * 10), center_y=100.0, timestamp=(4 + i) * 0.033)
        
    assert snapshot.direction_changes >= 1


def test_kinematics_engine_batch_update():
    """Test KinematicsEngine updating multiple player tracks."""
    engine = KinematicsEngine(pixels_to_meters=0.02)
    
    tracks = [
        Detection(box=[100.0, 100.0, 150.0, 200.0], confidence=0.9),
        Detection(box=[300.0, 100.0, 350.0, 200.0], confidence=0.9)
    ]
    
    # Frame 1
    engine.update(tracks, timestamp=0.0)
    # Frame 2
    tracks_f2 = [
        Detection(box=[110.0, 100.0, 160.0, 200.0], confidence=0.9),
        Detection(box=[310.0, 100.0, 360.0, 200.0], confidence=0.9)
    ]
    snapshots = engine.update(tracks_f2, timestamp=0.033)
    
    assert len(snapshots) >= 1
