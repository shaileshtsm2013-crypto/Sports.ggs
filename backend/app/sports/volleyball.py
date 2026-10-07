from typing import Dict, Any, List, Optional, Tuple
from collections import deque
import time
import math
import numpy as np

from backend.app.sports.base import SportsAnalyzer


def get_confidence_level(score: float) -> str:
    """Classifies a numeric confidence score into standard levels without fabrication."""
    if score is None or math.isnan(score) or score <= 0.0:
        return "Unknown"
    elif score >= 0.80:
        return "High"
    elif score >= 0.50:
        return "Medium"
    else:
        return "Low"


class VolleyballAnalyzer(SportsAnalyzer):
    """
    Dedicated analyzer for FIVB Volleyball matches.
    Implements:
      - Real-time side classification: Team A (X in [0, 9]m) vs Team B (X in [9, 18]m)
      - Front-row vs Back-row zone mapping (FIVB zones 1-6)
      - Center line penetration detection (Rule 11.2)
      - Net touch violation detection (Rule 11.3)
      - Back-row attack fault detection (Rule 13.2.2/13.2.3)
      - Rotational fault detection (Rule 7.4/7.5)
      - Action classification: Serve execution, Spike jump vs Block jump
      - Rally lifecycle state machine: IDLE -> SERVE -> RALLY_ACTIVE -> POINT_SCORED
    """

    def __init__(self, net_gender: str = "men"):
        super().__init__("volleyball")
        self.court_dimensions_meters = {
            "length": 18.0,
            "width": 9.0,
            "center_x": 9.0,
            "team_a_attack_x": 6.0,
            "team_b_attack_x": 12.0,
            "net_height_men": 2.43,
            "net_height_women": 2.24,
            "selected_net_height": 2.43 if net_gender.lower() == "men" else 2.24
        }
        self.court_calibrated = True

        # Player state registries
        self.player_sides: Dict[int, str] = {}  # pid -> "Team A" | "Team B"
        self.player_zones: Dict[int, int] = {}  # pid -> zone 1-6
        self.player_roles: Dict[int, str] = {}  # pid -> "front" | "back"
        self.player_takeoff_pos: Dict[int, Tuple[float, float]] = {}  # pid -> (x_m, y_m)

        # Rally state machine
        self.rally_state: str = "IDLE"  # IDLE, SERVE, RALLY_ACTIVE, POINT_SCORED
        self.rally_start_time: Optional[float] = None
        self.rally_duration: float = 0.0
        self.contacts_count: int = 0
        self.serving_team: Optional[str] = None

        # Event & Violation logs
        self.active_violations: List[Dict[str, Any]] = []
        self.all_violations: List[Dict[str, Any]] = []
        self.recent_events: deque = deque(maxlen=50)

        # Last jump states for detecting takeoffs
        self._prev_airborne_states: Dict[int, bool] = {}

    def calibrate_court(self, frame: np.ndarray, manual_points: Optional[List[Dict[str, float]]] = None) -> bool:
        self.court_calibrated = True
        return True

    def reset_rally(self):
        """Resets the current rally to IDLE state."""
        self.rally_state = "IDLE"
        self.rally_start_time = None
        self.rally_duration = 0.0
        self.contacts_count = 0
        self.serving_team = None
        self.active_violations.clear()

    def set_net_height(self, gender: str = "men"):
        """Sets net height between Men (2.43m) and Women (2.24m)."""
        height = 2.43 if gender.lower() == "men" else 2.24
        self.court_dimensions_meters["selected_net_height"] = height

    def classify_court_side(self, x_m: float) -> str:
        """Classifies metric X-coordinate into Team A or Team B."""
        if x_m <= 9.0:
            return "Team A"
        else:
            return "Team B"

    def classify_zone(self, x_m: float, y_m: float, team: str) -> Tuple[int, str]:
        """
        Maps metric coordinates (X, Y) into FIVB Rotational Zones (1 to 6)
        and row ('front' or 'back').
        Court Y: [0.0, 9.0] meters.
        Lateral bands: Left: [0, 3]m, Center: [3, 6]m, Right: [6, 9]m.
        """
        x_m = max(0.0, min(18.0, x_m))
        y_m = max(0.0, min(9.0, y_m))

        if team == "Team A":
            is_front = x_m >= self.court_dimensions_meters["team_a_attack_x"]
            row = "front" if is_front else "back"
            if is_front:
                if y_m < 3.0:
                    zone = 4  # Front-Left
                elif y_m < 6.0:
                    zone = 3  # Front-Center
                else:
                    zone = 2  # Front-Right
            else:
                if y_m < 3.0:
                    zone = 5  # Back-Left
                elif y_m < 6.0:
                    zone = 6  # Back-Center
                else:
                    zone = 1  # Back-Right
        else:  # Team B
            is_front = x_m <= self.court_dimensions_meters["team_b_attack_x"]
            row = "front" if is_front else "back"
            if is_front:
                if y_m < 3.0:
                    zone = 2  # Front-Right (facing net)
                elif y_m < 6.0:
                    zone = 3  # Front-Center
                else:
                    zone = 4  # Front-Left
            else:
                if y_m < 3.0:
                    zone = 1  # Back-Right
                elif y_m < 6.0:
                    zone = 6  # Back-Center
                else:
                    zone = 5  # Back-Left

        return zone, row

    def check_center_line_penetration(
        self,
        player_id: int,
        team: str,
        x_m: float,
        pose_keypoints: Optional[Dict[str, Any]] = None,
        confidence: float = 0.85
    ) -> Optional[Dict[str, Any]]:
        """
        FIVB Rule 11.2: Touching the opponent's court with any part of body above feet
        is permitted provided it does not interfere. Contact with the opponent's court
        with a foot/feet is permitted if some part of the foot/feet remains on or directly
        above the center line. Complete foot crossing into opponent court is a fault.
        """
        center_x = self.court_dimensions_meters["center_x"]
        penetration = 0.0
        is_fault = False
        foot_conf = confidence

        if pose_keypoints:
            l_ankle = pose_keypoints.get("left_ankle")
            r_ankle = pose_keypoints.get("right_ankle")
            ankle_confs = []
            if l_ankle and isinstance(l_ankle, dict):
                ankle_confs.append(l_ankle.get("confidence", 0.0))
            if r_ankle and isinstance(r_ankle, dict):
                ankle_confs.append(r_ankle.get("confidence", 0.0))
            if ankle_confs:
                foot_conf = sum(ankle_confs) / len(ankle_confs)

        if team == "Team A" and x_m > center_x + 0.15:
            is_fault = True
            penetration = x_m - center_x
        elif team == "Team B" and x_m < center_x - 0.15:
            is_fault = True
            penetration = center_x - x_m

        if is_fault:
            return {
                "rule": "FIVB Rule 11.2 - Center Line Penetration",
                "violation_type": "CENTER_LINE_PENETRATION",
                "player_id": player_id,
                "team": team,
                "penetration_meters": round(penetration, 2),
                "position_x": round(x_m, 2),
                "confidence_score": round(foot_conf, 2),
                "confidence_level": get_confidence_level(foot_conf),
                "description": f"Player #{player_id} ({team}) penetrated opponent court by {penetration:.2f}m past the centerline."
            }
        return None

    def check_net_touch(
        self,
        player_id: int,
        team: str,
        x_m: float,
        is_airborne: bool,
        pose_keypoints: Optional[Dict[str, Any]] = None,
        confidence: float = 0.85
    ) -> Optional[Dict[str, Any]]:
        """
        FIVB Rule 11.3: Contact with the net by a player between the antennae,
        during the action of playing the ball, is a fault.
        Net is located at X = 9.0m.
        """
        center_x = self.court_dimensions_meters["center_x"]
        dist_to_net = abs(x_m - center_x)

        if dist_to_net <= 0.25 and is_airborne:
            upper_conf = confidence
            contact_keypoint = "body"

            if pose_keypoints:
                for kp_name in ["left_wrist", "right_wrist", "left_elbow", "right_elbow"]:
                    kp = pose_keypoints.get(kp_name)
                    if kp and isinstance(kp, dict) and kp.get("confidence", 0) > 0.4:
                        contact_keypoint = kp_name
                        upper_conf = kp.get("confidence", upper_conf)
                        break

            return {
                "rule": "FIVB Rule 11.3 - Net Touch Fault",
                "violation_type": "NET_TOUCH",
                "player_id": player_id,
                "team": team,
                "distance_to_net_meters": round(dist_to_net, 2),
                "contact_keypoint": contact_keypoint,
                "confidence_score": round(upper_conf, 2),
                "confidence_level": get_confidence_level(upper_conf),
                "description": f"Player #{player_id} ({team}) contacted the net with {contact_keypoint} during aerial action."
            }
        return None

    def check_back_row_attack(
        self,
        player_id: int,
        team: str,
        role: str,
        takeoff_x: float,
        is_spiking: bool,
        confidence: float = 0.85
    ) -> Optional[Dict[str, Any]]:
        """
        FIVB Rule 13.2.2 / 13.2.3: A back-row player completing an attack hit inside the front zone.
        """
        if role != "back" or not is_spiking:
            return None

        is_illegal = False
        attack_line = 0.0

        if team == "Team A":
            attack_line = self.court_dimensions_meters["team_a_attack_x"]
            if takeoff_x > attack_line:
                is_illegal = True
        else:
            attack_line = self.court_dimensions_meters["team_b_attack_x"]
            if takeoff_x < attack_line:
                is_illegal = True

        if is_illegal:
            margin = abs(takeoff_x - attack_line)
            return {
                "rule": "FIVB Rule 13.2.2 - Illegal Back-Row Attack",
                "violation_type": "BACK_ROW_ATTACK",
                "player_id": player_id,
                "team": team,
                "takeoff_x": round(takeoff_x, 2),
                "attack_line_x": round(attack_line, 2),
                "margin_inside_front_zone": round(margin, 2),
                "confidence_score": round(confidence, 2),
                "confidence_level": get_confidence_level(confidence),
                "description": f"Back-row player #{player_id} ({team}) took off {margin:.2f}m inside the 3m attack line for an attack hit."
            }
        return None

    def check_rotation_fault(
        self,
        team_players: List[Dict[str, Any]],
        team: str
    ) -> Optional[Dict[str, Any]]:
        """
        FIVB Rule 7.4 / 7.5: Verifies front-to-back spatial ordering at service hit.
        """
        if len(team_players) < 6:
            return None

        zone_map: Dict[int, Dict[str, Any]] = {}
        for p in team_players:
            z = p.get("zone")
            if z:
                zone_map[z] = p

        faults = []
        pairs = [(4, 5), (3, 6), (2, 1)]

        for fz, bz in pairs:
            pf = zone_map.get(fz)
            pb = zone_map.get(bz)
            if not pf or not pb:
                continue

            xf = pf.get("x_m", 0.0)
            xb = pb.get("x_m", 0.0)

            if team == "Team A":
                if xf <= xb:
                    faults.append(f"Zone {fz} (#{pf.get('player_id')}) behind Zone {bz} (#{pb.get('player_id')})")
            else:
                if xf >= xb:
                    faults.append(f"Zone {fz} (#{pf.get('player_id')}) behind Zone {bz} (#{pb.get('player_id')})")

        if faults:
            return {
                "rule": "FIVB Rule 7.4/7.5 - Rotational Fault",
                "violation_type": "ROTATION_FAULT",
                "team": team,
                "faults": faults,
                "confidence_score": 0.82,
                "confidence_level": "High",
                "description": f"Rotational ordering fault on {team}: {', '.join(faults)}."
            }
        return None

    def classify_jump_action(
        self,
        player_id: int,
        team: str,
        x_m: float,
        is_airborne: bool,
        jump_height_cm: float,
        pose_keypoints: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Classifies jumping aerial maneuvers into Spike Jump vs Block Jump.
        """
        if not is_airborne:
            return None

        center_x = self.court_dimensions_meters["center_x"]
        dist_to_net = abs(x_m - center_x)

        left_wrist_up = False
        right_wrist_up = False
        wrists_above_head = False

        if pose_keypoints:
            lw = pose_keypoints.get("left_wrist", {})
            rw = pose_keypoints.get("right_wrist", {})
            ls = pose_keypoints.get("left_shoulder", {})
            rs = pose_keypoints.get("right_shoulder", {})
            nose = pose_keypoints.get("nose", {})

            if lw.get("y", 999) < ls.get("y", 0):
                left_wrist_up = True
            if rw.get("y", 999) < rs.get("y", 0):
                right_wrist_up = True
            if lw.get("y", 999) < nose.get("y", 0) or rw.get("y", 999) < nose.get("y", 0):
                wrists_above_head = True

        # Block: Both arms up, within 1.2m of net
        if dist_to_net <= 1.2 and (left_wrist_up and right_wrist_up):
            return {
                "event_type": "BLOCK",
                "player_id": player_id,
                "team": team,
                "distance_to_net_meters": round(dist_to_net, 2),
                "jump_height_cm": round(jump_height_cm, 1),
                "confidence_level": "High",
                "description": f"Player #{player_id} ({team}) executed a dual-arm net block ({jump_height_cm:.0f}cm)."
            }

        # Spike: Dominant wrist high, near attack zone / net (within 3.5m)
        if dist_to_net <= 3.5 and (left_wrist_up or right_wrist_up or wrists_above_head):
            return {
                "event_type": "SPIKE",
                "player_id": player_id,
                "team": team,
                "distance_to_net_meters": round(dist_to_net, 2),
                "jump_height_cm": round(jump_height_cm, 1),
                "confidence_level": "High" if wrists_above_head else "Medium",
                "description": f"Player #{player_id} ({team}) executed an attack spike jump ({jump_height_cm:.0f}cm)."
            }

        return None

    def check_service_event(
        self,
        player_id: int,
        team: str,
        x_m: float,
        is_airborne: bool,
        speed_mps: float,
        pose_keypoints: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        FIVB Rule 12.4: Service execution from behind endline.
        """
        is_behind_line = (team == "Team A" and x_m <= 0.5) or (team == "Team B" and x_m >= 17.5)
        if not is_behind_line:
            return None

        arm_raised = False
        if pose_keypoints:
            rw = pose_keypoints.get("right_wrist", {})
            rs = pose_keypoints.get("right_shoulder", {})
            lw = pose_keypoints.get("left_wrist", {})
            ls = pose_keypoints.get("left_shoulder", {})
            if rw.get("y", 999) < rs.get("y", 0) or lw.get("y", 999) < ls.get("y", 0):
                arm_raised = True

        if is_airborne or arm_raised or speed_mps > 1.5:
            return {
                "event_type": "SERVE",
                "player_id": player_id,
                "team": team,
                "position_x": round(x_m, 2),
                "service_type": "Jump Serve" if is_airborne else "Float / Standing Serve",
                "confidence_level": "High" if arm_raised else "Medium",
                "description": f"Player #{player_id} initiated service for {team} from baseline."
            }
        return None

    def analyze_frame(
        self,
        frame_idx: int,
        timestamp: float,
        players: List[Any],
        court_calibrator: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Main frame analysis pipeline for volleyball.
        """
        frame_violations: List[Dict[str, Any]] = []
        frame_events: List[Dict[str, Any]] = []

        team_a_players = []
        team_b_players = []

        for p in players:
            if isinstance(p, dict):
                pid = p.get("player_id", 0)
                conf = p.get("confidence", 0.85)
                kin = p.get("kinematics", {})
                c_pos = kin.get("court_position", {}) if isinstance(kin, dict) else {}
                x_m = c_pos.get("x_m", 0.0)
                y_m = c_pos.get("y_m", 0.0)
                movement_state = kin.get("movement_state", "standing") if isinstance(kin, dict) else "standing"
                jump_height = kin.get("highest_jump_cm", 0.0) if isinstance(kin, dict) else 0.0
                speed = kin.get("instant_speed_mps", 0.0) if isinstance(kin, dict) else 0.0
                pose_dict = p.get("pose", {})
            else:
                pid = getattr(p, "player_id", 0)
                conf = getattr(p, "confidence", 0.85)
                kin = getattr(p, "kinematics", None)
                if court_calibrator:
                    bx1, by1, bx2, by2 = getattr(p, "bbox", (0, 0, 0, 0))
                    cx = (bx1 + bx2) / 2.0
                    cy_feet = float(by2)
                    x_m, y_m = court_calibrator.image_to_court(cx, cy_feet)
                else:
                    x_m, y_m = 0.0, 0.0

                movement_state = getattr(kin, "movement_state", "standing") if kin else "standing"
                jump_height = getattr(kin, "highest_jump_cm", 0.0) if kin else 0.0
                speed = getattr(kin, "instant_speed_mps", 0.0) if kin else 0.0
                pose_dict = getattr(p, "pose", {})

            is_airborne = (movement_state == "airborne")
            team = self.classify_court_side(x_m)
            zone, row = self.classify_zone(x_m, y_m, team)

            self.player_sides[pid] = team
            self.player_zones[pid] = zone
            self.player_roles[pid] = row

            was_airborne = self._prev_airborne_states.get(pid, False)
            if is_airborne and not was_airborne:
                self.player_takeoff_pos[pid] = (x_m, y_m)
            takeoff_x, _ = self.player_takeoff_pos.get(pid, (x_m, y_m))
            self._prev_airborne_states[pid] = is_airborne

            p_summary = {
                "player_id": pid,
                "team": team,
                "zone": zone,
                "row": row,
                "x_m": round(x_m, 2),
                "y_m": round(y_m, 2),
                "speed_mps": round(speed, 2),
                "is_airborne": is_airborne
            }

            if team == "Team A":
                team_a_players.append(p_summary)
            else:
                team_b_players.append(p_summary)

            serve_evt = self.check_service_event(pid, team, x_m, is_airborne, speed, pose_dict)
            if serve_evt:
                serve_evt["timestamp"] = round(timestamp, 3)
                serve_evt["frame_idx"] = frame_idx
                frame_events.append(serve_evt)
                if self.rally_state in ["IDLE", "POINT_SCORED"]:
                    self.rally_state = "SERVE"
                    self.serving_team = team
                    self.rally_start_time = timestamp

            jump_action = self.classify_jump_action(pid, team, x_m, is_airborne, jump_height, pose_dict)
            is_spiking = False
            if jump_action:
                jump_action["timestamp"] = round(timestamp, 3)
                jump_action["frame_idx"] = frame_idx
                frame_events.append(jump_action)
                if jump_action["event_type"] == "SPIKE":
                    is_spiking = True
                    self.contacts_count += 1
                elif jump_action["event_type"] == "BLOCK":
                    self.contacts_count += 1

                if self.rally_state == "SERVE":
                    self.rally_state = "RALLY_ACTIVE"

            foul_center = self.check_center_line_penetration(pid, team, x_m, pose_dict, conf)
            if foul_center:
                foul_center["timestamp"] = round(timestamp, 3)
                foul_center["frame_idx"] = frame_idx
                frame_violations.append(foul_center)

            foul_net = self.check_net_touch(pid, team, x_m, is_airborne, pose_dict, conf)
            if foul_net:
                foul_net["timestamp"] = round(timestamp, 3)
                foul_net["frame_idx"] = frame_idx
                frame_violations.append(foul_net)

            foul_back_row = self.check_back_row_attack(pid, team, row, takeoff_x, is_spiking, conf)
            if foul_back_row:
                foul_back_row["timestamp"] = round(timestamp, 3)
                foul_back_row["frame_idx"] = frame_idx
                frame_violations.append(foul_back_row)

        if self.rally_state == "SERVE":
            rot_a = self.check_rotation_fault(team_a_players, "Team A")
            if rot_a:
                rot_a["timestamp"] = round(timestamp, 3)
                rot_a["frame_idx"] = frame_idx
                frame_violations.append(rot_a)

            rot_b = self.check_rotation_fault(team_b_players, "Team B")
            if rot_b:
                rot_b["timestamp"] = round(timestamp, 3)
                rot_b["frame_idx"] = frame_idx
                frame_violations.append(rot_b)

        if self.rally_start_time is not None:
            self.rally_duration = round(timestamp - self.rally_start_time, 2)

        self.active_violations = frame_violations
        for f in frame_violations:
            self.all_violations.append(f)
        for e in frame_events:
            self.recent_events.appendleft(e)

        return {
            "sport": "volleyball",
            "frame_idx": frame_idx,
            "timestamp": timestamp,
            "rally_state": self.rally_state,
            "rally_duration_seconds": self.rally_duration,
            "contacts_count": self.contacts_count,
            "serving_team": self.serving_team,
            "team_distribution": {
                "team_a_count": len(team_a_players),
                "team_b_count": len(team_b_players),
                "team_a_players": team_a_players,
                "team_b_players": team_b_players
            },
            "active_violations": frame_violations,
            "recent_events": list(self.recent_events)[:10]
        }

    def get_court_layout(self) -> Dict[str, Any]:
        return {
            "sport": "volleyball",
            "dimensions_meters": self.court_dimensions_meters,
            "zones": [
                "Zone 1 (Back-Right)", "Zone 2 (Front-Right)", "Zone 3 (Front-Center)",
                "Zone 4 (Front-Left)", "Zone 5 (Back-Left)", "Zone 6 (Back-Center)"
            ],
            "key_lines": ["Endlines", "Sidelines", "Centerline / Net", "Attack lines (3m)"]
        }

