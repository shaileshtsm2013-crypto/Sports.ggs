"""Human Pose Estimation module — 17-keypoint body landmark tracking and skeleton rendering."""
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
import cv2

logger = logging.getLogger("sports_analyzer.vision.pose")

# Standard 17 COCO keypoint names and indices
COCO_KEYPOINTS = [
    "nose",            # 0
    "left_eye",        # 1
    "right_eye",       # 2
    "left_ear",        # 3
    "right_ear",       # 4
    "left_shoulder",   # 5
    "right_shoulder",  # 6
    "left_elbow",      # 7
    "right_elbow",     # 8
    "left_wrist",      # 9
    "right_wrist",     # 10
    "left_hip",        # 11
    "right_hip",       # 12
    "left_knee",       # 13
    "right_knee",      # 14
    "left_ankle",      # 15
    "right_ankle"      # 16
]

# Limb connection pairs for drawing the human skeleton
SKELETON_CONNECTIONS: List[Tuple[str, str]] = [
    # Head
    ("nose", "left_eye"),
    ("nose", "right_eye"),
    ("left_eye", "left_ear"),
    ("right_eye", "right_ear"),
    # Upper Body
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    # Torso
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    # Lower Body
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle")
]

# Color styling for limb groups (BGR for OpenCV)
LIMB_COLORS = {
    "head": (255, 200, 50),       # Cyan-yellow
    "left_arm": (255, 100, 0),    # Blue
    "right_arm": (0, 165, 255),   # Orange
    "torso": (200, 255, 0),       # Lime green
    "left_leg": (255, 0, 128),    # Purple
    "right_leg": (0, 255, 128)    # Mint green
}


@dataclass
class Keypoint:
    """Represents a single anatomical landmark."""
    name: str
    x: float
    y: float
    norm_x: float
    norm_y: float
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "x": round(self.x, 1),
            "y": round(self.y, 1),
            "norm_x": round(self.norm_x, 4),
            "norm_y": round(self.norm_y, 4),
            "confidence": round(self.confidence, 3)
        }


@dataclass
class PoseResult:
    """Represents full body pose estimation for a tracked athlete."""
    player_id: int
    bbox: Tuple[int, int, int, int]
    keypoints: Dict[str, Keypoint]
    overall_confidence: float

    def get_keypoint(self, name: str) -> Optional[Keypoint]:
        return self.keypoints.get(name)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "bbox": list(self.bbox),
            "overall_confidence": round(self.overall_confidence, 3),
            "keypoints": {k: v.to_dict() for k, v in self.keypoints.items()}
        }


