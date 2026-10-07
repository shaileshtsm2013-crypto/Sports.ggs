import os
import time
import math
import logging
import threading
from typing import Optional, List, Dict, Any, Generator, Tuple
from collections import deque
import numpy as np
import cv2

from backend.app.vision.detector import PersonDetector, Detection
from backend.app.vision.tracker import PlayerTracker, TrackedPlayer
from backend.app.vision.pose import PoseEstimator, PoseResult
from backend.app.vision.calibration import CourtCalibrator
from backend.app.sports.court_renderer import CourtRenderer
from backend.app.sports.volleyball import VolleyballAnalyzer
from backend.app.sports.kabaddi import KabaddiAnalyzer
from backend.app.sports.kho_kho import KhoKhoAnalyzer
from backend.app.analytics.kinematics import KinematicsEngine, KinematicsSnapshot
from backend.app.analytics.heatmap import generate_court_heatmap, generate_topdown_court_heatmap, heatmap_to_base64_png
from backend.app.core.hardware import hardware_manager, PerformanceProfile

logger = logging.getLogger("sports_analyzer.vision.pipeline")



class SyntheticVideoGenerator:
    """
    Generates a realistic synthetic sports court with articulated multi-joint
    player avatars exhibiting running and jumping movements.
    """

    def __init__(self, width: int = 1280, height: int = 720, num_players: int = 6, sport: str = "volleyball"):
        self.width = width
        self.height = height
        self.num_players = num_players
        self.sport = sport
        self.frame_idx = 0
        
        np.random.seed(42)
        self.players = []
        for i in range(num_players):
            self.players.append({
                "id": i + 1,
                "base_x": np.random.uniform(width * 0.2, width * 0.8),
                "base_y": np.random.uniform(height * 0.35, height * 0.75),
                "rad_x": np.random.uniform(70, 190),
                "rad_y": np.random.uniform(30, 90),
                "freq": np.random.uniform(0.02, 0.04),
                "phase": np.random.uniform(0, 2 * math.pi),
                "color": (255, 140, 0) if i % 2 == 0 else (0, 180, 255),
                "height": np.random.randint(100, 140),
                "width": np.random.randint(44, 64),
                "jump_phase": np.random.uniform(0, 100),
                "jump_interval": np.random.randint(60, 120)
            })

    def read(self) -> Tuple[bool, np.ndarray]:
        self.frame_idx += 1
        t = self.frame_idx * 0.033

        # Create court background
        if self.sport == "volleyball":
            frame = np.full((self.height, self.width, 3), (35, 60, 110), dtype=np.uint8)
            court_color = (25, 45, 80)
            line_color = (240, 240, 240)
            cv2.rectangle(frame, (int(self.width * 0.15), int(self.height * 0.2)), 
                          (int(self.width * 0.85), int(self.height * 0.85)), court_color, -1)
            cv2.rectangle(frame, (int(self.width * 0.15), int(self.height * 0.2)), 
                          (int(self.width * 0.85), int(self.height * 0.85)), line_color, 3)
            # Net line
            cv2.line(frame, (int(self.width * 0.5), int(self.height * 0.2)), 
                     (int(self.width * 0.5), int(self.height * 0.85)), (0, 220, 255), 4)
            # Attack lines
            cv2.line(frame, (int(self.width * 0.38), int(self.height * 0.2)), 
                     (int(self.width * 0.38), int(self.height * 0.85)), line_color, 2)
            cv2.line(frame, (int(self.width * 0.62), int(self.height * 0.2)), 
                     (int(self.width * 0.62), int(self.height * 0.85)), line_color, 2)
        else:
            frame = np.full((self.height, self.width, 3), (30, 30, 30), dtype=np.uint8)
            court_color = (40, 75, 40)
            line_color = (255, 255, 255)
            cv2.rectangle(frame, (int(self.width * 0.15), int(self.height * 0.2)), 
                          (int(self.width * 0.85), int(self.height * 0.85)), court_color, -1)
            cv2.rectangle(frame, (int(self.width * 0.15), int(self.height * 0.2)), 
                          (int(self.width * 0.85), int(self.height * 0.85)), line_color, 3)
            cv2.line(frame, (int(self.width * 0.5), int(self.height * 0.2)), 
                     (int(self.width * 0.5), int(self.height * 0.85)), (0, 255, 255), 3)

        # Draw moving human figures with articulated limb motions
        for p in self.players:
            cx = int(p["base_x"] + p["rad_x"] * math.sin(p["freq"] * self.frame_idx + p["phase"]))
            cy_base = p["base_y"] + p["rad_y"] * math.cos(p["freq"] * self.frame_idx * 0.8 + p["phase"])
            
            # Periodic jumping motion
            jump_cycle = (self.frame_idx + p["jump_phase"]) % p["jump_interval"]
            vertical_jump = 0.0
            if jump_cycle < 15:  # Jump duration ~15 frames (0.5s)
                vertical_jump = math.sin((jump_cycle / 15.0) * math.pi) * 45.0

            cy = int(cy_base - vertical_jump)
            pw = p["width"]
            ph = p["height"]

            # Head
            cv2.circle(frame, (cx, cy - int(ph * 0.38)), int(ph * 0.12), (220, 200, 180), -1)
            # Torso (Jersey)
            cv2.rectangle(frame, (cx - int(pw * 0.4), cy - int(ph * 0.25)),
                          (cx + int(pw * 0.4), cy + int(ph * 0.15)), p["color"], -1)
            # Shorts & Legs
            cv2.rectangle(frame, (cx - int(pw * 0.35), cy + int(ph * 0.15)),
                          (cx + int(pw * 0.35), cy + int(ph * 0.48)), (20, 20, 20), -1)
            # Arms running swing
            arm_swing = int(math.sin(self.frame_idx * 0.3 + p["phase"]) * pw * 0.3)
            cv2.line(frame, (cx - int(pw * 0.4), cy - int(ph * 0.2)),
                     (cx - int(pw * 0.45), cy + arm_swing), (220, 200, 180), 4)
            cv2.line(frame, (cx + int(pw * 0.4), cy - int(ph * 0.2)),
                     (cx + int(pw * 0.45), cy - arm_swing), (220, 200, 180), 4)

        return True, frame

    def release(self):
        pass


