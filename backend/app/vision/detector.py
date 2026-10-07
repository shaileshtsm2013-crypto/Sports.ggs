import os
import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import cv2

logger = logging.getLogger("sports_analyzer.vision.detector")


@dataclass
class Detection:
    """Represents a single detected human/player in a frame."""
    box: Tuple[int, int, int, int]  # (x1, y1, x2, y2) in pixel coordinates
    confidence: float
    class_id: int = 0
    class_name: str = "person"
    
    @property
    def x1(self) -> int:
        return self.box[0]
    
    @property
    def y1(self) -> int:
        return self.box[1]
    
    @property
    def x2(self) -> int:
        return self.box[2]
    
    @property
    def y2(self) -> int:
        return self.box[3]
    
    @property
    def width(self) -> int:
        return max(0, self.box[2] - self.box[0])
    
    @property
    def height(self) -> int:
        return max(0, self.box[3] - self.box[1])
    
    @property
    def centroid(self) -> Tuple[float, float]:
        return ((self.box[0] + self.box[2]) / 2.0, (self.box[1] + self.box[3]) / 2.0)

    @property
    def cx(self) -> float:
        return (self.box[0] + self.box[2]) / 2.0

    @property
    def cy(self) -> float:
        return (self.box[1] + self.box[3]) / 2.0

    @property
    def area(self) -> float:
        return float(self.width * self.height)
    
    def to_dict(self, frame_w: int = 1, frame_h: int = 1) -> Dict[str, Any]:
        """Returns JSON-serializable dictionary with pixel and normalized coordinates."""
        cx, cy = self.centroid
        return {
            "bbox": {
                "x1": int(self.box[0]),
                "y1": int(self.box[1]),
                "x2": int(self.box[2]),
                "y2": int(self.box[3]),
                "width": int(self.width),
                "height": int(self.height),
                "norm_x1": round(self.box[0] / max(1, frame_w), 4),
                "norm_y1": round(self.box[1] / max(1, frame_h), 4),
                "norm_x2": round(self.box[2] / max(1, frame_w), 4),
                "norm_y2": round(self.box[3] / max(1, frame_h), 4),
                "norm_cx": round(cx / max(1, frame_w), 4),
                "norm_cy": round(cy / max(1, frame_h), 4),
            },
            "confidence": round(float(self.confidence), 3),
            "class_id": self.class_id,
            "class_name": self.class_name
        }


class PersonDetector:
    """
    Modular Person Detector using YOLOv8 with automatic fallback.
    Filters exclusively for humans (class 0 in COCO).
    """

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.40,
        device: str = "cpu",
        use_fallback_only: bool = False,
    ):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.yolo_model = None
        self.using_fallback = use_fallback_only
        
        # Initialize YOLO or fallback detector
        if use_fallback_only:
            self._init_fallback_detector()
        else:
            self._init_detector()

    def _init_detector(self):
        try:
            from ultralytics import YOLO
            logger.info(f"Loading YOLO model: {self.model_name} on device: {self.device}")
            self.yolo_model = YOLO(self.model_name)
            self.using_fallback = False
            logger.info("YOLO detector initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize YOLO ({e}). Falling back to OpenCV HOG/Color detector.")
            self.using_fallback = True
            self._init_fallback_detector()

    def _init_fallback_detector(self):
        self.hog = None
        if hasattr(cv2, "HOGDescriptor"):
            try:
                self.hog = cv2.HOGDescriptor()
                self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            except Exception:
                self.hog = None
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=50, varThreshold=25, detectShadows=True)

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Runs person detection on an input RGB/BGR frame.
        Returns a list of Detection objects.
        """
        if frame is None or frame.size == 0:
            return []

        if not self.using_fallback and self.yolo_model is not None:
            try:
                return self._detect_yolo(frame)
            except Exception as e:
                logger.warning(f"YOLO inference error: {e}. Attempting fallback.")
                if not hasattr(self, "bg_subtractor"):
                    self._init_fallback_detector()
                return self._detect_fallback(frame)
        else:
            return self._detect_fallback(frame)

    def _detect_yolo(self, frame: np.ndarray) -> List[Detection]:
        results = self.yolo_model.predict(
            source=frame,
            classes=[0],  # Filter only class 0 (person)
            conf=self.confidence_threshold,
            verbose=False,
            device=self.device
        )
        
        detections: List[Detection] = []
        if not results or len(results) == 0:
            return detections

        r = results[0]
        if r.boxes is None or len(r.boxes) == 0:
            return detections

        boxes = r.boxes.xyxy.cpu().numpy()
        confs = r.boxes.conf.cpu().numpy()
        cls_ids = r.boxes.cls.cpu().numpy()

        for box, conf, cls_id in zip(boxes, confs, cls_ids):
            detections.append(Detection(
                box=(int(box[0]), int(box[1]), int(box[2]), int(box[3])),
                confidence=float(conf),
                class_id=0,
                class_name="person"
            ))

        return detections

    def _detect_fallback(self, frame: np.ndarray) -> List[Detection]:
        """OpenCV HOG + Motion contour fallback for CPU environments or fallback testing."""
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        detections: List[Detection] = []
        
        # HOG detection if supported
        if self.hog is not None:
            try:
                boxes, weights = self.hog.detectMultiScale(
                    gray,
                    winStride=(8, 8),
                    padding=(4, 4),
                    scale=1.05
                )
                for (x, y, bw, bh), weight in zip(boxes, weights):
                    conf = float(min(0.95, max(0.50, weight[0] if isinstance(weight, (list, np.ndarray)) else weight)))
                    if conf >= self.confidence_threshold:
                        detections.append(Detection(
                            box=(int(x), int(y), int(x + bw), int(y + bh)),
                            confidence=conf,
                            class_id=0,
                            class_name="person"
                        ))
            except Exception:
                pass

        # If HOG didn't find anything, try foreground motion blob detection
        if not detections:
            fg_mask = self.bg_subtractor.apply(gray)
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 1200:  # reasonable person blob size
                    x, y, bw, bh = cv2.boundingRect(cnt)
                    aspect_ratio = bh / float(max(1, bw))
                    if 1.1 <= aspect_ratio <= 4.0:  # roughly standing/moving human aspect ratio
                        detections.append(Detection(
                            box=(int(x), int(y), int(x + bw), int(y + bh)),
                            confidence=0.65,
                            class_id=0,
                            class_name="person"
                        ))

        return detections