class PoseEstimator:
    """
    Modular Pose Estimator using YOLOv8-Pose with automatic fallback
    to anthropometric heuristic estimation when deep models are unavailable.
    """

    def __init__(
        self,
        model_name: str = "yolov8n-pose.pt",
        confidence_threshold: float = 0.35,
        device: str = "cpu",
        use_fallback_only: bool = False
    ):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.yolo_pose = None
        self.using_fallback = use_fallback_only

        if not use_fallback_only:
            self._init_model()

    def _init_model(self):
        try:
            from ultralytics import YOLO
            logger.info(f"Loading YOLOv8-Pose model: {self.model_name} on {self.device}")
            self.yolo_pose = YOLO(self.model_name)
            self.using_fallback = False
            logger.info("YOLOv8-Pose initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not load YOLOv8-Pose ({e}). Falling back to heuristic pose estimation.")
            self.using_fallback = True

    def estimate(
        self,
        frame: np.ndarray,
        tracks: List[Any]  # List of TrackedPlayer or Detection
    ) -> List[PoseResult]:
        """
        Estimates 17 body landmarks for each tracked player.
        """
        if frame is None or frame.size == 0 or not tracks:
            return []

        h, w = frame.shape[:2]

        if not self.using_fallback and self.yolo_pose is not None:
            try:
                return self._estimate_yolo(frame, tracks, w, h)
            except Exception as e:
                logger.warning(f"YOLO-Pose inference error: {e}. Using fallback.")
                return self._estimate_heuristic(tracks, w, h)
        else:
            return self._estimate_heuristic(tracks, w, h)

    def _estimate_yolo(
        self, frame: np.ndarray, tracks: List[Any], frame_w: int, frame_h: int
    ) -> List[PoseResult]:
        """Runs YOLOv8-Pose batch inference."""
        results = self.yolo_pose.predict(
            source=frame,
            conf=self.confidence_threshold,
            verbose=False,
            device=self.device
        )

        pose_results: List[PoseResult] = []
        if not results or len(results) == 0:
            return self._estimate_heuristic(tracks, frame_w, frame_h)

        r = results[0]
        if r.keypoints is None or len(r.keypoints) == 0:
            return self._estimate_heuristic(tracks, frame_w, frame_h)

        kpts_data = r.keypoints.data.cpu().numpy()  # [N, 17, 3] (x, y, conf)
        boxes_data = r.boxes.xyxy.cpu().numpy() if r.boxes is not None else []

        # Match detected poses to our persistent track IDs by bounding box overlap
        for trk in tracks:
            trk_id = getattr(trk, "player_id", getattr(trk, "track_id", 0))
            trk_box = getattr(trk, "bbox", getattr(trk, "box", (0, 0, 0, 0)))

            best_match_idx = -1
            best_iou = 0.2

            for i, pbox in enumerate(boxes_data):
                iou = self._box_iou(trk_box, pbox)
                if iou > best_iou:
                    best_iou = iou
                    best_match_idx = i

            if best_match_idx >= 0 and best_match_idx < len(kpts_data):
                kpts = kpts_data[best_match_idx]
                keypoints_dict: Dict[str, Keypoint] = {}
                confs = []

                for k_idx, name in enumerate(COCO_KEYPOINTS):
                    kx, ky, kconf = float(kpts[k_idx, 0]), float(kpts[k_idx, 1]), float(kpts[k_idx, 2])
                    confs.append(kconf)
                    keypoints_dict[name] = Keypoint(
                        name=name,
                        x=kx,
                        y=ky,
                        norm_x=kx / max(1, frame_w),
                        norm_y=ky / max(1, frame_h),
                        confidence=kconf
                    )

                pose_results.append(PoseResult(
                    player_id=trk_id,
                    bbox=tuple(map(int, trk_box)),
                    keypoints=keypoints_dict,
                    overall_confidence=float(np.mean(confs)) if confs else 0.0
                ))
            else:
                # If deep pose didn't find this player, generate heuristic landmarks
                fallback_pose = self._generate_heuristic_pose(trk_id, trk_box, frame_w, frame_h)
                pose_results.append(fallback_pose)

        return pose_results

    def _estimate_heuristic(
        self, tracks: List[Any], frame_w: int, frame_h: int
    ) -> List[PoseResult]:
        """Generates anthropometrically sound body landmarks from bounding box dimensions."""
        poses: List[PoseResult] = []
        for trk in tracks:
            trk_id = getattr(trk, "player_id", getattr(trk, "track_id", 0))
            trk_box = getattr(trk, "bbox", getattr(trk, "box", (0, 0, 0, 0)))
            poses.append(self._generate_heuristic_pose(trk_id, trk_box, frame_w, frame_h))
        return poses

    def _generate_heuristic_pose(
        self, player_id: int, box: Tuple[int, int, int, int], frame_w: int, frame_h: int
    ) -> PoseResult:
        """
        Constructs standard 17-keypoint skeleton using human body proportions:
        Head: 0-15%, Shoulders: 20%, Elbows: 35%, Wrists: 48%, Hips: 52%, Knees: 75%, Ankles: 96%
        """
        x1, y1, x2, y2 = box
        w = max(10, x2 - x1)
        h = max(20, y2 - y1)
        cx = (x1 + x2) / 2.0

        # Heuristic anatomical proportions
        kpt_coords = {
            "nose": (cx, y1 + h * 0.08),
            "left_eye": (cx - w * 0.10, y1 + h * 0.06),
            "right_eye": (cx + w * 0.10, y1 + h * 0.06),
            "left_ear": (cx - w * 0.20, y1 + h * 0.08),
            "right_ear": (cx + w * 0.20, y1 + h * 0.08),
            "left_shoulder": (cx - w * 0.35, y1 + h * 0.20),
            "right_shoulder": (cx + w * 0.35, y1 + h * 0.20),
            "left_elbow": (cx - w * 0.42, y1 + h * 0.36),
            "right_elbow": (cx + w * 0.42, y1 + h * 0.36),
            "left_wrist": (cx - w * 0.38, y1 + h * 0.50),
            "right_wrist": (cx + w * 0.38, y1 + h * 0.50),
            "left_hip": (cx - w * 0.22, y1 + h * 0.53),
            "right_hip": (cx + w * 0.22, y1 + h * 0.53),
            "left_knee": (cx - w * 0.24, y1 + h * 0.75),
            "right_knee": (cx + w * 0.24, y1 + h * 0.75),
            "left_ankle": (cx - w * 0.25, y1 + h * 0.96),
            "right_ankle": (cx + w * 0.25, y1 + h * 0.96),
        }

        keypoints: Dict[str, Keypoint] = {}
        for name, (px, py) in kpt_coords.items():
            keypoints[name] = Keypoint(
                name=name,
                x=round(px, 1),
                y=round(py, 1),
                norm_x=round(px / max(1, frame_w), 4),
                norm_y=round(py / max(1, frame_h), 4),
                confidence=0.75
            )

        return PoseResult(
            player_id=player_id,
            bbox=tuple(map(int, box)),
            keypoints=keypoints,
            overall_confidence=0.75
        )

    def draw_skeleton(self, frame: np.ndarray, pose: PoseResult, line_thickness: int = 2) -> np.ndarray:
        """
        Draws skeleton bones and keypoint joints on the frame.
        """
        if frame is None or pose is None:
            return frame

        # Draw limb connections
        for p1_name, p2_name in SKELETON_CONNECTIONS:
            pt1 = pose.get_keypoint(p1_name)
            pt2 = pose.get_keypoint(p2_name)

            if pt1 and pt2 and pt1.confidence >= self.confidence_threshold and pt2.confidence >= self.confidence_threshold:
                c1 = (int(pt1.x), int(pt1.y))
                c2 = (int(pt2.x), int(pt2.y))
                cv2.line(frame, c1, c2, (0, 255, 200), line_thickness, cv2.LINE_AA)

        # Draw joint nodes
        for kpt in pose.keypoints.values():
            if kpt.confidence >= self.confidence_threshold:
                cx, cy = int(kpt.x), int(kpt.y)
                cv2.circle(frame, (cx, cy), 3, (255, 0, 128), -1, cv2.LINE_AA)
                cv2.circle(frame, (cx, cy), 4, (255, 255, 255), 1, cv2.LINE_AA)

        return frame

    @staticmethod
    def _box_iou(box1: Any, box2: Any) -> float:
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter
        return inter / max(1e-5, union)