class VisionPipeline:
    """
    Core video processing pipeline orchestrating capture, detection,
    multi-object tracking, 17-keypoint pose estimation, kinematics analysis,
    annotation rendering, and telemetry streaming.
    """

    def __init__(
        self,
        source: Any = "synthetic",
        sport: str = "volleyball",
        confidence_threshold: float = 0.40,
        model_name: str = "yolov8n.pt",
        enable_pose: bool = True
    ):
        self.source = source
        self.sport = sport
        self.confidence_threshold = confidence_threshold
        self.model_name = model_name
        self.enable_pose = enable_pose

        self.cap = None
        self.is_running = False
        self.is_paused = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Display settings
        self.show_skeleton: bool = True
        self.show_boxes: bool = True
        self.show_trails: bool = True
        self.pixels_to_meters: float = 0.02

        # Performance & Hardware Profile
        self.profile: PerformanceProfile = hardware_manager.active_profile
        self.last_detections: List[Detection] = []
        self.last_poses: List[PoseResult] = []

        # Submodules (using hardware accelerated device: CUDA / DirectML / CPU)
        device = hardware_manager.specs.primary_device
        self.detector = PersonDetector(
            model_name=model_name,
            confidence_threshold=confidence_threshold,
            device=device
        )
        self.tracker = PlayerTracker(
            max_age=30,
            min_hits=2,
            iou_threshold=0.30
        )
        self.pose_estimator = PoseEstimator(
            confidence_threshold=0.35,
            device=device
        )
        self.calibrator = CourtCalibrator(sport=self.sport)
        self.court_renderer = CourtRenderer(sport=self.sport)
        self.kinematics_engine = KinematicsEngine(
            pixels_to_meters=self.pixels_to_meters,
            court_calibrator=self.calibrator
        )
        self.volleyball_analyzer = VolleyballAnalyzer() if self.sport == "volleyball" else None
        self.kabaddi_analyzer = KabaddiAnalyzer() if self.sport == "kabaddi" else None
        self.kho_kho_analyzer = KhoKhoAnalyzer() if self.sport == "kho_kho" else None


        # Telemetry & Output buffers
        self.latest_raw_frame: Optional[np.ndarray] = None
        self.latest_annotated_frame: Optional[np.ndarray] = None
        self.latest_telemetry: Dict[str, Any] = {}
        
        # Performance & FPS tracking
        self.fps_buffer = deque(maxlen=30)
        self.current_fps: float = 0.0
        self.frame_index: int = 0
        self.start_time: float = time.time()
        self.frame_width: int = 1280
        self.frame_height: int = 720

    def start(self):
        """Starts the capture and processing thread."""
        if self.is_running:
            return

        self._init_capture()
        self.is_running = True
        self.is_paused = False
        self.start_time = time.time()
        self.frame_index = 0

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"VisionPipeline started on source: {self.source}")

    def stop(self):
        """Stops the processing pipeline and releases capture."""
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        logger.info("VisionPipeline stopped.")

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def change_source(self, new_source: Any):
        was_running = self.is_running
        self.stop()
        self.source = new_source
        if was_running:
            self.start()

    def set_overlay_options(
        self,
        show_skeleton: Optional[bool] = None,
        show_boxes: Optional[bool] = None,
        show_trails: Optional[bool] = None
    ):
        """Configures visual overlays."""
        if show_skeleton is not None:
            self.show_skeleton = show_skeleton
        if show_boxes is not None:
            self.show_boxes = show_boxes
        if show_trails is not None:
            self.show_trails = show_trails

    def _init_capture(self):
        if self.source == "synthetic" or str(self.source).lower() in ["demo", "synthetic", "mock"]:
            self.cap = SyntheticVideoGenerator(width=1280, height=720, num_players=6, sport=self.sport)
            self.frame_width = 1280
            self.frame_height = 720
        else:
            src = int(self.source) if str(self.source).isdigit() else str(self.source)
            self.cap = cv2.VideoCapture(src)
            if not self.cap.isOpened():
                logger.warning(f"Failed to open source {self.source}. Falling back to synthetic generator.")
                self.cap = SyntheticVideoGenerator(width=1280, height=720, num_players=6, sport=self.sport)
                self.frame_width = 1280
                self.frame_height = 720
            else:
                self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
                self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720

    def _run_loop(self):
        last_time = time.time()

        while self.is_running:
            if self.is_paused:
                time.sleep(0.05)
                continue

            ret, frame = self.cap.read()
            if not ret or frame is None:
                if hasattr(self.cap, "set"):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                time.sleep(0.03)
                continue

            self.frame_index += 1
            cur_time = time.time()
            elapsed_time = cur_time - self.start_time
            dt = cur_time - last_time
            last_time = cur_time
            if dt > 0:
                self.fps_buffer.append(1.0 / dt)
                self.current_fps = sum(self.fps_buffer) / len(self.fps_buffer)

            # 1. Detection (with adaptive frame skipping for low-end / battery profile)
            skip = self.profile.frame_skip
            is_detect_frame = (skip <= 0) or (self.frame_index % (skip + 1) == 0)
            if is_detect_frame or not self.last_detections:
                detections = self.detector.detect(frame)
                self.last_detections = detections
            else:
                detections = self.last_detections

            # 2. Tracking (continuous Kalman prediction on every frame)
            tracked_players = self.tracker.update(detections, timestamp=elapsed_time)

            # 3. Pose Estimation (with cadence regulation)
            poses: List[PoseResult] = []
            if self.enable_pose and tracked_players:
                cadence = self.profile.pose_cadence
                is_pose_frame = (cadence <= 1) or (self.frame_index % cadence == 0)
                if is_pose_frame or not self.last_poses:
                    poses = self.pose_estimator.estimate(frame, tracked_players)
                    self.last_poses = poses
                else:
                    poses = self.last_poses


            # 4. Kinematics Update
            kinematics_map = self.kinematics_engine.update(
                tracked_players, timestamp=elapsed_time, poses=poses
            )

            # 5. Sport Rules & Event Analysis
            sport_analysis: Dict[str, Any] = {}
            if self.sport == "volleyball" and self.volleyball_analyzer:
                pose_dict = {p.player_id: p.to_dict()["keypoints"] for p in poses}
                sport_players = []
                for p in tracked_players:
                    kin_snap = kinematics_map.get(p.player_id)
                    x_m = kin_snap.court_position[0] if kin_snap else 0.0
                    y_m = kin_snap.court_position[1] if kin_snap else 0.0
                    sport_players.append({
                        "player_id": p.player_id,
                        "confidence": p.confidence,
                        "bbox": p.bbox,
                        "kinematics": {
                            "court_position": {"x_m": x_m, "y_m": y_m},
                            "instant_speed_mps": kin_snap.instant_speed_mps if kin_snap else 0.0,
                            "movement_state": kin_snap.movement_state if kin_snap else "standing",
                            "highest_jump_cm": kin_snap.highest_jump_cm if kin_snap else 0.0
                        },
                        "pose": pose_dict.get(p.player_id, {})
                    })
                sport_analysis = self.volleyball_analyzer.analyze_frame(
                    frame_idx=self.frame_index,
                    timestamp=elapsed_time,
                    players=sport_players,
                    court_calibrator=self.calibrator
                )
            elif self.sport == "kabaddi" and self.kabaddi_analyzer:
                sport_players = []
                for p in tracked_players:
                    kin_snap = kinematics_map.get(p.player_id)
                    x_m = kin_snap.court_position[0] if kin_snap else 0.0
                    y_m = kin_snap.court_position[1] if kin_snap else 0.0
                    sport_players.append({
                        "player_id": p.player_id,
                        "confidence": p.confidence,
                        "bbox": p.bbox,
                        "kinematics": {
                            "court_position": {"x_m": x_m, "y_m": y_m},
                            "instant_speed_mps": kin_snap.instant_speed_mps if kin_snap else 0.0,
                            "movement_state": kin_snap.movement_state if kin_snap else "standing",
                        },
                    })
                sport_analysis = self.kabaddi_analyzer.analyze_frame(
                    frame_idx=self.frame_index,
                    timestamp=elapsed_time,
                    players=sport_players,
                )
            elif self.sport == "kho_kho" and self.kho_kho_analyzer:
                sport_players = []
                for p in tracked_players:
                    kin_snap = kinematics_map.get(p.player_id)
                    x_m = kin_snap.court_position[0] if kin_snap else 0.0
                    y_m = kin_snap.court_position[1] if kin_snap else 0.0
                    sport_players.append({
                        "player_id": p.player_id,
                        "confidence": p.confidence,
                        "bbox": p.bbox,
                        "kinematics": {
                            "court_position": {"x_m": x_m, "y_m": y_m},
                            "instant_speed_mps": kin_snap.instant_speed_mps if kin_snap else 0.0,
                            "movement_state": kin_snap.movement_state if kin_snap else "standing",
                        },
                    })
                sport_analysis = self.kho_kho_analyzer.analyze_frame(
                    frame_idx=self.frame_index,
                    timestamp=elapsed_time,
                    players=sport_players,
                )

            # 6. Annotation
            annotated_frame = self._annotate_frame(
                frame.copy(), tracked_players, poses, kinematics_map, sport_analysis
            )

            # 7. Telemetry Generation
            telemetry = self._generate_telemetry(
                tracked_players, poses, kinematics_map, sport_analysis
            )

            with self._lock:
                self.latest_raw_frame = frame
                self.latest_annotated_frame = annotated_frame
                self.latest_telemetry = telemetry

            # Throttle slightly
            elapsed = time.time() - cur_time
            sleep_time = max(0.001, (1.0 / 30.0) - elapsed)
            time.sleep(sleep_time)

    def _annotate_frame(
        self,
        frame: np.ndarray,
        players: List[TrackedPlayer],
        poses: List[PoseResult],
        kinematics_map: Dict[int, KinematicsSnapshot],
        sport_analysis: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        h, w = frame.shape[:2]

        # 1. Motion trails
        if self.show_trails:
            for p in players:
                trail_points = list(p.trail)
                if len(trail_points) >= 2:
                    for i in range(1, len(trail_points)):
                        pt1 = (int(trail_points[i - 1][0]), int(trail_points[i - 1][1]))
                        pt2 = (int(trail_points[i][0]), int(trail_points[i][1]))
                        alpha = float(i) / len(trail_points)
                        thickness = max(1, int(3 * alpha))
                        color = (0, int(255 * alpha), int(255 * (1 - alpha * 0.5)))
                        cv2.line(frame, pt1, pt2, color, thickness)

        # 2. Skeletons
        if self.show_skeleton and poses:
            for pose in poses:
                self.pose_estimator.draw_skeleton(frame, pose, line_thickness=2)

        # 3. Bounding boxes & Kinematic Info Badges
        if self.show_boxes:
            for p in players:
                x1, y1, x2, y2 = p.bbox
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                bw = x2 - x1
                bh = y2 - y1

                # Confidence color
                if p.confidence >= 0.85:
                    color = (0, 255, 128)
                elif p.confidence >= 0.70:
                    color = (0, 215, 255)
                else:
                    color = (0, 140, 255)

                # Corner brackets
                line_len = min(25, int(bw * 0.25), int(bh * 0.25))
                thick = 2
                cv2.line(frame, (x1, y1), (x1 + line_len, y1), color, thick)
                cv2.line(frame, (x1, y1), (x1, y1 + line_len), color, thick)
                cv2.line(frame, (x2, y1), (x2 - line_len, y1), color, thick)
                cv2.line(frame, (x2, y1), (x2, y1 + line_len), color, thick)
                cv2.line(frame, (x1, y2), (x1 + line_len, y2), color, thick)
                cv2.line(frame, (x1, y2), (x1, y2 - line_len), color, thick)
                cv2.line(frame, (x2, y2), (x2 - line_len, y2), color, thick)
                cv2.line(frame, (x2, y2), (x2, y2 - line_len), color, thick)

                # Kinematic & Sport metrics badge
                kin = kinematics_map.get(p.player_id)
                speed_str = f"{kin.instant_speed_mps:.1f}m/s" if kin else "0.0m/s"
                state_str = kin.movement_state.upper() if kin else "STAND"

                badge_sport = ""
                if self.volleyball_analyzer:
                    side = self.volleyball_analyzer.player_sides.get(p.player_id, "")
                    zone = self.volleyball_analyzer.player_zones.get(p.player_id, 0)
                    role = self.volleyball_analyzer.player_roles.get(p.player_id, "")
                    t_abbr = "A" if side == "Team A" else ("B" if side == "Team B" else "?")
                    badge_sport = f" | [{t_abbr}-Z{zone} {role[:1].upper()}]"

                badge_text = f"ID #{p.player_id} | {speed_str} | {state_str}{badge_sport}"
                (tw, th), baseline = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
                badge_y = max(th + 6, y1 - 6)
                cv2.rectangle(frame, (x1, badge_y - th - 6), (x1 + tw + 10, badge_y + 2), (15, 15, 15), -1)
                cv2.rectangle(frame, (x1, badge_y - th - 6), (x1 + tw + 10, badge_y + 2), color, 1)
                cv2.putText(frame, badge_text, (x1 + 5, badge_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1, cv2.LINE_AA)

                # Jump indicator alert
                if kin and kin.movement_state == "airborne":
                    jump_txt = f"AIRBORNE ({kin.highest_jump_cm:.0f}cm)"
                    cv2.putText(frame, jump_txt, (x1, y2 + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1, cv2.LINE_AA)

        # Broadcast HUD Top Bar
        hud_bg = (15, 15, 15)
        cv2.rectangle(frame, (0, 0), (w, 40), hud_bg, -1)
        cv2.line(frame, (0, 40), (w, 40), (60, 60, 60), 1)

        rally_hud = ""
        if self.volleyball_analyzer:
            rally_hud = f"  |  RALLY: {self.volleyball_analyzer.rally_state}"

        hud_text = (
            f"SPORTS ANALYZER AI  |  SPORT: {self.sport.upper()}{rally_hud}  |  "
            f"FPS: {self.current_fps:.1f}  |  PLAYERS: {len(players)}  |  "
            f"FRAME: {self.frame_index}"
        )
        cv2.putText(frame, hud_text, (20, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 240, 255), 1, cv2.LINE_AA)

        # Live REC dot indicator
        cv2.circle(frame, (w - 30, 20), 6, (0, 0, 255), -1)
        cv2.putText(frame, "LIVE", (w - 75, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # Active Violations Alert Banner
        violations = []
        if sport_analysis:
            violations = sport_analysis.get("active_violations") or sport_analysis.get("violations") or []
        if violations:
            for idx, v in enumerate(violations[:2]):
                banner_y = h - 45 - (idx * 32)
                cv2.rectangle(frame, (20, banner_y - 20), (w - 20, banner_y + 8), (20, 20, 160), -1)
                cv2.rectangle(frame, (20, banner_y - 20), (w - 20, banner_y + 8), (0, 0, 255), 2)
                pid_val = v.get("player_id", v.get("raider_id", v.get("chaser_id", "?")))
                alert_text = f"FOUL: {v.get('violation_type')} - Player #{pid_val} ({v.get('team', '')}) | Conf: {v.get('confidence_level', 'High')}"
                cv2.putText(frame, alert_text, (30, banner_y - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)

        return frame

    def _generate_telemetry(
        self,
        players: List[TrackedPlayer],
        poses: List[PoseResult],
        kinematics_map: Dict[int, KinematicsSnapshot],
        sport_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pose_dict = {p.player_id: p.to_dict() for p in poses}

        player_telemetry = []
        for p in players:
            p_data = p.to_dict(self.frame_width, self.frame_height)
            pid = p.player_id

            if pid in kinematics_map:
                p_data["kinematics"] = kinematics_map[pid].to_dict()
            if pid in pose_dict:
                p_data["pose"] = pose_dict[pid]["keypoints"]

            if self.volleyball_analyzer:
                p_data["team"] = self.volleyball_analyzer.player_sides.get(pid, "unknown")
                p_data["zone"] = f"Zone {self.volleyball_analyzer.player_zones.get(pid, 0)}"
                p_data["row"] = self.volleyball_analyzer.player_roles.get(pid, "unknown")
            elif self.kabaddi_analyzer:
                if pid == self.kabaddi_analyzer.active_raider_id:
                    p_data["role"] = "raider"
                    p_data["team"] = self.kabaddi_analyzer.raiding_team or "unknown"
                else:
                    p_data["role"] = "defender"
            elif self.kho_kho_analyzer:
                if pid == self.kho_kho_analyzer.active_chaser_id:
                    p_data["role"] = "active_chaser"
                elif pid in self.kho_kho_analyzer._sitting_chasers:
                    p_data["role"] = f"sitting_chaser_sq{self.kho_kho_analyzer._sitting_chasers[pid]}"

            player_telemetry.append(p_data)

        telemetry: Dict[str, Any] = {
            "type": "live_telemetry",
            "timestamp": round(time.time() - self.start_time, 3),
            "frame_index": self.frame_index,
            "fps": round(self.current_fps, 1),
            "sport": self.sport,
            "frame_dimensions": {"width": self.frame_width, "height": self.frame_height},
            "players_count": len(players),
            "players": player_telemetry
        }

        if sport_analysis:
            if self.sport == "volleyball":
                telemetry["volleyball"] = sport_analysis
            elif self.sport == "kabaddi":
                telemetry["kabaddi"] = sport_analysis
            elif self.sport == "kho_kho":
                telemetry["kho_kho"] = sport_analysis
            else:
                telemetry[self.sport] = sport_analysis

        return telemetry

    def get_latest_telemetry(self) -> Dict[str, Any]:
        with self._lock:
            return self.latest_telemetry.copy() if self.latest_telemetry else {}

    def get_annotated_frame_jpeg(self, quality: int = 80) -> Optional[bytes]:
        with self._lock:
            if self.latest_annotated_frame is None:
                return None
            ret, jpeg = cv2.imencode('.jpg', self.latest_annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            return jpeg.tobytes() if ret else None

    def mjpeg_stream_generator(self) -> Generator[bytes, None, None]:
        while self.is_running:
            jpeg_bytes = self.get_annotated_frame_jpeg()
            if jpeg_bytes is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n')
            time.sleep(0.033)

    def get_topdown_tactical_image(self) -> np.ndarray:
        """Returns rendered 2D top-down court image with projected player positions."""
        telemetry = self.get_latest_telemetry()
        players = telemetry.get("players", [])
        positions = []
        for p in players:
            kin = p.get("kinematics", {})
            c_pos = kin.get("court_position", {})
            positions.append({
                "player_id": p.get("player_id", 0),
                "x_m": c_pos.get("x_m", 0.0),
                "y_m": c_pos.get("y_m", 0.0),
                "team": p.get("team", "Team A"),
                "speed": kin.get("instant_speed_mps", 0.0)
            })
        return self.court_renderer.render_tactical_view(positions)

    def get_heatmap_base64(self, player_id: Optional[int] = None, mode: str = "court") -> str:
        """Generates 2D top-down or perspective heatmap encoded as base64 PNG."""
        metric_positions_dict = self.kinematics_engine.get_all_metric_positions()
        pts = []
        if player_id is not None:
            pts = metric_positions_dict.get(player_id, [])
        else:
            for p_list in metric_positions_dict.values():
                pts.extend(p_list)

        if mode == "court":
            img = generate_topdown_court_heatmap(pts, sport=self.sport)
        else:
            img = generate_court_heatmap(pts)
        return heatmap_to_base64_png(img)

    def get_volleyball_events(self) -> List[Dict[str, Any]]:
        """Returns recent volleyball events (serves, spikes, blocks)."""
        if self.volleyball_analyzer:
            return list(self.volleyball_analyzer.recent_events)
        return []

    def get_volleyball_violations(self) -> List[Dict[str, Any]]:
        """Returns all logged volleyball violations."""
        if self.volleyball_analyzer:
            return self.volleyball_analyzer.all_violations
        return []

    def reset_rally(self):
        """Resets active volleyball rally to IDLE state."""
        if self.volleyball_analyzer:
            self.volleyball_analyzer.reset_rally()

    def get_kabaddi_events(self) -> List[Dict[str, Any]]:
        """Returns recent kabaddi events (raids, tackles, touches)."""
        if self.kabaddi_analyzer:
            return self.kabaddi_analyzer.get_events()
        return []

    def get_kabaddi_violations(self) -> List[Dict[str, Any]]:
        """Returns all logged kabaddi violations."""
        if self.kabaddi_analyzer:
            return self.kabaddi_analyzer.get_violations()
        return []

    def reset_raid(self):
        """Resets active kabaddi raid to WAITING state."""
        if self.kabaddi_analyzer:
            self.kabaddi_analyzer.reset_raid()

    def get_kho_kho_events(self) -> List[Dict[str, Any]]:
        """Returns recent kho kho events (khos, tags)."""
        if self.kho_kho_analyzer:
            return self.kho_kho_analyzer.get_events()
        return []

    def get_kho_kho_violations(self) -> List[Dict[str, Any]]:
        """Returns all logged kho kho violations."""
        if self.kho_kho_analyzer:
            return self.kho_kho_analyzer.get_violations()
        return []

    def reset_kho_kho_turn(self):
        """Resets kho kho chase turn."""
        if self.kho_kho_analyzer:
            self.kho_kho_analyzer.reset_turn()

    def set_performance_profile(self, profile: PerformanceProfile):
        """Updates active tuning profile for frame skipping and pose cadence."""
        with self._lock:
            self.profile = profile
            logger.info(f"VisionPipeline updated with profile: {profile.name} (skip={profile.frame_skip}, pose_cadence={profile.pose_cadence})")

    def get_performance_profile(self) -> PerformanceProfile:
        """Returns the active performance tuning profile."""
        with self._lock:
            return self.profile


