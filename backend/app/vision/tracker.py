import enum
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from scipy.optimize import linear_sum_assignment

from backend.app.vision.detector import Detection


class TrackState(enum.Enum):
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    LOST = "lost"
    DELETED = "deleted"


class KalmanBoxTracker:
    """
    Kalman Filter for tracking bounding boxes in image space.
    State vector: [x_center, y_center, area, aspect_ratio, vx, vy, va, vh]
    """
    count = 0

    def __init__(self, bbox: Tuple[int, int, int, int], confidence: float = 0.8):
        # State: [cx, cy, s (area), r (aspect ratio)]
        self.kf_dim_z = 4
        self.kf_dim_x = 8

        # Initialize state mean
        self.x = np.zeros((self.kf_dim_x, 1))
        x1, y1, x2, y2 = bbox
        w = max(1.0, float(x2 - x1))
        h = max(1.0, float(y2 - y1))
        self.x[0] = x1 + w / 2.0
        self.x[1] = y1 + h / 2.0
        self.x[2] = w * h
        self.x[3] = w / h

        # State transition matrix F
        self.F = np.eye(self.kf_dim_x)
        for i in range(4):
            self.F[i, i + 4] = 1.0

        # Measurement matrix H
        self.H = np.eye(self.kf_dim_z, self.kf_dim_x)

        # Covariance matrices
        self.P = np.eye(self.kf_dim_x) * 10.0
        self.P[4:, 4:] *= 100.0  # High uncertainty in initial velocities

        self.Q = np.eye(self.kf_dim_x) * 1.0
        self.Q[4:, 4:] *= 0.01

        self.R = np.eye(self.kf_dim_z) * 1.0
        self.R[2:, 2:] *= 10.0

        self.confidence = confidence
        self.time_since_update = 0
        KalmanBoxTracker.count += 1
        self.id = KalmanBoxTracker.count
        self.history: List[Tuple[int, int, int, int]] = []
        self.hits = 1
        self.hit_streak = 1
        self.age = 0

    def update(self, bbox: Tuple[int, int, int, int], confidence: float):
        self.time_since_update = 0
        self.history = []
        self.hits += 1
        self.hit_streak += 1
        self.confidence = 0.8 * self.confidence + 0.2 * confidence

        x1, y1, x2, y2 = bbox
        w = max(1.0, float(x2 - x1))
        h = max(1.0, float(y2 - y1))
        z = np.array([[x1 + w / 2.0], [y1 + h / 2.0], [w * h], [w / h]])

        # Kalman measurement update
        y = z - np.dot(self.H, self.x)
        S = np.dot(self.H, np.dot(self.P, self.H.T)) + self.R
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))
        self.x = self.x + np.dot(K, y)
        self.P = np.dot(np.eye(self.kf_dim_x) - np.dot(K, self.H), self.P)

    def predict(self) -> Tuple[int, int, int, int]:
        if (self.x[6] + self.x[2]) <= 0:
            self.x[6] *= 0.0
            
        self.x = np.dot(self.F, self.x)
        self.P = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q
        self.age += 1
        if self.time_since_update > 0:
            self.hit_streak = 0
        self.time_since_update += 1
        
        box = self.get_state()
        self.history.append(box)
        return box

    def get_state(self) -> Tuple[int, int, int, int]:
        """Convert bounding box state [cx, cy, s, r] to [x1, y1, x2, y2]."""
        cx = float(self.x[0, 0])
        cy = float(self.x[1, 0])
        s = max(1.0, float(self.x[2, 0]))
        r = max(0.1, float(self.x[3, 0]))
        
        w = np.sqrt(s * r)
        h = s / w
        x1 = int(cx - w / 2.0)
        y1 = int(cy - h / 2.0)
        x2 = int(cx + w / 2.0)
        y2 = int(cy + h / 2.0)
        return (x1, y1, x2, y2)

    def get_velocity(self) -> Tuple[float, float]:
        """Returns instantaneous velocity vector (vx, vy) in pixels/frame."""
        return (float(self.x[4, 0]), float(self.x[5, 0]))


