"""Unit tests for the PlayerTracker Kalman and Hungarian tracking module."""
import pytest
from backend.app.vision.tracker import PlayerTracker, compute_iou, TrackState
from backend.app.vision.detector import Detection


def test_compute_iou():
    """Test IoU calculation for overlapping and disjoint boxes."""
    box_a = [0, 0, 10, 10]
    box_b = [0, 0, 10, 10]
    assert compute_iou(box_a, box_b) == pytest.approx(1.0)

    box_c = [20, 20, 30, 30]
    assert compute_iou(box_a, box_c) == pytest.approx(0.0)

    box_d = [5, 0, 15, 10]
    # intersection: [5,0,10,10] area = 5*10 = 50. Union = 100+100-50 = 150. IoU = 50/150 = 1/3
    assert compute_iou(box_a, box_d) == pytest.approx(1.0 / 3.0)


def test_tracker_lifecycle():
    """Test track creation, hit counting, and confirmation."""
    tracker = PlayerTracker(max_age=5, min_hits=2)
    
    # Frame 1: new detection creates tentative track
    det1 = Detection(box=[100.0, 100.0, 150.0, 200.0], confidence=0.85)
    tracks_f1 = tracker.update([det1])
    # With min_hits=2, it may not be confirmed yet or tentative
    all_tracks = tracker.get_all_tracks()
    assert len(all_tracks) == 1
    track_id = all_tracks[0].track_id

    # Frame 2: consecutive detection updates and confirms track
    det2 = Detection(box=[102.0, 101.0, 152.0, 201.0], confidence=0.88)
    tracks_f2 = tracker.update([det2])
    assert len(tracks_f2) == 1
    assert tracks_f2[0].track_id == track_id
    assert tracks_f2[0].state == TrackState.CONFIRMED