@dataclass
class TrackedPlayer:
    """Represents a consistently identified player with trajectory and state."""
    player_id: int
    bbox: Tuple[int, int, int, int]
    confidence: float
    state: TrackState = TrackState.CONFIRMED
    trail: deque = field(default_factory=lambda: deque(maxlen=60))  # [(cx, cy, timestamp)]
    velocity: Tuple[float, float] = (0.0, 0.0)
    total_distance_px: float = 0.0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    jersey_number: Optional[str] = None
    team: str = "Team A"

    @property
    def centroid(self) -> Tuple[float, float]:
        return ((self.bbox[0] + self.bbox[2]) / 2.0, (self.bbox[1] + self.bbox[3]) / 2.0)

    @property
    def track_id(self) -> int:
        return self.player_id

    def to_dict(self, frame_w: int = 1, frame_h: int = 1) -> Dict[str, Any]:
        cx, cy = self.centroid
        norm_trail = [
            {"x": round(pt[0] / max(1, frame_w), 4), "y": round(pt[1] / max(1, frame_h), 4)}
            for pt in self.trail
        ]
        return {
            "player_id": self.player_id,
            "bounding_box": {
                "x1": int(self.bbox[0]),
                "y1": int(self.bbox[1]),
                "x2": int(self.bbox[2]),
                "y2": int(self.bbox[3]),
                "norm_x1": round(self.bbox[0] / max(1, frame_w), 4),
                "norm_y1": round(self.bbox[1] / max(1, frame_h), 4),
                "norm_x2": round(self.bbox[2] / max(1, frame_w), 4),
                "norm_y2": round(self.bbox[3] / max(1, frame_h), 4),
            },
            "confidence": round(float(self.confidence), 3),
            "position": {"x": round(cx, 1), "y": round(cy, 1)},
            "velocity": {"vx": round(self.velocity[0], 2), "vy": round(self.velocity[1], 2)},
            "speed_px_per_frame": round(float(np.hypot(self.velocity[0], self.velocity[1])), 2),
            "state": self.state.value,
            "trail": norm_trail,
            "total_distance_px": round(self.total_distance_px, 1),
            "jersey_number": self.jersey_number,
            "team": self.team
        }


def compute_iou(bb_test: Tuple[int, int, int, int], bb_gt: Tuple[int, int, int, int]) -> float:
    """Computes Intersection over Union (IoU) between two bounding boxes."""
    xx1 = max(bb_test[0], bb_gt[0])
    yy1 = max(bb_test[1], bb_gt[1])
    xx2 = min(bb_test[2], bb_gt[2])
    yy2 = min(bb_test[3], bb_gt[3])
    
    w = max(0.0, float(xx2 - xx1))
    h = max(0.0, float(yy2 - yy1))
    intersection = w * h
    
    area_test = (bb_test[2] - bb_test[0]) * (bb_test[3] - bb_test[1])
    area_gt = (bb_gt[2] - bb_gt[0]) * (bb_gt[3] - bb_gt[1])
    union = float(area_test + area_gt - intersection)
    
    return intersection / union if union > 0 else 0.0


class PlayerTracker:
    """
    Multi-Object Player Tracker with Kalman state prediction,
    IoU distance association, occlusion survival, and trajectory history.
    """

    def __init__(
        self,
        max_age: int = 30,
        min_hits: int = 2,
        iou_threshold: float = 0.30,
        max_trail_len: int = 60
    ):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.max_trail_len = max_trail_len
        
        self.trackers: List[KalmanBoxTracker] = []
        self.player_trails: Dict[int, deque] = {}
        self.player_distances: Dict[int, float] = {}
        self.frame_count = 0

    def update(self, detections: List[Detection], timestamp: float = 0.0) -> List[TrackedPlayer]:
        """
        Updates the tracker with detections from the current frame.
        Returns a list of currently active, confirmed TrackedPlayer instances.
        """
        self.frame_count += 1
        
        # 1. Get predicted locations from existing trackers
        predicted_boxes = []
        to_del = []
        for i, trk in enumerate(self.trackers):
            pos = trk.predict()
            if np.any(np.isnan(pos)):
                to_del.append(i)
            else:
                predicted_boxes.append(pos)
                
        for i in reversed(to_del):
            self.trackers.pop(i)

        # 2. Match detections with predicted tracks
        matched_indices, unmatched_dets, unmatched_trks = self._associate_detections_to_trackers(
            detections, predicted_boxes
        )

        # 3. Update matched trackers
        for trk_idx, det_idx in matched_indices:
            det = detections[det_idx]
            self.trackers[trk_idx].update(det.box, det.confidence)

        # 4. Create new trackers for unmatched detections
        for det_idx in unmatched_dets:
            det = detections[det_idx]
            trk = KalmanBoxTracker(det.box, det.confidence)
            self.trackers.append(trk)

        # 5. Build output list of confirmed active players & clean up dead tracks
        active_players: List[TrackedPlayer] = []
        remaining_trackers: List[KalmanBoxTracker] = []
        
        current_time = timestamp if timestamp > 0 else time.time()

        for trk in self.trackers:
            box = trk.get_state()
            pid = trk.id

            # Keep tracker if it was updated recently
            if trk.time_since_update <= self.max_age:
                remaining_trackers.append(trk)
                
                # Only return tracks that have enough hits (min_hits)
                if trk.hits >= self.min_hits and trk.time_since_update <= 1:
                    cx = (box[0] + box[2]) / 2.0
                    cy = (box[1] + box[3]) / 2.0
                    
                    if pid not in self.player_trails:
                        self.player_trails[pid] = deque(maxlen=self.max_trail_len)
                        self.player_distances[pid] = 0.0
                    
                    trail = self.player_trails[pid]
                    if len(trail) > 0:
                        last_pt = trail[-1]
                        dist = np.hypot(cx - last_pt[0], cy - last_pt[1])
                        # Filter out crazy teleportation jumps
                        if dist < 300:
                            self.player_distances[pid] += float(dist)
                            
                    trail.append((cx, cy, current_time))
                    
                    vel = trk.get_velocity()
                    
                    player = TrackedPlayer(
                        player_id=pid,
                        bbox=box,
                        confidence=trk.confidence,
                        state=TrackState.CONFIRMED,
                        trail=trail,
                        velocity=vel,
                        total_distance_px=self.player_distances.get(pid, 0.0),
                        last_seen=current_time
                    )
                    active_players.append(player)

        self.trackers = remaining_trackers
        return active_players

    def _associate_detections_to_trackers(
        self, detections: List[Detection], predicted_boxes: List[Tuple[int, int, int, int]]
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Hungarian algorithm matching based on IoU distance."""
        if len(self.trackers) == 0:
            return [], list(range(len(detections))), []

        if len(detections) == 0:
            return [], [], list(range(len(self.trackers)))

        iou_matrix = np.zeros((len(self.trackers), len(detections)), dtype=np.float32)
        for t, trk_box in enumerate(predicted_boxes):
            for d, det in enumerate(detections):
                iou_matrix[t, d] = compute_iou(trk_box, det.box)

        # Cost matrix: 1 - IoU
        cost_matrix = 1.0 - iou_matrix
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        matched_indices = []
        unmatched_dets = list(range(len(detections)))
        unmatched_trks = list(range(len(self.trackers)))

        for r, c in zip(row_ind, col_ind):
            if iou_matrix[r, c] >= self.iou_threshold:
                matched_indices.append((r, c))
                if c in unmatched_dets:
                    unmatched_dets.remove(c)
                if r in unmatched_trks:
                    unmatched_trks.remove(r)

        return matched_indices, unmatched_dets, unmatched_trks

    def get_all_tracks(self) -> List[TrackedPlayer]:
        """Returns all current tracks (confirmed or tentative)."""
        tracks: List[TrackedPlayer] = []
        for trk in self.trackers:
            box = trk.get_state()
            state = TrackState.CONFIRMED if trk.hits >= self.min_hits else TrackState.TENTATIVE
            trail = self.player_trails.get(trk.id, deque())
            tracks.append(TrackedPlayer(
                player_id=trk.id,
                bbox=box,
                confidence=trk.confidence,
                state=state,
                trail=trail,
                velocity=trk.get_velocity(),
                total_distance_px=self.player_distances.get(trk.id, 0.0),
                last_seen=time.time()
            ))
        return tracks
